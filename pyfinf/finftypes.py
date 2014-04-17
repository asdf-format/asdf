# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os

from astropy.extern import six

from . import versioning


__all__ = ['format_tag', 'FinfTypeIndex', 'FinfType']


def format_tag(organization, standard, version, tag_name=None):
    """
    Format a YAML tag.
    """

    result = 'tag:{0}:{1}/{2}/'.format(
        organization, standard, version)
    if tag_name is not None:
        result += tag_name
    return result


class FinfTypeIndex(object):
    """
    An index of the known `FinfType`s.
    """

    _type_by_cls = {}
    _type_by_name = {}

    @classmethod
    def get_finftype_from_custom_type(cls, custom_type):
        return cls._type_by_cls.get(custom_type)

    @classmethod
    def get_finftype_from_yaml_tag(cls, tag):
        return cls._type_by_name.get(tag)


class FinfTypeMeta(type):
    """
    Keeps track of `FinfType` subclasses that are created, and stores
    them in `FinfTypeIndex`.
    """
    def __new__(mcls, name, bases, attrs):
        cls = super(FinfTypeMeta, mcls).__new__(mcls, name, bases, attrs)

        if hasattr(cls, 'name'):
            cls.yaml_tag = format_tag(
                cls.organization,
                cls.standard,
                versioning.version_to_string(cls.version),
                cls.name)

            FinfTypeIndex._type_by_cls[cls] = cls
            FinfTypeIndex._type_by_name[cls.yaml_tag] = cls

            for typ in cls.types:
                FinfTypeIndex._type_by_cls[typ] = cls

        return cls


@six.add_metaclass(FinfTypeMeta)
class FinfType(object):
    """
    The base class of all custom types in the tree.

    Besides the attributes defined below, most subclasses will also
    override `to_tree` and `from_tree`.

    To customize how the type's schema is located, override `get_schema_path`.

    Attributes
    ----------
    name : str
        The name of the type.

    organization : str
        The organization responsible for the type.

    standard : str
        The standard the type is defined in.  For built-in FINF types,
        this is ``"finf"``.

    version : 3-tuple of int
        The version of the standard the type is defined in.

    types : list of Python types
        Custom Python types that, when found in the tree, will be
        converted into basic types for YAML output.
    """
    name = None
    organization = 'stsci.edu'
    standard = 'finf'
    version = (0, 1, 0)
    types = []

    @classmethod
    def get_schema_path(cls):
        return os.path.join(
            cls.organization, cls.standard,
            versioning.version_to_string(cls.version),
            cls.name)

    @classmethod
    def get_schema(cls):
        from . import schema
        return schema.load_schema(cls.get_schema_path())

    @classmethod
    def validate(cls, tree):
        """
        Validate the given tree of basic data types against the schema
        for this type.
        """
        from . import schema
        schema.validate(tree, cls.get_schema())

    @classmethod
    def to_tree(cls, node, ctx):
        """
        Converts from a custom type to any of the basic types (dict,
        list, str, number) supported by YAML.  In most cases, must be
        overridden by subclasses.
        """
        return node.__class__.__bases__[0](node)

    @classmethod
    def from_tree(cls, tree, ctx):
        """
        Converts from basic types to a custom type.
        """
        return cls(tree)
