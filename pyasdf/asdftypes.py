# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import imp
import warnings

import six

from .compat import lru_cache
from . import tagged
from . import util
from . import versioning


__all__ = ['format_tag', 'AsdfTypeIndex', 'AsdfType']


_BASIC_PYTHON_TYPES = set(list(six.string_types) +
                          list(six.integer_types) +
                          [float, list, dict, tuple])


def format_tag(organization, standard, version, tag_name):
    """
    Format a YAML tag.
    """

    return 'tag:{0}:{1}/{2}-{3}'.format(
        organization, standard, tag_name, version)


class AsdfTypeIndex(object):
    """
    An index of the known `AsdfType`s.
    """
    def __init__(self):
        self._type_by_cls = {}
        self._type_by_subclasses = {}
        self._type_by_name = {}
        self._types_with_dynamic_subclasses = {}
        self._hooks_by_type = {}
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
            for typ2 in util.iter_subclasses(typ):
                self._type_by_subclasses[typ2] = asdftype

        if asdftype.handle_dynamic_subclasses:
            for typ in asdftype.types:
                self._types_with_dynamic_subclasses[typ] = asdftype

    def from_custom_type(self, custom_type):
        """
        Given a custom type, return the corresponding AsdfType
        definition.
        """
        # Basic Python types should not ever have an AsdfType
        # associated with them.
        if custom_type in _BASIC_PYTHON_TYPES:
            return None

        # Try to find an exact class match first...
        try:
            return self._type_by_cls[custom_type]
        except KeyError:
            # ...failing that, match any subclasses
            try:
                return self._type_by_subclasses[custom_type]
            except KeyError:
                # ...failing that, try any subclasses that we couldn't
                # cache in _type_by_subclasses.  This generally only
                # includes classes that are created dynamically post
                # Python-import, e.g. astropy.modeling._CompoundModel
                # subclasses.
                for key, val in six.iteritems(
                        self._types_with_dynamic_subclasses):
                    if issubclass(custom_type, key):
                        self._type_by_cls[custom_type] = val
                        return val

        return None

    def from_yaml_tag(self, tag):
        """
        From a given YAML tag string, return the corresponding
        AsdfType definition.
        """
        return self._type_by_name.get(tag)

    @lru_cache(5)
    def has_hook(self, hook_name):
        """
        Returns `True` if the given hook name exists on any of the managed
        types.
        """
        for cls in self._all_types:
            if hasattr(cls, hook_name):
                return True
        return False

    def get_hook_for_type(self, hookname, typ):
        """
        Get the hook function for the given type, if it exists,
        else return None.
        """
        hooks = self._hooks_by_type.setdefault(hookname, {})
        hook = hooks.get(typ, None)
        if hook is not None:
            return hook

        tag = self.from_custom_type(typ)
        if tag is not None:
            hook = getattr(tag, hookname, None)
            if hook is not None:
                hooks[typ] = hook
                return hook

        hooks[typ] = None
        return None


_all_asdftypes = set()


def _from_tree_tagged_missing_requirements(cls, tree, ctx):
    # A special version of AsdfType.from_tree_tagged for when the
    # required dependencies for an AsdfType are missing.  Shows a
    # warning, and then returns the raw dictionary.
    plural = 's' if len(cls.requires) else ''
    warnings.warn("{0} package{1} is required to instantiate '{2}'".format(
        util.human_list(cls.requires), plural, tree._tag))
    return tree


class AsdfTypeMeta(type):
    """
    Keeps track of `AsdfType` subclasses that are created, and stores
    them in `AsdfTypeIndex`.
    """
    _import_cache = {}

    @classmethod
    def _has_required_modules(cls, requires):
        for mod in requires:
            if mod in cls._import_cache:
                if not cls._import_cache[mod]:
                    return False
            try:
                imp.find_module(mod)
            except ImportError:
                cls._import_cache[mod] = False
                return False
            else:
                cls._import_cache[mod] = True
        return True

    @classmethod
    def _find_in_bases(cls, attrs, bases, name, default=None):
        if name in attrs:
            return attrs[name]
        for base in bases:
            if hasattr(base, name):
                return getattr(base, name)
        return default

    def __new__(mcls, name, bases, attrs):
        requires = mcls._find_in_bases(attrs, bases, 'requires', [])
        if not mcls._has_required_modules(requires):
            attrs['from_tree_tagged'] = classmethod(
                _from_tree_tagged_missing_requirements)
            attrs['types'] = []
            attrs['has_required_modules'] = False
        else:
            attrs['has_required_modules'] = True
            types = attrs.get('types', [])
            new_types = []
            for typ in types:
                if isinstance(typ, six.string_types):
                    typ = util.resolve_name(typ)
                new_types.append(typ)
            attrs['types'] = new_types

        cls = super(AsdfTypeMeta, mcls).__new__(mcls, name, bases, attrs)

        if hasattr(cls, 'name'):
            if isinstance(cls.name, six.string_types):
                if 'yaml_tag' not in attrs:
                    cls.yaml_tag = cls.make_yaml_tag(cls.name)
            elif isinstance(cls.name, list):
                pass
            elif cls.name is not None:
                raise TypeError("name must be string or list")

        _all_asdftypes.add(cls)

        return cls


@six.add_metaclass(AsdfTypeMeta)
@six.add_metaclass(util.InheritDocstrings)
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

    validators : dict
        Mapping JSON Schema keywords to validation functions for
        jsonschema.  Useful if the type defines extra types of
        validation that can be performed.

    requires : list of str
        A list of Python packages that are required to instantiate the
        object.
    """
    name = None
    organization = 'stsci.edu'
    standard = 'asdf'
    version = (0, 1, 0)
    types = []
    handle_dynamic_subclasses = False
    validators = {}
    requires = []

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
