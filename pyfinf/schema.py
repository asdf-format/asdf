# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os

from astropy.extern import six
from astropy.utils.compat.odict import OrderedDict

from jsonschema import validators
from jsonschema.exceptions import ValidationError
import yaml

from . import constants
from . import reference
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


_schema_cache = {}
def load_schema(name, reload=False):
    """
    Load a local FINF schema from the package.
    """
    if not reload and name in _schema_cache:
        return _schema_cache[name]

    _name = name.split('/')
    path = os.path.join(SCHEMA_PATH, *_name) + '.yaml'

    with open(path, 'rt') as fd:
        schema = yaml.safe_load(fd.read())

    _schema_cache[name] = schema
    return schema


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
    """Validates the propertyOrder attribute in YAML Schemas.

    The propertyOrder attribute requires an object to be represented as an
    ordered mapping (such as an OrderedDict) so that the keys are stored in
    the required order.

    Not all properties listed in propertyOrder are required to be present in
    object (unless specified by the "required" attribute), but must be in the
    correct relative position defined by this attribute. Properties not list in
    propertyOrder must come after the last property listed in propertyOrder,
    but may be in any order after that point.

    The object need not be an OrderedDict either, and this may validate by
    chance even on unordered dicts.  But to guarantee that it validates use an
    ordered mapping of some sort.
    """

    if not validator.is_type(instance, 'object'):
        return

    if not order:
        # propertyOrder may be an empty list
        return

    property_orders = dict((key, idx) for idx, key in enumerate(order))
    inst_keys = instance.keys()

    sort_key = lambda k: property_orders.get(k, len(property_orders))

    if inst_keys != sorted(inst_keys, key=sort_key):
        yield ValidationError(
            "Properties are not in the correct order according to the "
            "propertyOrder attribute.  Required {0!r}; got {1!r}.".format(
                order, inst_keys))


YAML_VALIDATORS = validators.Draft4Validator.VALIDATORS.copy()
YAML_VALIDATORS.update({
    'tag': validate_tag,
    'propertyOrder': validate_propertyOrder
})


class PackageLocalRefResolver(validators.RefResolver):
    """
    This is a resolver to pass to `jsonschema` that knows how to
    resolve URIs to files in the source package.
    """
    def __init__(self, root_uri, organization, local_path):
        super(PackageLocalRefResolver, self).__init__(root_uri, None)
        # Not to be confused with self.base_uri on the parent class
        self.root_uri = root_uri.rstrip('/') + '/'
        self.organization = organization
        self.local_path = os.path.normpath(local_path)

    def resolve_remote(self, uri):
        if uri.startswith(self.root_uri):
            path = uri[len(self.root_uri):].strip('/').split('/')
            path = os.path.join(self.organization, *path)
            if os.path.exists(os.path.join(self.local_path, path) + '.yaml'):
                return load_schema(path)

        return super(PackageLocalRefResolver, self).resolve_remote(uri)


RESOLVER = PackageLocalRefResolver(
    constants.STSCI_SCHEMA_URI_BASE, 'stsci.edu', SCHEMA_PATH)


_created_validator = False
def validate(instance, schema, cls=None, *args, **kwargs):
    """
    Validate the given instance against the given schema using the
    YAML schema extensions to JSON schema.

    The arguments are the same as to `jsonschema.validate`.
    """
    global _created_validator
    if not _created_validator:
        validator = validators.create(
            meta_schema=load_schema('stsci.edu/yaml-schema/draft-01'),
            validators=YAML_VALIDATORS,
            version=str('yaml schema draft 1'))
        validator.orig_iter_errors = validator.iter_errors

        # We can't validate anything that looks like an external
        # reference, since we don't have the actual content, so we
        # just have to defer it for now.  If the user cares about
        # complete validation, they can call
        # `FinfFile.resolve_references`.
        def iter_errors(self, instance, _schema=None):
            if ((isinstance(instance, dict) and '$ref' in instance) or
                isinstance(instance, reference.Reference)):
                return

            for x in self.orig_iter_errors(instance, _schema=_schema):
                yield x

        validator.iter_errors = iter_errors
        _created_validator = True

    if 'resolver' not in kwargs:
        kwargs['resolver'] = RESOLVER

    validators.validate(instance, schema, *args, **kwargs)
