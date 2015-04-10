# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.extern import six
from astropy.utils.misc import InheritDocstrings

from . import tagged
from . import versioning


__all__ = ['format_tag', 'AsdfTypeIndex', 'AsdfType']


def format_tag(organization, standard, version, tag_name=None):
    """
    Format a YAML tag.
    """

    result = 'tag:{0}:{1}/{2}/'.format(
        organization, standard, version)
    if tag_name is not None:
        result += tag_name
    return result


class AsdfTypeIndex(object):
    """
    An index of the known `AsdfType`s.
    """
    def __init__(self):
        self._type_by_cls = {}
        self._type_by_name = {}
        self._all_types = set()

    def add_type(self, asdftype):
        """
        Add a type to the index.
        """
        self._all_types.add(asdftype)

        if hasattr(asdftype, 'name'):
            if isinstance(asdftype.name, six.string_types):
                self._type_by_name[asdftype.yaml_tag] = asdftype
            elif isinstance(asdftype.name, list):
                for name in asdftype.name:
                    self._type_by_name[asdftype.make_yaml_tag(name)] = asdftype
            elif asdftype.name is not None:
                raise TypeError("name must be string or list")

        self._type_by_cls[asdftype] = asdftype
        for typ in asdftype.types:
            self._type_by_cls[typ] = asdftype

    def from_custom_type(self, custom_type):
        """
        Given a custom type, return the corresponding AsdfType
        definition.
        """
        try:
            return self._type_by_cls[custom_type]
        except KeyError:
            for key, val in six.iteritems(self._type_by_cls):
                if issubclass(custom_type, key):
                    return val
        return None

    def from_yaml_tag(self, tag):
        """
        From a given YAML tag string, return the corresponding
        AsdfType definition.
        """
        return self._type_by_name.get(tag)


_all_asdftypes = AsdfTypeIndex()


class AsdfTypeMeta(type):
    """
    Keeps track of `AsdfType` subclasses that are created, and stores
    them in `AsdfTypeIndex`.
    """
    def __new__(mcls, name, bases, attrs):
        cls = super(AsdfTypeMeta, mcls).__new__(mcls, name, bases, attrs)

        if hasattr(cls, 'name'):
            if isinstance(cls.name, six.string_types):
                if 'yaml_tag' not in attrs:
                    cls.yaml_tag = cls.make_yaml_tag(cls.name)
            elif isinstance(cls.name, list):
                pass
            elif cls.name is not None:
                raise TypeError("name must be string or list")

        _all_asdftypes.add_type(cls)

        return cls


@six.add_metaclass(AsdfTypeMeta)
@six.add_metaclass(InheritDocstrings)
class AsdfType(object):
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
        The standard the type is defined in.  For built-in ASDF types,
        this is ``"asdf"``.

    version : 3-tuple of int
        The version of the standard the type is defined in.

    types : list of Python types
        Custom Python types that, when found in the tree, will be
        converted into basic types for YAML output.
    """
    name = None
    organization = 'stsci.edu'
    standard = 'asdf'
    version = (0, 1, 0)
    types = []

    @classmethod
    def make_yaml_tag(cls, name):
        return format_tag(
            cls.organization,
            cls.standard,
            versioning.version_to_string(cls.version),
            name)

    @classmethod
    def to_tree(cls, node, ctx):
        """
        Converts from a custom type to any of the basic types (dict,
        list, str, number) supported by YAML.  In most cases, must be
        overridden by subclasses.
        """
        return node.__class__.__bases__[0](node)

    @classmethod
    def to_tree_tagged(cls, node, ctx):
        """
        Converts from a custom type to any of the basic types (dict,
        list, str, number) supported by YAML.  The result should be a
        tagged object.  Overriding this, rather than the more common
        `to_tree`, allows types to customize how the result is tagged.
        """
        obj = cls.to_tree(node, ctx)
        return tagged.tag_object(cls.yaml_tag, obj)

    @classmethod
    def from_tree(cls, tree, ctx):
        """
        Converts from basic types to a custom type.
        """
        return cls(tree)

    @classmethod
    def from_tree_tagged(cls, tree, ctx):
        """
        Converts from basic types to a custom type.  Overriding this,
        rather than the more common `from_tree`, allows types to deal
        with the tag directly.
        """
        return cls.from_tree(tree.data, ctx)
