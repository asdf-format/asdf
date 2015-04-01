# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import json
import os

from astropy.extern import six
from astropy.utils.compat.odict import OrderedDict

from jsonschema import validators
from jsonschema.exceptions import ValidationError
import yaml

from .compat import lru_cache
from . import constants
from . import generic_io
from . import reference
from . import resolver as mresolver
from . import tagged


__all__ = ['validate']


SCHEMA_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'schemas'))


PYTHON_TYPE_TO_YAML_TAG = {
    None: 'null',
    six.text_type: 'str',
    bytes: 'str',
    bool: 'bool',
    int: 'int',
    float: 'float',
    list: 'seq',
    dict: 'map',
    set: 'set',
    OrderedDict: 'omap'
}


if six.PY2:
    PYTHON_TYPE_TO_YAML_TAG[long] = 'int'


# Prepend full YAML tag prefix
for k, v in PYTHON_TYPE_TO_YAML_TAG.items():
    PYTHON_TYPE_TO_YAML_TAG[k] = constants.YAML_TAG_PREFIX + v


def _type_to_tag(type_):
    for base in type_.mro():
        if base in PYTHON_TYPE_TO_YAML_TAG:
            return PYTHON_TYPE_TO_YAML_TAG[base]


def validate_tag(validator, tagname, instance, schema):
    # Shortcut: If the instance is a subclass of YAMLObject then we know it
    # should have a yaml_tag attribute attached; otherwise we have to use a
    # hack of reserializing the object and seeing what tags get attached to it
    # (though there may be a better way than this).

    # We can't validate tags at the top level of the schema, because
    # the tag information is lost.  This is, however, enforced by how
    # the rest of the system works, so it shouldn't matter.
    if schema == validator.schema:
        return

    if isinstance(tagname, bytes):
        tagname = tagname.decode('ascii')

    if isinstance(instance, tagged.Tagged):
        instance_tag = instance.tag
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


YAML_VALIDATORS = validators.Draft4Validator.VALIDATORS.copy()
YAML_VALIDATORS.update({
    'tag': validate_tag,
    'propertyOrder': validate_propertyOrder,
    'flowStyle': validate_flowStyle,
    'style': validate_style
})


_created_validator = False
def create_validator():
    global _created_validator
    if _created_validator:
        return

    validator = validators.create(
        meta_schema=load_schema(
            'http://stsci.edu/schemas/yaml-schema/draft-01',
            mresolver.default_url_mapping),
        validators=YAML_VALIDATORS,
        version=str('yaml schema draft 1'))
    validator.orig_iter_errors = validator.iter_errors

    # We can't validate anything that looks like an external
    # reference, since we don't have the actual content, so we
    # just have to defer it for now.  If the user cares about
    # complete validation, they can call
    # `AsdfFile.resolve_references`.
    def iter_errors(self, instance, _schema=None):
        if ((isinstance(instance, dict) and '$ref' in instance) or
            isinstance(instance, reference.Reference)):
            return

        for x in self.orig_iter_errors(instance, _schema=_schema):
            yield x

    validator.iter_errors = iter_errors
    _created_validator = True


@lru_cache()
def _make_schema_loader(resolver):
    @lru_cache()
    def load_schema(url, reload=False):
        url = resolver(url)
        with generic_io.get_file(url) as fd:
            if isinstance(url, six.text_type) and url.endswith('json'):
                result = json.load(fd)
            else:
                result = yaml.safe_load(fd)
        return result

    return load_schema


def load_schema(url, resolver=None):
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
    """
    if resolver is None:
        resolver = mresolver.default_url_mapping
    loader = _make_schema_loader(resolver)
    return loader(url)


def validate(instance, schema, resolver=None, *args, **kwargs):
    """
    Validate the given instance against the given schema using the
    YAML schema extensions to JSON schema.

    The arguments are the same as to `jsonschema.validate`.
    """
    create_validator()

    handlers = {}
    for x in ['http', 'https', 'file']:
        handlers[x] = _make_schema_loader(resolver)
    kwargs['resolver'] = validators.RefResolver(
        schema.get('id', ''), schema, cache_remote=False,
        handlers=handlers)

    # We don't just call validators.validate() directly here, because
    # that validates the schema itself, wasting a lot of time (at the
    # time of this writing, it was half of the runtime of the unit
    # test suite!!!).  Instead, we assume that the schemas are valid
    # through the running of the unit tests, not at run time.
    cls = validators.validator_for(schema)
    cls(schema, *args, **kwargs).validate(instance)


def check_schema(schema):
    """
    Check a given schema to make sure it is valid YAML schema.
    """
    create_validator()

    cls = validators.validator_for(schema)
    cls.check_schema(schema)
