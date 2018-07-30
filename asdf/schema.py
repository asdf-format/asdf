# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import os
import json
import datetime
from functools import lru_cache
from collections import OrderedDict
from urllib import parse as urlparse

from jsonschema import validators as mvalidators
from jsonschema.exceptions import ValidationError

import yaml

from . import constants
from . import generic_io
from . import reference
from . import resolver as mresolver
from . import treeutil
from . import util


YAML_SCHEMA_METASCHEMA_ID = 'http://stsci.edu/schemas/yaml-schema/draft-01'


if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_loader = yaml.SafeLoader


__all__ = ['validate', 'fill_defaults', 'remove_defaults', 'check_schema']


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


def validate_tag(validator, tagname, instance, schema):
    if hasattr(instance, '_tag'):
        instance_tag = instance._tag
    else:
        # Try tags for known Python builtins
        instance_tag = _type_to_tag(type(instance))

    if instance_tag is not None and instance_tag != tagname:
        yield ValidationError(
            "mismatched tags, wanted '{0}', got '{1}'".format(
                tagname, instance_tag))


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
for key in ('allOf', 'anyOf', 'oneOf', 'items'):
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
for key in ('allOf', 'anyOf', 'oneOf', 'items'):
    REMOVE_DEFAULTS[key] = mvalidators.Draft4Validator.VALIDATORS[key]
REMOVE_DEFAULTS['properties'] = validate_remove_default



@lru_cache()
def _create_validator(validators=YAML_VALIDATORS):
    meta_schema = load_schema(YAML_SCHEMA_METASCHEMA_ID, mresolver.default_resolver)
    base_cls = mvalidators.create(meta_schema=meta_schema, validators=validators)

    class ASDFValidator(base_cls):
        DEFAULT_TYPES = base_cls.DEFAULT_TYPES.copy()
        DEFAULT_TYPES['array'] = (list, tuple)

        def iter_errors(self, instance, _schema=None, _seen=set()):
            # We can't validate anything that looks like an external reference,
            # since we don't have the actual content, so we just have to defer
            # it for now.  If the user cares about complete validation, they
            # can call `AsdfFile.resolve_references`.
            if id(instance) in _seen:
                return

            if _schema is None:
                schema = self.schema
            else:
                schema = _schema

            if ((isinstance(instance, dict) and '$ref' in instance) or
                    isinstance(instance, reference.Reference)):
                return

            if _schema is None:
                tag = getattr(instance, '_tag', None)
                if tag is not None:
                    schema_path = self.ctx.resolver(tag)
                    if schema_path != tag:
                        s = load_schema(schema_path, self.ctx.resolver)
                        if s:
                            with self.resolver.in_scope(schema_path):
                                for x in super(ASDFValidator, self).iter_errors(instance, s):
                                    yield x

                if isinstance(instance, dict):
                    new_seen = _seen | set([id(instance)])
                    for val in instance.values():
                        for x in self.iter_errors(val, _seen=new_seen):
                            yield x

                elif isinstance(instance, list):
                    new_seen = _seen | set([id(instance)])
                    for val in instance:
                        for x in self.iter_errors(val, _seen=new_seen):
                            yield x
            else:
                for x in super(ASDFValidator, self).iter_errors(instance, _schema=schema):
                    yield x

    return ASDFValidator


# We want to load mappings in schema as ordered dicts
class OrderedLoader(_yaml_base_loader):
    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


OrderedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping)


@lru_cache()
def _load_schema(url):
    with generic_io.get_file(url) as fd:
        if isinstance(url, str) and url.endswith('json'):
            json_data = fd.read().decode('utf-8')
            result = json.loads(json_data, object_pairs_hook=OrderedDict)
        else:
            result = yaml.load(fd, Loader=OrderedLoader)
    return result, fd.uri


def _make_schema_loader(resolver):
    def load_schema(url):
        url = resolver(url)
        return _load_schema(url)
    return load_schema


def _make_resolver(url_mapping):
    handlers = {}
    schema_loader = _make_schema_loader(url_mapping)

    def get_schema(url):
        return schema_loader(url)[0]

    for x in ['http', 'https', 'file', 'tag']:
        handlers[x] = get_schema

    # We set cache_remote=False here because we do the caching of
    # remote schemas here in `load_schema`, so we don't need
    # jsonschema to do it on our behalf.  Setting it to `True`
    # counterintuitively makes things slower.
    return mvalidators.RefResolver(
        '', {}, cache_remote=False, handlers=handlers)


def _load_draft4_metaschema():
    from jsonschema import _utils
    return _utils.load_schema('draft4')


# This is a list of schema that we have locally on disk but require
# special methods to obtain
HARDCODED_SCHEMA = {
    'http://json-schema.org/draft-04/schema': _load_draft4_metaschema
}


@lru_cache()
def load_custom_schema(url):
    # Avoid circular import
    from .tags.core import AsdfObject
    custom = load_schema(url, resolve_local_refs=True)
    core = load_schema(AsdfObject.yaml_tag)

    def update(d, u):
        from collections import Mapping
        for k, v in u.items():
            # Respect the property ordering of the core schema
            if k == 'propertyOrder' and k in d:
                d[k] = u[k] + d[k]
            elif isinstance(v, Mapping):
                d[k] = update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    return update(custom, core)

@lru_cache()
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
    """
    if resolver is None:
        resolver = mresolver.default_resolver
    loader = _make_schema_loader(resolver)
    if url in HARDCODED_SCHEMA:
        schema = HARDCODED_SCHEMA[url]()
    else:
        schema, url = loader(url)

    # Resolve local references
    if resolve_local_refs:
        def resolve_local(node, json_id):
            if isinstance(node, dict) and '$ref' in node:
                ref_url = resolver(node['$ref'])
                if ref_url.startswith('#'):
                    parts = urlparse.urlparse(ref_url)
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
                parts = urlparse.urlparse(suburl)
                fragment = parts.fragment
                if len(fragment):
                    suburl_path = suburl[:-(len(fragment) + 1)]
                else:
                    suburl_path = suburl
                suburl_path = resolver(suburl_path)
                if suburl_path == url:
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
                  *args, **kwargs):
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

    Returns
    -------
    validator : jsonschema.Validator
    """
    if ctx is None:
        from .asdf import AsdfFile
        ctx = AsdfFile()

    if validators is None:
        validators = util.HashableDict(YAML_VALIDATORS.copy())
        validators.update(ctx._extensions.validators)

    kwargs['resolver'] = _make_resolver(url_mapping)

    # We don't just call validators.validate() directly here, because
    # that validates the schema itself, wasting a lot of time (at the
    # time of this writing, it was half of the runtime of the unit
    # test suite!!!).  Instead, we assume that the schemas are valid
    # through the running of the unit tests, not at run time.
    cls = _create_validator(validators=validators)
    validator = cls(schema, *args, **kwargs)
    validator.ctx = ctx
    return validator


def validate_large_literals(instance):
    """
    Validate that the tree has no large numeric literals.
    """
    # We can count on 52 bits of precision
    for instance in treeutil.iter_tree(instance):
        if (isinstance(instance, int) and (
            instance > ((1 << 51) - 1) or
            instance < -((1 << 51) - 2))):
            raise ValidationError(
                "Integer value {0} is too large to safely represent as a "
                "literal in ASDF".format(instance))


def validate(instance, ctx=None, schema={}, validators=None, *args, **kwargs):
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
    """
    if ctx is None:
        from .asdf import AsdfFile
        ctx = AsdfFile()

    validator = get_validator(schema, ctx, validators, ctx.resolver,
                              *args, **kwargs)
    validator.validate(instance, _schema=(schema or None))

    validate_large_literals(instance)


def fill_defaults(instance, ctx):
    """
    For any default values in the schema, add them to the tree if they
    don't exist.

    Parameters
    ----------
    instance : tagged tree

    ctx : AsdfFile context
        Used to resolve tags and urls
    """
    validate(instance, ctx, validators=FILL_DEFAULTS)


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


def check_schema(schema):
    """
    Check a given schema to make sure it is valid YAML schema.
    """
    # We also want to validate the "default" values in the schema
    # against the schema itself.  jsonschema as a library doesn't do
    # this on its own.

    def validate_default(validator, default, instance, schema):
        if not validator.is_type(instance, 'object'):
            return

        if 'default' in instance:
            with instance_validator.resolver.in_scope(scope):
                for err in instance_validator.iter_errors(
                        instance['default'], instance):
                    yield err

    VALIDATORS = util.HashableDict(
        mvalidators.Draft4Validator.VALIDATORS.copy())
    VALIDATORS.update({
        'default': validate_default
    })

    meta_schema = load_schema(YAML_SCHEMA_METASCHEMA_ID, mresolver.default_resolver)

    resolver = _make_resolver(mresolver.default_resolver)

    cls = mvalidators.create(meta_schema=meta_schema,
                             validators=VALIDATORS)
    validator = cls(meta_schema, resolver=resolver)

    instance_validator = mvalidators.Draft4Validator(schema, resolver=resolver)
    scope = schema.get('id', '')

    validator.validate(schema, _schema=meta_schema)
