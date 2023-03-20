import copy
import datetime
import json
import warnings
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import contextmanager
from functools import lru_cache
from numbers import Integral
from operator import methodcaller

import numpy as np
import yaml
import importlib_metadata
if importlib_metadata.version('jsonschema') >= "4.18":
    USE_REFERENCING = True
    import referencing
    from referencing.exceptions import Unretrievable as RefError
else:
    from jsonschema.exceptions import RefResolutionError as RefError
    USE_REFERENCING = False
from jsonschema import validators as mvalidators
from jsonschema.exceptions import ValidationError

from . import constants, generic_io, reference, tagged, treeutil, util, versioning, yamlutil
from .config import get_config
from .exceptions import AsdfDeprecationWarning, AsdfWarning
from .extension import _legacy
from .util import patched_urllib_parse

YAML_SCHEMA_METASCHEMA_ID = "http://stsci.edu/schemas/yaml-schema/draft-01"

__all__ = ["validate", "fill_defaults", "remove_defaults", "check_schema"]

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


class _JsonSchemaValidatorFactory:
    def __init__(self, validator_class, seen_id_pairs):
        self._validator_class = validator_class
        self._seen_id_pairs = seen_id_pairs

    @contextmanager
    def validation_context(self):
        self._seen_id_pairs.clear()
        yield
        self._seen_id_pairs.clear()

    def has_seen_pair(self, schema, instance):
        return (id(schema), id(instance)) in self._seen_id_pairs

    def create(self, schema, resolver):
        if USE_REFERENCING:
            return self._validator_class(schema, registry=resolver)
        else:
            return self._validator_class(schema, resolver=resolver)


class _CycleCheckingValidatorProxy:
    """
    This class wraps the jsonschema Validator and ignores calls to descend
    if the instance + schema pair have already been seen in this validation
    session.
    """

    def __init__(self, delegate, seen_id_pairs):
        self._delegate = delegate
        self._seen_id_pairs = seen_id_pairs

    def descend(self, instance, schema, *args, **kwargs):
        seen_id_pair = (id(instance), id(schema))
        if seen_id_pair not in self._seen_id_pairs:
            self._seen_id_pairs.add(seen_id_pair)
            yield from self._delegate.descend(instance, schema, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._delegate, name)


def _create_cycle_checking_validator_method(validator_method, seen_id_pairs):
    """
    Wrap a jsonschema validator method so that the validator instance
    can then be wrapped in _CycleCheckingValidatorProxy before being
    passed to the original method.
    """

    def _cycle_checking_validator_method(validator, properties, instance, schema):
        if isinstance(validator, _CycleCheckingValidatorProxy):
            validator_proxy = validator
        else:
            validator_proxy = _CycleCheckingValidatorProxy(validator, seen_id_pairs)
        return validator_method(validator_proxy, properties, instance, schema)

    return _cycle_checking_validator_method


@lru_cache
def _create_json_schema_validator_factory(validators=YAML_VALIDATORS, visit_repeat_nodes=False):
    """
    Create an instance of _JsonSchemaValidatorFactory for the given set of validators
    and visit_repeat_nodes setting.  When visit_repeat_nodes is set to False, the
    validator methods will be wrapped to prevent re-validating the same instance + schema
    pair twice.  This is done to break reference cycles in the instance object.  The
    jsonschema library doesn't handle this because JSON documents do not support anything
    like YAML's anchor/alias feature.
    """
    type_checker = mvalidators.Draft4Validator.TYPE_CHECKER.redefine_many(
        {
            "array": lambda checker, instance: isinstance(instance, (list, tuple)),
            "integer": lambda checker, instance: not isinstance(instance, bool) and isinstance(instance, Integral),
            "string": lambda checker, instance: isinstance(instance, (str, np.str_)),
        },
    )

    meta_schema = _load_schema_cached(YAML_SCHEMA_METASCHEMA_ID, _legacy.get_default_resolver(), False, False)

    seen_id_pairs = set()
    if not visit_repeat_nodes:
        validators = {k: _create_cycle_checking_validator_method(v, seen_id_pairs) for k, v in validators.items()}

    create_kwargs = {
        "meta_schema": meta_schema,
        "validators": validators,
        "type_checker": type_checker,
        "id_of": mvalidators.Draft4Validator.ID_OF,
    }

    # We still support versions of jsonschema prior to the advent
    # of format checker.
    if hasattr(mvalidators.Draft4Validator, "FORMAT_CHECKER"):
        create_kwargs["format_checker"] = mvalidators.Draft4Validator.FORMAT_CHECKER

    validator_class = mvalidators.create(**create_kwargs)

    return _JsonSchemaValidatorFactory(validator_class, seen_id_pairs)


def _repair_and_warn_root_ref(schema):
    """
    The $ref property is supposed to wipe out all other content within
    the object that it resides which was clarified in draft 5 of the JSON
    Schema spec:

    https://datatracker.ietf.org/doc/html/draft-wright-json-schema-00#section-7

    but this library has historically permitted it to coexist with other properties.
    The code that was accidentally facilitating this has been fixed, but in order
    to give users a chance to update their schemas we're deliberately patching
    them here, with a warning.
    """
    if "$ref" in schema:
        schema_id = schema.get("id", "(unknown)")
        warnings.warn(
            f"Schema with id '{schema_id}' has a $ref at the root level. "
            "Please ask the schema maintainer to move the $ref to an allOf "
            "combiner.  This will be an error in asdf 3.0",
            AsdfDeprecationWarning,
        )
        schema.setdefault("allOf", []).append({"$ref": schema.pop("$ref")})


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

    _repair_and_warn_root_ref(result)

    return result, fd.uri


def _make_schema_loader(resolver):
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

            _repair_and_warn_root_ref(result)

            return result, url

        # If not, this must be a URL (or missing).  Fall back to fetching
        # the schema the old way:
        return _load_schema(url)

    return load_schema


def _make_resolver(url_mapping):
    handlers = {}
    schema_loader = _make_schema_loader(url_mapping)

    def get_schema(url):
        return schema_loader(url)[0]

    for x in ["http", "https", "file", "tag", "asdf"]:
        handlers[x] = get_schema

    # Supplying our own implementation of urljoin_cache
    # allows asdf:// URIs to be resolved correctly.
    urljoin_cache = lru_cache(1024)(patched_urllib_parse.urljoin)

    # We set cache_remote=False here because we do the caching of
    # remote schemas here in `load_schema`, so we don't need
    # jsonschema to do it on our behalf.  Setting it to `True`
    # counterintuitively makes things slower.
    if USE_REFERENCING:
        def retrieve_schema(url):
            schema = get_schema(url)
            resource = referencing.Resource(schema, specification=referencing.jsonschema.DRAFT4)
            return resource
        return referencing.Registry({}, retrieve=retrieve_schema)
    else:
        return mvalidators.RefResolver(
            "",
            {},
            cache_remote=False,
            handlers=handlers,
            urljoin_cache=urljoin_cache,
        )


@lru_cache
def load_custom_schema(url):
    warnings.warn(
        "The 'load_custom_schema(...)' function is deprecated. Use 'load_schema' instead.",
        AsdfDeprecationWarning,
    )
    return load_schema(url, resolve_references=True)


def load_schema(url, resolver=None, resolve_references=False, resolve_local_refs=False):
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
        warnings.warn("The 'resolve_local_refs' parameter is deprecated.", AsdfDeprecationWarning)

    if resolver is None:
        # We can't just set this as the default in load_schema's definition
        # because invoking get_default_resolver at import time leads to a circular import.
        resolver = _legacy.get_default_resolver()

    # We want to cache the work that went into constructing the schema, but returning
    # the same object is treacherous, because users who mutate the result will not
    # expect that they're changing the schema everywhere.
    return copy.deepcopy(_load_schema_cached(url, resolver, resolve_references, resolve_local_refs))


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
def _load_schema_cached(url, resolver, resolve_references, resolve_local_refs):
    loader = _make_schema_loader(resolver)
    schema, url = loader(url)

    if resolve_references or resolve_local_refs:

        def resolve_refs(node, json_id):
            if json_id is None:
                json_id = url

            if isinstance(node, dict) and "$ref" in node:
                suburl_base, suburl_fragment = _safe_resolve(resolver, json_id, node["$ref"])

                if suburl_base == url or suburl_base == schema.get("id"):
                    # This is a local ref, which we'll resolve in both cases.
                    subschema = schema
                elif resolve_references:
                    # Only resolve non-local refs when the flag is set.
                    subschema = load_schema(suburl_base, resolver, True)
                else:
                    # Otherwise return the $ref unmodified.
                    return node

                return reference.resolve_fragment(subschema, suburl_fragment)

            return node

        schema = treeutil.walk_and_modify(schema, resolve_refs)

    return schema


class _Validator:
    """
    ASDF schema validator.  The validate method quacks like jsonschema.Validator.validate, but
    all other jsonschema.Validator methods are unavailable.

    Parameters
    ----------
    ctx : asdf.AsdfFile
        Used to obtain schema URIs for tags handled by an old-style extension.

    serialization_context : asdf.asdf.SerializationContext
        Used to obtain schema URIs for tags handled by a new-style extension.

    json_schema_validator_factory : asdf.schema._JsonSchemaValidatorFactory
        Creates instances of jsonschema.Validator and manages the context that
        tracks nodes that have already been validated.

    schema : dict
        A schema to validate against in addition to the tag schemas.  One example
        is the custom schema passed to AsdfFile.__init__.

    visit_repeat_nodes : bool
        Flag that indicates (node, schema) pairs should be re-validated even if
        the validator factory's context indicates that they've already been
        seen.

    resolver : jsonschema.RefResolver
        jsonschema component that provides access to referenced schemas.
    """

    def __init__(self, ctx, serialization_context, json_schema_validator_factory, schema, visit_repeat_nodes, resolver):
        self._ctx = ctx
        self._serialization_context = serialization_context
        self._json_schema_validator_factory = json_schema_validator_factory
        self._schema = schema
        self._visit_repeat_nodes = visit_repeat_nodes
        self._resolver = resolver

    def _iter_errors(self, instance, _schema=None):
        if _schema is not None:
            yield from self._json_schema_validator_factory.create(_schema, self._resolver).iter_errors(instance)
        elif self._schema is not None:
            yield from self._json_schema_validator_factory.create(self._schema, self._resolver).iter_errors(instance)

        for node in treeutil.iter_tree(instance, _visit_repeat_nodes=self._visit_repeat_nodes):
            tag = getattr(node, "_tag", None)
            if tag is not None:
                if self._serialization_context.extension_manager.handles_tag_definition(tag):
                    tag_def = self._serialization_context.extension_manager.get_tag_definition(tag)
                    schema_uris = tag_def.schema_uris
                else:
                    schema_uris = [self._ctx._tag_mapping(tag)]
                    if schema_uris[0] == tag:
                        schema_uris = []

                for schema_uri in schema_uris:
                    try:
                        if USE_REFERENCING:
                            tag_resource = self._resolver.get_or_retrieve(schema_uri)
                            resolver = tag_resource.value @ self._resolver
                            v = self._json_schema_validator_factory.create(tag_resource.value.contents, resolver)
                            v._resolver = resolver.resolver_with_root(tag_resource.value)
                            yield from v.iter_errors(node)
                        else:
                            tag_schema = self._resolver.resolve(schema_uri)[1]
                            yield from self._json_schema_validator_factory.create(tag_schema, self._resolver).iter_errors(
                                node,
                            )
                    except RefError:
                        warnings.warn(f"Unable to locate schema file for '{tag}': '{schema_uri}'", AsdfWarning)

    def validate(self, instance, _schema=None):
        """
        Validate an instance of a tagged ASDF tree against the
        schemas associated with its tags, as well as any custom
        schema that was requested.
        """
        with self._json_schema_validator_factory.validation_context():
            for error in self._iter_errors(instance, _schema):
                raise error


def get_validator(
    schema=None,
    ctx=None,
    validators=None,
    url_mapping=None,
    _visit_repeat_nodes=False,
    _serialization_context=None,
):
    """
    Get a validator object for the given schema.  This method is not
    intended for use outside this package.

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
    validator : asdf.schema._Validator
    """
    if ctx is None:
        from .asdf import AsdfFile

        ctx = AsdfFile()

    if _serialization_context is None:
        _serialization_context = ctx._create_serialization_context()

    if validators is None:
        validators = util.HashableDict(YAML_VALIDATORS.copy())
        validators.update(ctx._extension_list.validators)
        validators.update(ctx._extension_manager.validator_manager.get_jsonschema_validators())

    resolver = _make_resolver(url_mapping)

    json_schema_validator_factory = _create_json_schema_validator_factory(
        validators=validators,
        visit_repeat_nodes=_visit_repeat_nodes,
    )
    return _Validator(
        ctx=ctx,
        serialization_context=_serialization_context,
        json_schema_validator_factory=json_schema_validator_factory,
        schema=schema,
        visit_repeat_nodes=_visit_repeat_nodes,
        resolver=resolver,
    )


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

    validator = get_validator({} if schema is None else schema, ctx, validators, ctx._resolver, *args, **kwargs)
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
        instance_validator = _create_json_schema_validator_factory().create(schema, _make_resolver(None))
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
    meta_schema = _load_schema_cached(meta_schema_id, _legacy.get_default_resolver(), False, False)

    resolver = _make_resolver(_legacy.get_default_resolver())

    cls = mvalidators.create(
        meta_schema=meta_schema,
        validators=validators,
        type_checker=mvalidators.Draft4Validator.TYPE_CHECKER,
        id_of=mvalidators.Draft4Validator.ID_OF,
        applicable_validators=applicable_validators,
    )
    if USE_REFERENCING:
        validator = cls(meta_schema, registry=resolver)
        resource = referencing.Resource(meta_schema, specification=referencing.jsonschema.DRAFT4)
        validator._resolver = resolver.resolver_with_root(resource)
    else:
        validator = cls(meta_schema, resolver=resolver)
    validator.validate(schema)
