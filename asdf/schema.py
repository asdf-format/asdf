import copy
import datetime
import json
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from functools import lru_cache
from numbers import Integral
from operator import methodcaller

import numpy as np
import yaml

from asdf._jsonschema import validators as mvalidators
from asdf._jsonschema.exceptions import RefResolutionError, ValidationError

from . import constants, generic_io, reference, tagged, treeutil, util, versioning, yamlutil
from .config import get_config
from .exceptions import AsdfWarning
from .util import _patched_urllib_parse

YAML_SCHEMA_METASCHEMA_ID = "http://stsci.edu/schemas/yaml-schema/draft-01"

__all__ = ["check_schema", "fill_defaults", "load_schema", "remove_defaults", "validate"]

PYTHON_TYPE_TO_YAML_TAG = {
    None: "null",
    str: "str",
    bytes: "str",
    bool: "bool",
    int: "int",
    float: "float",
    list: "seq",
    dict: "map",
    set: "set",
    OrderedDict: "omap",
}


# Prepend full YAML tag prefix
for k, v in PYTHON_TYPE_TO_YAML_TAG.items():
    PYTHON_TYPE_TO_YAML_TAG[k] = constants.YAML_TAG_PREFIX + v


def _type_to_tag(type_):
    for base in type_.mro():
        if base in PYTHON_TYPE_TO_YAML_TAG:
            return PYTHON_TYPE_TO_YAML_TAG[base]
    return None


def _default_resolver(uri):
    return uri


def validate_tag(validator, tag_pattern, instance, schema):
    """
    Implements the tag validation directive, which checks the
    tag against a pattern that may include wildcards.  See
    `asdf.util.uri_match` for details on the matching behavior.
    """
    instance_tag = instance._tag if hasattr(instance, "_tag") else _type_to_tag(type(instance))

    if instance_tag is None:
        yield ValidationError(
            f"mismatched tags, wanted '{tag_pattern}', got unhandled object type '{util.get_class_name(instance)}'",
        )

    if not util.uri_match(tag_pattern, instance_tag):
        yield ValidationError(f"mismatched tags, wanted '{tag_pattern}', got '{instance_tag}'")


def validate_propertyOrder(validator, order, instance, schema):
    """
    Stores a value on the `tagged.TaggedDict` instance so that
    properties can be written out in the preferred order.  In that
    sense this isn't really a "validator", but using the `jsonschema`
    library's extensible validation system is the easiest way to get
    this property assigned.
    """
    if not validator.is_type(instance, "object"):
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
    if not (validator.is_type(instance, "object") or validator.is_type(instance, "array")):
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
    if not validator.is_type(instance, "string"):
        return

    instance.style = style


def validate_type(validator, types, instance, schema):
    """
    PyYAML returns strings that look like dates as datetime objects.
    However, as far as JSON is concerned, this is type==string and
    format==date-time.  That detects for that case and doesn't raise
    an error, otherwise falling back to the default type checker.
    """
    if isinstance(instance, datetime.datetime) and schema.get("format") == "date-time" and "string" in types:
        return None

    return mvalidators.Draft4Validator.VALIDATORS["type"](validator, types, instance, schema)


def validate_enum(validator, enums, instance, schema):
    """
    `asdf.tagged.Tagged` objects will fail in the default enum validator
    """

    if isinstance(instance, tagged.Tagged):
        instance = instance.base

    yield from mvalidators.Draft4Validator.VALIDATORS["enum"](validator, enums, instance, schema)


YAML_VALIDATORS = util.HashableDict(mvalidators.Draft4Validator.VALIDATORS.copy())
YAML_VALIDATORS.update(
    {
        "tag": validate_tag,
        "propertyOrder": validate_propertyOrder,
        "flowStyle": validate_flowStyle,
        "style": validate_style,
        "type": validate_type,
        "enum": validate_enum,
    },
)


def validate_fill_default(validator, properties, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for property_, subschema in properties.items():
        if "default" in subschema:
            instance.setdefault(property_, subschema["default"])

    yield from mvalidators.Draft4Validator.VALIDATORS["properties"](validator, properties, instance, schema)


FILL_DEFAULTS = util.HashableDict()
for key in ("allOf", "items"):
    FILL_DEFAULTS[key] = mvalidators.Draft4Validator.VALIDATORS[key]
FILL_DEFAULTS["properties"] = validate_fill_default


def validate_remove_default(validator, properties, instance, schema):
    if not validator.is_type(instance, "object"):
        return

    for property_, subschema in properties.items():
        if subschema.get("default", None) is not None and instance.get(property_, None) == subschema["default"]:
            del instance[property_]

    yield from mvalidators.Draft4Validator.VALIDATORS["properties"](validator, properties, instance, schema)


REMOVE_DEFAULTS = util.HashableDict()
for key in ("allOf", "items"):
    REMOVE_DEFAULTS[key] = mvalidators.Draft4Validator.VALIDATORS[key]
REMOVE_DEFAULTS["properties"] = validate_remove_default


class _ValidationContext:
    """
    Context that tracks (tree node, schema fragment) pairs that have
    already been validated.

    Instances of this class are context managers that track
    how many times they have been entered, and only reset themselves
    when exiting the outermost context.
    """

    __slots__ = ["_depth", "_seen"]

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


@lru_cache
def _create_validator(validators=YAML_VALIDATORS, visit_repeat_nodes=False):
    meta_schema = _load_schema_cached(YAML_SCHEMA_METASCHEMA_ID, None, False)

    type_checker = mvalidators.Draft4Validator.TYPE_CHECKER.redefine_many(
        {
            "array": lambda checker, instance: isinstance(instance, (list, tuple)),
            "integer": lambda checker, instance: not isinstance(instance, bool) and isinstance(instance, Integral),
            "string": lambda checker, instance: isinstance(instance, (str, np.str_)),
        },
    )
    id_of = mvalidators.Draft4Validator.ID_OF
    ASDFvalidator = mvalidators.create(
        meta_schema=meta_schema,
        validators=validators,
        type_checker=type_checker,
        id_of=id_of,
    )

    def _patch_init(cls):
        original_init = cls.__init__

        def init(self, *args, **kwargs):
            self.ctx = kwargs.pop("ctx", None)
            self.serialization_context = kwargs.pop("serialization_context", None)

            original_init(self, *args, **kwargs)

        cls.__init__ = init

    def _patch_iter_errors(cls):
        original_iter_errors = cls.iter_errors

        cls._context = _ValidationContext()

        def iter_errors(self, instance, *args, **kwargs):
            # We can't validate anything that looks like an external reference,
            # since we don't have the actual content, so we just have to defer
            # it for now.  If the user cares about complete validation, they
            # can call `AsdfFile.resolve_references`.
            with self._context:
                if self._context.seen(instance, self.schema):
                    # We've already validated this instance against this schema,
                    # no need to do it again.
                    return

                if not visit_repeat_nodes:
                    self._context.add(instance, self.schema)

                if (isinstance(instance, dict) and "$ref" in instance) or isinstance(instance, reference.Reference):
                    return

                if not self.schema:
                    tag = getattr(instance, "_tag", None)
                    if tag is not None and self.serialization_context.extension_manager.handles_tag_definition(tag):
                        tag_def = self.serialization_context.extension_manager.get_tag_definition(tag)
                        schema_uris = tag_def.schema_uris

                        # Must validate against all schema_uris
                        for schema_uri in schema_uris:
                            try:
                                with self.resolver.resolving(schema_uri) as resolved:
                                    yield from self.descend(instance, resolved)
                            except RefResolutionError:
                                warnings.warn(f"Unable to locate schema file for '{tag}': '{schema_uri}'", AsdfWarning)

                    if isinstance(instance, dict):
                        for val in instance.values():
                            yield from self.iter_errors(val)

                    elif isinstance(instance, list):
                        for val in instance:
                            yield from self.iter_errors(val)
                else:
                    yield from original_iter_errors(self, instance)

        cls.iter_errors = iter_errors

    _patch_init(ASDFvalidator)
    _patch_iter_errors(ASDFvalidator)

    return ASDFvalidator


@lru_cache
def _load_schema(url):
    if url.startswith("http://") or url.startswith("https://") or url.startswith("asdf://"):
        msg = f"Unable to fetch schema from non-file URL: {url}"
        raise FileNotFoundError(msg)

    with generic_io.get_file(url) as fd:
        if isinstance(url, str) and url.endswith("json"):
            json_data = fd.read().decode("utf-8")
            result = json.loads(json_data, object_pairs_hook=OrderedDict)
        else:
            # The following call to yaml.load is safe because we're
            # using a loader that inherits from pyyaml's SafeLoader.
            result = yaml.load(fd, Loader=yamlutil.AsdfLoader)  # noqa: S506
    return result, fd.uri


def _make_schema_loader(resolver):
    if resolver is None:
        resolver = _default_resolver

    def load_schema(url):
        # Check if this is a URI provided by the new
        # Mapping API:
        resource_manager = get_config().resource_manager

        if url not in resource_manager:
            # Allow the resolvers to do their thing, in case they know
            # how to turn this string into a URI that the resource manager
            # recognizes.
            url = resolver(str(url))

        if url in resource_manager:
            content = resource_manager[url]
            # The jsonschema metaschemas are JSON, but pyyaml
            # doesn't mind.
            # The following call to yaml.load is safe because we're
            # using a loader that inherits from pyyaml's SafeLoader.
            result = yaml.load(content, Loader=yamlutil.AsdfLoader)  # noqa: S506
            return result, url

        # If not, this must be a URL (or missing).  Fall back to fetching
        # the schema the old way:
        return _load_schema(url)

    return load_schema


def _make_jsonschema_refresolver(url_mapping):
    handlers = {}
    schema_loader = _make_schema_loader(url_mapping)

    def get_schema(url):
        return schema_loader(url)[0]

    for x in ["http", "https", "file", "tag", "asdf"]:
        handlers[x] = get_schema

    # Supplying our own implementation of urljoin_cache
    # allows asdf:// URIs to be resolved correctly.
    urljoin_cache = lru_cache(1024)(_patched_urllib_parse.urljoin)

    # We set cache_remote=False here because we do the caching of
    # remote schemas here in `load_schema`, so we don't need
    # jsonschema to do it on our behalf.  Setting it to `True`
    # counterintuitively makes things slower.
    return mvalidators.RefResolver(
        "",
        {},
        cache_remote=False,
        handlers=handlers,
        urljoin_cache=urljoin_cache,
    )


def load_schema(url, resolver=None, resolve_references=False):
    """
    Load a schema from the given URL.

    Parameters
    ----------
    url : str
        The path to the schema

    resolver : callable, optional
        DEPRECATED arbitrary mapping of uris is no longer supported
        Please register all required resources with the resource manager.
        A callback function used to map URIs to other URIs.  The
        callable must take a string and return a string or `None`.
        This is useful, for example, when a remote resource has a
        mirror on the local filesystem that you wish to use.

    resolve_references : bool, optional
        If ``True``, resolve all ``$ref`` references.

    """
    if resolver is not None:
        warnings.warn("resolver is deprecated, arbitrary mapping of uris is no longer supported", DeprecationWarning)
    # We want to cache the work that went into constructing the schema, but returning
    # the same object is treacherous, because users who mutate the result will not
    # expect that they're changing the schema everywhere.
    return copy.deepcopy(_load_schema_cached(url, resolver, resolve_references))


def _safe_resolve(resolver, json_id, uri):
    """
    This function handles the tricky task of resolving a schema URI
    in the presence of both new and legacy extensions.

    There are two senses of "resolve" here: one is to resolve the URI
    to a file:// URL using the legacy extension resolver object. The other
    is to resolve relative URIs against the id of the current schema document,
    which is what generic_io.resolve_uri does.

    For URIs associated with new-style extensions, we want to resolve with
    generic_io.resolve_uri, but not with the resolver object, otherwise we risk
    mangling URIs that share a prefix with a resolver mapping.
    """
    if resolver is None:
        resolver = _default_resolver
    # We can't use urllib.parse here because tag: URIs don't
    # parse correctly.
    parts = uri.split("#")
    base = parts[0]
    fragment = parts[1] if len(parts) > 1 else ""

    # The generic_io.resolve_uri method cannot operate on tag: URIs.
    # New-style extensions don't support $ref with a tag URI target anyway,
    # so it's safe to feed this through the resolver right away.
    if base.startswith("tag:"):
        base = resolver(base)

    # Resolve relative URIs (e.g., #foo/bar, ../foo/bar) against
    # the current schema id.
    base = generic_io.resolve_uri(json_id, base)

    # Use the resolver object only if the URI does not belong to one
    # of the new-style extensions.
    if base not in get_config().resource_manager:
        base = resolver(base)

    return base, fragment


@lru_cache
def _load_schema_cached(url, resolver, resolve_references):
    loader = _make_schema_loader(resolver)
    schema, url = loader(url)

    if resolve_references:

        def resolve_refs(node, json_id):
            if json_id is None:
                json_id = url

            if isinstance(node, dict) and "$ref" in node:
                suburl_base, suburl_fragment = _safe_resolve(resolver, json_id, node["$ref"])

                if suburl_base == url or suburl_base == schema.get("id"):
                    # This is a local ref, which we'll resolve in both cases.
                    subschema = schema
                else:
                    subschema = load_schema(suburl_base, resolver, True)

                return reference.resolve_fragment(subschema, suburl_fragment)

            return node

        schema = treeutil.walk_and_modify(schema, resolve_refs)

    return schema


def get_validator(
    schema=None,
    ctx=None,
    validators=None,
    url_mapping=None,
    *args,
    _visit_repeat_nodes=False,
    _serialization_context=None,
    **kwargs,
):
    """
    Get a JSON schema validator object for the given schema.

    The additional *args and **kwargs are passed along to
    `~jsonschema.protocols.Validator.validate`.

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

    url_mapping : callable, optional
        DEPRECATED
        A callable that takes one string argument and returns a string
        to convert remote URLs into local ones.

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
    if url_mapping is not None:
        warnings.warn("url_mapping is deprecated, arbitrary mapping of uris is no longer supported", DeprecationWarning)

    if ctx is None:
        from ._asdf import AsdfFile

        ctx = AsdfFile()

    if _serialization_context is None:
        _serialization_context = ctx._create_serialization_context()

    if validators is None:
        validators = util.HashableDict(YAML_VALIDATORS.copy())
        validators.update(ctx._extension_manager.validator_manager.get_jsonschema_validators())

    kwargs["resolver"] = _make_jsonschema_refresolver(url_mapping)

    # We don't just call validators.validate() directly here, because
    # that validates the schema itself, wasting a lot of time (at the
    # time of this writing, it was half of the runtime of the unit
    # test suite!!!).  Instead, we assume that the schemas are valid
    # through the running of the unit tests, not at run time.
    cls = _create_validator(validators=validators, visit_repeat_nodes=_visit_repeat_nodes)
    return cls({} if schema is None else schema, *args, ctx=ctx, serialization_context=_serialization_context, **kwargs)


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
                AsdfWarning,
            )
        else:
            msg = f"Integer value {value} is too large to safely represent as a literal in ASDF"
            raise ValidationError(msg)

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
                    AsdfWarning,
                )
            else:
                msg = f"Mapping key {key} is not permitted.  Valid types: str, int, bool."
                raise ValidationError(msg)


def validate(instance, ctx=None, schema=None, validators=None, reading=False, *args, **kwargs):
    """
    Validate the given instance (which must be a tagged tree) against
    the appropriate schema.  The schema itself is located using the
    tag on the instance.

    The additional ``*args`` and ``**kwargs`` are passed along to
    `~jsonschema.protocols.Validator.validate`.

    Parameters
    ----------
    instance : tagged tree

    ctx : AsdfFile context
        Used to resolve tags and urls

    schema : schema, optional
        Explicit schema to use.  If not provided, the schema to use
        is determined by the tag on instance (or subinstance) and
        any custom schema provided to ``ctx``.

    validators : dict, optional
        A dictionary mapping properties to validators to use (instead
        of the built-in ones and ones provided by extension types).

    reading: bool, optional
        Indicates whether validation is being performed when the file is being
        read. This is useful to allow for different validation behavior when
        reading vs writing files.
    """
    if ctx is None:
        from ._asdf import AsdfFile

        ctx = AsdfFile()

    if schema is None and ctx._custom_schema:
        schema = ctx._custom_schema
    validator = get_validator({} if schema is None else schema, ctx, validators, None, *args, **kwargs)
    validator.validate(instance)

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
        The schema object, as returned by ``load_schema``.
    validate_default : bool, optional
        Set to `True` to validate the content of the default
        field against the schema.
    """
    validators = util.HashableDict(mvalidators.Draft4Validator.VALIDATORS.copy())

    if validate_default:
        # The jsonschema library doesn't validate defaults
        # on its own.
        instance_validator = get_validator(schema)
        instance_scope = schema.get("id", "")

        def _validate_default(validator, default, instance, schema):
            if not validator.is_type(instance, "object"):
                return

            if "default" in instance:
                instance_validator.resolver.push_scope(instance_scope)
                try:
                    yield from instance_validator.descend(instance["default"], instance)
                finally:
                    instance_validator.resolver.pop_scope()

        validators.update({"default": _validate_default})

        def applicable_validators(schema):
            items = list(schema.items())
            items.append(("default", ""))
            return items

    else:
        applicable_validators = methodcaller("items")

    meta_schema_id = schema.get("$schema", YAML_SCHEMA_METASCHEMA_ID)
    meta_schema = _load_schema_cached(meta_schema_id, None, False)

    resolver = _make_jsonschema_refresolver(_default_resolver)

    cls = mvalidators.create(
        meta_schema=meta_schema,
        validators=validators,
        type_checker=mvalidators.Draft4Validator.TYPE_CHECKER,
        id_of=mvalidators.Draft4Validator.ID_OF,
        applicable_validators=applicable_validators,
    )
    validator = cls(meta_schema, resolver=resolver)
    validator.validate(schema)
