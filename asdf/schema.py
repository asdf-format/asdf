import json
import datetime
import warnings
import copy
from numbers import Integral
from functools import lru_cache
from collections import OrderedDict
from collections.abc import Mapping

from jsonschema import validators as mvalidators
from jsonschema.exceptions import ValidationError

import yaml
import numpy as np

from .config import get_config
from . import constants
from . import generic_io
from . import reference
from . import treeutil
from . import util
from . import extension
from . import yamlutil
from . import versioning
from . import tagged
from .exceptions import AsdfDeprecationWarning, AsdfWarning

from .util import patched_urllib_parse


YAML_SCHEMA_METASCHEMA_ID = 'http://stsci.edu/schemas/yaml-schema/draft-01'


if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_loader = yaml.SafeLoader


__all__ = ['validate', 'fill_defaults', 'remove_defaults', 'check_schema']


def default_ext_resolver(uri):
    """
    Resolver that uses tag/url mappings from all installed extensions
    """
    # Deprecating this because it doesn't play nicely with the caching on
    # load_schema(...).
    warnings.warn(
            "The 'default_ext_resolver(...)' function is deprecated. Use "
            "'asdf.extension.get_default_resolver()(...)' instead.",
            AsdfDeprecationWarning)
    return extension.get_default_resolver()(uri)


PYTHON_TYPE_TO_YAML_TAG = {
    None: 'null',
    str: 'str',
    bytes: 'str',
    bool: 'bool',
    int: 'int',
    float: 'float',
    list: 'seq',
    dict: 'map',
    set: 'set',
    OrderedDict: 'omap'
}


# Prepend full YAML tag prefix
for k, v in PYTHON_TYPE_TO_YAML_TAG.items():
    PYTHON_TYPE_TO_YAML_TAG[k] = constants.YAML_TAG_PREFIX + v


def _type_to_tag(type_):
    for base in type_.mro():
        if base in PYTHON_TYPE_TO_YAML_TAG:
            return PYTHON_TYPE_TO_YAML_TAG[base]
    return None


def validate_tag(validator, tag_pattern, instance, schema):
    """
    Implements the tag validation directive, which checks the
    tag against a pattern that may include wildcards.  See
    `asdf.util.uri_match` for details on the matching behavior.
    """
    if hasattr(instance, '_tag'):
        instance_tag = instance._tag
    else:
        # Try tags for known Python builtins
        instance_tag = _type_to_tag(type(instance))

    if instance_tag is None:
        yield ValidationError(
            "mismatched tags, wanted '{}', got unhandled object type '{}'".format(
                tag_pattern, util.get_class_name(instance)
            )
        )

    if not util.uri_match(tag_pattern, instance_tag):
        yield ValidationError(
            "mismatched tags, wanted '{0}', got '{1}'".format(
                tag_pattern, instance_tag))


def validate_propertyOrder(validator, order, instance, schema):
    """
    Stores a value on the `tagged.TaggedDict` instance so that
    properties can be written out in the preferred order.  In that
    sense this isn't really a "validator", but using the `jsonschema`
    library's extensible validation system is the easiest way to get
    this property assigned.
    """
    if not validator.is_type(instance, 'object'):
        return

    if not order:
        # propertyOrder may be an empty list
        return

    instance.property_order = order


def validate_flowStyle(validator, flow_style, instance, schema):
    """
    Sets a flag on the `tagged.TaggedList` or `tagged.TaggedDict`
    object so that the YAML generator knows which style to use to
    write the element.  In that sense this isn't really a "validator",
    but using the `jsonschema` library's extensible validation system
    is the easiest way to get this property assigned.
    """
    if not (validator.is_type(instance, 'object') or
            validator.is_type(instance, 'array')):
        return

    instance.flow_style = flow_style


def validate_style(validator, style, instance, schema):
    """
    Sets a flag on the `tagged.TaggedString` object so that the YAML
    generator knows which style to use to write the string.  In that
    sense this isn't really a "validator", but using the `jsonschema`
    library's extensible validation system is the easiest way to get
    this property assigned.
    """
    if not validator.is_type(instance, 'string'):
        return

    instance.style = style


def validate_type(validator, types, instance, schema):
    """
    PyYAML returns strings that look like dates as datetime objects.
    However, as far as JSON is concerned, this is type==string and
    format==date-time.  That detects for that case and doesn't raise
    an error, otherwise falling back to the default type checker.
    """
    if (isinstance(instance, datetime.datetime) and
        schema.get('format') == 'date-time' and
        'string' in types):
        return

    return mvalidators.Draft4Validator.VALIDATORS['type'](
        validator, types, instance, schema)


YAML_VALIDATORS = util.HashableDict(
    mvalidators.Draft4Validator.VALIDATORS.copy())
YAML_VALIDATORS.update({
    'tag': validate_tag,
    'propertyOrder': validate_propertyOrder,
    'flowStyle': validate_flowStyle,
    'style': validate_style,
    'type': validate_type
})


def validate_fill_default(validator, properties, instance, schema):
    if not validator.is_type(instance, 'object'):
        return

    for property, subschema in properties.items():
        if "default" in subschema:
            instance.setdefault(property, subschema["default"])

    for err in mvalidators.Draft4Validator.VALIDATORS['properties'](
        validator, properties, instance, schema):
        yield err


FILL_DEFAULTS = util.HashableDict()
for key in ('allOf', 'items'):
    FILL_DEFAULTS[key] = mvalidators.Draft4Validator.VALIDATORS[key]
FILL_DEFAULTS['properties'] = validate_fill_default


def validate_remove_default(validator, properties, instance, schema):
    if not validator.is_type(instance, 'object'):
        return

    for property, subschema in properties.items():
        if subschema.get("default", None) is not None:
            if instance.get(property, None) == subschema["default"]:
                del instance[property]

    for err in mvalidators.Draft4Validator.VALIDATORS['properties'](
        validator, properties, instance, schema):
        yield err


REMOVE_DEFAULTS = util.HashableDict()
for key in ('allOf', 'items'):
    REMOVE_DEFAULTS[key] = mvalidators.Draft4Validator.VALIDATORS[key]
REMOVE_DEFAULTS['properties'] = validate_remove_default


class _ValidationContext:
    """
    Context that tracks (tree node, schema fragment) pairs that have
    already been validated.

    Instances of this class are context managers that track
    how many times they have been entered, and only reset themselves
    when exiting the outermost context.
    """
    def __init__(self):
        self._depth = 0
        self._seen = set()

    def add(self, instance, schema):
        """
        Inform the context that an instance has
        been validated against a schema fragment.
        """
        self._seen.add(self._make_seen_key(instance, schema))

    def seen(self, instance, schema):
        """
        Return True if an instance has already been
        validated against a schema fragment.
        """
        return self._make_seen_key(instance, schema) in self._seen

    def __enter__(self):
        self._depth += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._depth -= 1

        if self._depth == 0:
            self._seen = set()

    def _make_seen_key(self, instance, schema):
        return (id(instance), id(schema))


@lru_cache()
def _create_validator(validators=YAML_VALIDATORS, visit_repeat_nodes=False):
    meta_schema = _load_schema_cached(YAML_SCHEMA_METASCHEMA_ID, extension.get_default_resolver(), False, False)

    type_checker = mvalidators.Draft4Validator.TYPE_CHECKER.redefine_many({
        'array': lambda checker, instance: isinstance(instance, list) or isinstance(instance, tuple),
        'integer': lambda checker, instance: not isinstance(instance, bool) and isinstance(instance, Integral),
        'string': lambda checker, instance: isinstance(instance, (str, np.str_)),
    })
    id_of = mvalidators.Draft4Validator.ID_OF
    base_cls = mvalidators.create(
        meta_schema=meta_schema,
        validators=validators,
        type_checker=type_checker,
        id_of=id_of
    )

    class ASDFValidator(base_cls):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._context = _ValidationContext()

        def iter_errors(self, instance, _schema=None):
            # We can't validate anything that looks like an external reference,
            # since we don't have the actual content, so we just have to defer
            # it for now.  If the user cares about complete validation, they
            # can call `AsdfFile.resolve_references`.
            with self._context:
                if _schema is None:
                    schema = self.schema
                else:
                    schema = _schema

                if self._context.seen(instance, schema):
                    # We've already validated this instance against this schema,
                    # no need to do it again.
                    return

                if not visit_repeat_nodes:
                    self._context.add(instance, schema)

                if ((isinstance(instance, dict) and '$ref' in instance) or
                        isinstance(instance, reference.Reference)):
                    return

                if _schema is None:
                    tag = getattr(instance, '_tag', None)
                    if tag is not None:
                        if self.serialization_context.extension_manager.handles_tag(tag):
                            tag_def = self.serialization_context.extension_manager.get_tag_definition(tag)
                            schema_uri = tag_def.schema_uri
                        else:
                            schema_uri = self.ctx.tag_mapping(tag)
                            if schema_uri == tag:
                                schema_uri = None

                        if schema_uri is not None:
                            try:
                                s = _load_schema_cached(schema_uri, self.ctx.resolver, False, False)
                            except FileNotFoundError:
                                msg = "Unable to locate schema file for '{}': '{}'"
                                warnings.warn(msg.format(tag, schema_uri), AsdfWarning)
                                s = {}
                            if s:
                                with self.resolver.in_scope(schema_uri):
                                    for x in super(ASDFValidator, self).iter_errors(instance, s):
                                        yield x


                    if isinstance(instance, dict):
                        for val in instance.values():
                            for x in self.iter_errors(val):
                                yield x

                    elif isinstance(instance, list):
                        for val in instance:
                            for x in self.iter_errors(val):
                                yield x
                else:
                    for x in super(ASDFValidator, self).iter_errors(instance, _schema=schema):
                        yield x

    return ASDFValidator


@lru_cache()
def _load_schema(url):
    with generic_io.get_file(url) as fd:
        if isinstance(url, str) and url.endswith('json'):
            json_data = fd.read().decode('utf-8')
            result = json.loads(json_data, object_pairs_hook=OrderedDict)
        else:
            # The following call to yaml.load is safe because we're
            # using a loader that inherits from pyyaml's SafeLoader.
            result = yaml.load(fd, Loader=yamlutil.AsdfLoader) # nosec
    return result, fd.uri


def _make_schema_loader(resolver):
    def load_schema(url):
        # Check if this is a URI provided by the new
        # Mapping API:
        resource_manager = get_config().resource_manager
        if url in resource_manager:
            content = resource_manager[url]
            # The jsonschema metaschemas are JSON, but pyyaml
            # doesn't mind.
            # The following call to yaml.load is safe because we're
            # using a loader that inherits from pyyaml's SafeLoader.
            result = yaml.load(content, Loader=yamlutil.AsdfLoader) # nosec
            return result, url

        # If not, fall back to fetching the schema the old way:
        url = resolver(str(url))
        return _load_schema(url)
    return load_schema


def _make_resolver(url_mapping):
    handlers = {}
    schema_loader = _make_schema_loader(url_mapping)

    def get_schema(url):
        return schema_loader(url)[0]

    for x in ['http', 'https', 'file', 'tag', 'asdf']:
        handlers[x] = get_schema

    # Supplying our own implementation of urljoin_cache
    # allows asdf:// URIs to be resolved correctly.
    urljoin_cache = lru_cache(1024)(patched_urllib_parse.urljoin)

    # We set cache_remote=False here because we do the caching of
    # remote schemas here in `load_schema`, so we don't need
    # jsonschema to do it on our behalf.  Setting it to `True`
    # counterintuitively makes things slower.
    return mvalidators.RefResolver(
        '',
        {},
        cache_remote=False,
        handlers=handlers,
        urljoin_cache=urljoin_cache,
    )


@lru_cache()
def load_custom_schema(url):
    warnings.warn(
        "The 'load_custom_schema(...)' function is deprecated. Use"
        "'load_schema' instead.",
        AsdfDeprecationWarning
    )
    return load_schema(url, resolve_references=True)


def load_schema(url, resolver=None, resolve_references=False,
                resolve_local_refs=False):
    """
    Load a schema from the given URL.

    Parameters
    ----------
    url : str
        The path to the schema

    resolver : callable, optional
        A callback function used to map URIs to other URIs.  The
        callable must take a string and return a string or `None`.
        This is useful, for example, when a remote resource has a
        mirror on the local filesystem that you wish to use.

    resolve_references : bool, optional
        If `True`, resolve all `$ref` references.

    resolve_local_refs : bool, optional
        If `True`, resolve all `$ref` references that refer to other objects
        within the same schema. This will automatically be handled when passing
        `resolve_references=True`, but it may be desirable in some cases to
        control local reference resolution separately.
        This parameter is deprecated.
    """
    if resolve_local_refs is True:
        warnings.warn(
            "The 'resolve_local_refs' parameter is deprecated.",
            AsdfDeprecationWarning
        )

    if resolver is None:
        # We can't just set this as the default in load_schema's definition
        # because invoking get_default_resolver at import time leads to a circular import.
        resolver = extension.get_default_resolver()

    # We want to cache the work that went into constructing the schema, but returning
    # the same object is treacherous, because users who mutate the result will not
    # expect that they're changing the schema everywhere.
    return copy.deepcopy(
        _load_schema_cached(url, resolver, resolve_references, resolve_local_refs)
    )


@lru_cache()
def _load_schema_cached(url, resolver, resolve_references, resolve_local_refs):
    loader = _make_schema_loader(resolver)
    schema, url = loader(url)

    # Resolve local references
    if resolve_local_refs:
        def resolve_local(node, json_id):
            if isinstance(node, dict) and '$ref' in node:
                ref_url = resolver(node['$ref'])
                if ref_url.startswith('#'):
                    parts = patched_urllib_parse.urlparse(ref_url)
                    subschema_fragment = reference.resolve_fragment(
                        schema, parts.fragment)
                    return subschema_fragment
            return node

        schema = treeutil.walk_and_modify(schema, resolve_local)

    if resolve_references:
        def resolve_refs(node, json_id):
            if json_id is None:
                json_id = url
            if isinstance(node, dict) and '$ref' in node:
                suburl = generic_io.resolve_uri(json_id, resolver(node['$ref']))
                parts = patched_urllib_parse.urlparse(suburl)
                fragment = parts.fragment
                if len(fragment):
                    suburl_path = suburl[:-(len(fragment) + 1)]
                else:
                    suburl_path = suburl
                suburl_path = resolver(suburl_path)
                if suburl_path == url or suburl_path == schema.get("id"):
                    subschema = schema
                else:
                    subschema = load_schema(suburl_path, resolver, True)

                subschema_fragment = reference.resolve_fragment(
                    subschema, fragment)
                return subschema_fragment

            return node

        schema = treeutil.walk_and_modify(schema, resolve_refs)

    return schema


def get_validator(schema={}, ctx=None, validators=None, url_mapping=None,
                  *args, _visit_repeat_nodes=False, _serialization_context=None,
                  **kwargs):
    """
    Get a JSON schema validator object for the given schema.

    The additional *args and **kwargs are passed along to
    `jsonschema.validate`.

    Parameters
    ----------
    schema : schema, optional
        Explicit schema to use.  If not provided, the schema to use
        is determined by the tag on instance (or subinstance).

    ctx : AsdfFile context
        Used to resolve tags and urls

    validators : dict, optional
        A dictionary mapping properties to validators to use (instead
        of the built-in ones and ones provided by extension types).

    url_mapping : resolver.Resolver, optional
        A resolver to convert remote URLs into local ones.

    _visit_repeat_nodes : bool, optional
        Force the validator to visit nodes that it has already
        seen.  This flag is a temporary hack to support a specific
        project that uses a custom validator to update a .fits file.
        Setting `True` is discouraged and will lead to RecursionError
        in trees containing reference cycles.

    Returns
    -------
    validator : jsonschema.Validator
    """
    if ctx is None:
        from .asdf import AsdfFile
        ctx = AsdfFile()

    if _serialization_context is None:
        _serialization_context = ctx._create_serialization_context()

    if validators is None:
        validators = util.HashableDict(YAML_VALIDATORS.copy())
        validators.update(ctx.extension_list.validators)

    kwargs['resolver'] = _make_resolver(url_mapping)

    # We don't just call validators.validate() directly here, because
    # that validates the schema itself, wasting a lot of time (at the
    # time of this writing, it was half of the runtime of the unit
    # test suite!!!).  Instead, we assume that the schemas are valid
    # through the running of the unit tests, not at run time.
    cls = _create_validator(validators=validators, visit_repeat_nodes=_visit_repeat_nodes)
    validator = cls(schema, *args, **kwargs)
    validator.ctx = ctx
    validator.serialization_context = _serialization_context
    return validator


def _validate_large_literals(instance, reading):
    """
    Validate that the tree has no large numeric literals.
    """
    def _validate(value):
        if value <= constants.MAX_NUMBER and value >= constants.MIN_NUMBER:
            return

        if reading:
            warnings.warn(
                f"Invalid integer literal value {value} detected while reading file. "
                "The value has been read safely, but the file should be "
                "fixed.",
                AsdfWarning
            )
        else:
            raise ValidationError(
                f"Integer value {value} is too large to safely represent as a "
                "literal in ASDF"
            )

    if isinstance(instance, Integral):
        _validate(instance)
    elif isinstance(instance, Mapping):
        for key in instance:
            if isinstance(key, Integral):
                _validate(key)


def _validate_mapping_keys(instance, reading):
    """
    Validate that mappings do not contain illegal key types
    (as of ASDF Standard 1.6.0, only str, int, and bool are
    permitted).
    """
    if not isinstance(instance, Mapping):
        return

    for key in instance:
        if isinstance(key, tagged.Tagged) or not isinstance(key, (str, int, bool)):
            if reading:
                warnings.warn(
                    f"Invalid mapping key {key} detected while reading file. "
                    "The value has been read safely, but the file should be "
                    "fixed.",
                    AsdfWarning
                )
            else:
                raise ValidationError(
                    f"Mapping key {key} is not permitted.  Valid types: "
                    "str, int, bool."
                )


def validate(instance, ctx=None, schema={}, validators=None, reading=False,
             *args, **kwargs):
    """
    Validate the given instance (which must be a tagged tree) against
    the appropriate schema.  The schema itself is located using the
    tag on the instance.

    The additional *args and **kwargs are passed along to
    `jsonschema.validate`.

    Parameters
    ----------
    instance : tagged tree

    ctx : AsdfFile context
        Used to resolve tags and urls

    schema : schema, optional
        Explicit schema to use.  If not provided, the schema to use
        is determined by the tag on instance (or subinstance).

    validators : dict, optional
        A dictionary mapping properties to validators to use (instead
        of the built-in ones and ones provided by extension types).

    reading: bool, optional
        Indicates whether validation is being performed when the file is being
        read. This is useful to allow for different validation behavior when
        reading vs writing files.
    """
    if ctx is None:
        from .asdf import AsdfFile
        ctx = AsdfFile()

    validator = get_validator(schema, ctx, validators, ctx.resolver,
                              *args, **kwargs)
    validator.validate(instance, _schema=(schema or None))

    additional_validators = [_validate_large_literals]
    if ctx.version >= versioning.RESTRICTED_KEYS_MIN_VERSION:
        additional_validators.append(_validate_mapping_keys)

    def _callback(instance):
        for validator in additional_validators:
            validator(instance, reading)

    treeutil.walk(instance, _callback)


def fill_defaults(instance, ctx, reading=False):
    """
    For any default values in the schema, add them to the tree if they
    don't exist.

    Parameters
    ----------
    instance : tagged tree

    ctx : AsdfFile context
        Used to resolve tags and urls

    reading: bool, optional
        Indicates whether the ASDF file is being read (in contrast to being
        written).
    """
    validate(instance, ctx, validators=FILL_DEFAULTS, reading=reading)


def remove_defaults(instance, ctx):
    """
    For any values in the tree that are the same as the default values
    specified in the schema, remove them from the tree.

    Parameters
    ----------
    instance : tagged tree

    ctx : AsdfFile context
        Used to resolve tags and urls
    """
    validate(instance, ctx, validators=REMOVE_DEFAULTS)


def check_schema(schema, validate_default=True):
    """
    Check a given schema to make sure it is valid YAML schema.

    Parameters
    ----------
    schema : dict
        The schema object, as returned by `load_schema`.
    validate_default : bool, optional
        Set to `True` to validate the content of the default
        field against the schema.
    """
    validators = util.HashableDict(
        mvalidators.Draft4Validator.VALIDATORS.copy())

    if validate_default:
        # The jsonschema library doesn't validate defaults
        # on its own.
        instance_validator = get_validator(schema)
        instance_scope = schema.get('id', '')

        def _validate_default(validator, default, instance, schema):
            if not validator.is_type(instance, 'object'):
                return

            if 'default' in instance:
                with instance_validator.resolver.in_scope(instance_scope):
                    for err in instance_validator.iter_errors(
                            instance['default'], instance):
                        yield err

        validators.update({
            'default': _validate_default
        })

    meta_schema_id = schema.get('$schema', YAML_SCHEMA_METASCHEMA_ID)
    meta_schema = _load_schema_cached(meta_schema_id, extension.get_default_resolver(), False, False)

    resolver = _make_resolver(extension.get_default_resolver())

    cls = mvalidators.create(
        meta_schema=meta_schema,
        validators=validators,
        type_checker=mvalidators.Draft4Validator.TYPE_CHECKER,
        id_of=mvalidators.Draft4Validator.ID_OF,
    )
    validator = cls(meta_schema, resolver=resolver)
    validator.validate(schema, _schema=meta_schema)
