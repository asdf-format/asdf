# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import bisect
import imp
import warnings

import six


from .compat import lru_cache
from .extern import semver

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


def split_tag_version(tag):
    """
    Split a tag into its base and version.
    """
    name, version = tag.rsplit('-', 1)
    version = semver.parse(version)
    return name, (version['major'], version['minor'], version['patch'])


def join_tag_version(name, version):
    """
    Join the root and version of a tag back together.
    """
    return '{0}-{1}'.format(name, versioning.version_to_string(version))


class _AsdfWriteTypeIndex(object):
    """
    The _AsdfWriteTypeIndex is a helper class for AsdfTypeIndex that
    manages an index of types for writing out ASDF files, i.e. from
    converting from custom types to tagged_types.  It is not always
    the inverse of the mapping from tags to custom types, since there
    are likely multiple versions present for a given tag.

    This uses the `version_map.yaml` file that ships with the ASDF
    standard to figure out which schemas correspond to a particular
    version of the ASDF standard.

    An AsdfTypeIndex manages multiple _AsdfWriteTypeIndex instances
    for each version the user may want to write out, and they are
    instantiated on-demand.

    If version is ``'latest'``, it will just use the highest-numbered
    versions of each of the schemas.  This is currently only used to
    aid in testing.
    """
    _version_map = None

    def __init__(self, version, index):
        self._version = version

        self._type_by_cls = {}
        self._type_by_subclasses = {}
        self._types_with_dynamic_subclasses = {}

        def add_type(asdftype):
            self._type_by_cls[asdftype] = asdftype
            for typ in asdftype.types:
                self._type_by_cls[typ] = asdftype
                for typ2 in util.iter_subclasses(typ):
                    self._type_by_subclasses[typ2] = asdftype

            if asdftype.handle_dynamic_subclasses:
                for typ in asdftype.types:
                    self._types_with_dynamic_subclasses[typ] = asdftype

        def add_by_tag(name, version):
            tag = join_tag_version(name, version)
            if tag in index._type_by_tag:
                asdftype = index._type_by_tag[tag]
                add_type(asdftype)

        if version == 'latest':
            for name, versions in six.iteritems(index._versions_by_type_name):
                version = versions[-1]
                add_by_tag(name, version)
        else:
            try:
                version_map = versioning.get_version_map(version)
            except ValueError:
                raise ValueError(
                    "Don't know how to write out ASDF version {0}".format(
                        version))

            for name, version in six.iteritems(version_map['tags']):
                add_by_tag(name, semver.parse(version))

            # Now add any extension types that aren't known to the ASDF standard
            for name, versions in six.iteritems(index._versions_by_type_name):
                if name not in version_map:
                    version = versions[-1]
                    add_by_tag(name, version)

        for asdftype in index._unnamed_types:
            add_type(asdftype)

    def from_custom_type(self, custom_type):
        """
        Given a custom type, return the corresponding AsdfType
        definition.
        """
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


class AsdfTypeIndex(object):
    """
    An index of the known `AsdfType`s.
    """
    def __init__(self):
        self._write_type_indices = {}
        self._type_by_tag = {}
        self._versions_by_type_name = {}
        self._best_matches = {}
        self._unnamed_types = set()
        self._hooks_by_type = {}
        self._all_types = set()

    def add_type(self, asdftype):
        """
        Add a type to the index.
        """
        self._all_types.add(asdftype)

        if asdftype.yaml_tag is None and asdftype.name is None:
            return

        if isinstance(asdftype.name, list):
            yaml_tags = [asdftype.make_yaml_tag(name) for name in asdftype.name]
        elif isinstance(asdftype.name, six.string_types):
            yaml_tags = [asdftype.yaml_tag]
        elif asdftype.name is None:
            yaml_tags = []
        else:
            raise TypeError("name must be a string, list or None")

        for yaml_tag in yaml_tags:
            self._type_by_tag[yaml_tag] = asdftype
            name, version = split_tag_version(yaml_tag)
            versions = self._versions_by_type_name.get(name)
            if versions is None:
                self._versions_by_type_name[name] = [version]
            else:
                idx = bisect.bisect_left(versions, version)
                if idx == len(versions) or versions[idx] != version:
                    versions.insert(idx, version)

        if not len(yaml_tags):
            self._unnamed_types.add(asdftype)

    def from_custom_type(self, custom_type, version='latest'):
        """
        Given a custom type, return the corresponding AsdfType
        definition.
        """
        # Basic Python types should not ever have an AsdfType
        # associated with them.
        if custom_type in _BASIC_PYTHON_TYPES:
            return None

        write_type_index = self._write_type_indices.get(version)
        if write_type_index is None:
            write_type_index = _AsdfWriteTypeIndex(version, self)
            self._write_type_indices[version] = write_type_index

        return write_type_index.from_custom_type(custom_type)

    def fix_yaml_tag(self, tag):
        """
        Given a YAML tag, adjust it to the best supported version.

        If there is no exact match, this finds the newest version
        understood that is still less than the version in file.  Or,
        the earliest understood version if none are less than the
        version in the file.

        Raises a warning if it could not find a match where the major
        and minor numbers are the same.
        """
        if tag in self._type_by_tag:
            return tag

        if tag in self._best_matches:
            best_tag, warning_string = self._best_matches[tag]

            if warning_string:
                warnings.warn(warning_string)

            return best_tag

        name, version = split_tag_version(tag)
        versions = self._versions_by_type_name.get(name)
        if versions is None:
            return tag

        # The versions list is kept sorted, so bisect can be used to
        # quickly find the best option.

        i = bisect.bisect_left(versions, version)
        i = max(0, i - 1)

        best_version = versions[i]
        if best_version[:2] == version[:2]:
            # Major and minor match, so only patch and devel differs
            # -- no need for alarm
            warning_string = None
        else:
            warning_string = (
                "'{0}' with version {1} found in file, but asdf only "
                "understands version {2}.".format(
                    name,
                    semver.format_version(*version),
                    semver.format_version(*best_version)))

        if warning_string:
            warnings.warn(warning_string)

        best_tag = join_tag_version(name, best_version)
        self._best_matches[tag] = best_tag, warning_string
        return best_tag

    def from_yaml_tag(self, tag):
        """
        From a given YAML tag string, return the corresponding
        AsdfType definition.
        """
        tag = self.fix_yaml_tag(tag)
        return self._type_by_tag.get(tag)

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

    def get_hook_for_type(self, hookname, typ, version='latest'):
        """
        Get the hook function for the given type, if it exists,
        else return None.
        """
        hooks = self._hooks_by_type.setdefault(hookname, {})
        hook = hooks.get(typ, None)
        if hook is not None:
            return hook

        tag = self.from_custom_type(typ, version)
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
            types = mcls._find_in_bases(attrs, bases, 'types', [])
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

    yaml_tag : str
        The YAML tag to use for the type.  If not provided, it will be
        automatically generated from name, organization, standard and
        version.

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
    version = (1, 0, 0)
    types = []
    handle_dynamic_subclasses = False
    validators = {}
    requires = []
    yaml_tag = None

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
        return tagged.tag_object(cls.yaml_tag, obj, ctx=ctx)

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
