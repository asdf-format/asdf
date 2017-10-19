# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import bisect
import importlib
import warnings
import re

import six
from copy import copy

from .compat import lru_cache

from . import tagged
from . import util
from .versioning import AsdfVersion, AsdfSpec, get_version_map


__all__ = ['format_tag', 'AsdfTypeIndex', 'AsdfType']


_BASIC_PYTHON_TYPES = set(list(six.string_types) +
                          list(six.integer_types) +
                          [float, list, dict, tuple])

# regex used to parse module name from optional version string
MODULE_RE = re.compile(r'([a-zA-Z]+)(-(\d+\.\d+\.\d+))?')


def format_tag(organization, standard, version, tag_name):
    """
    Format a YAML tag.
    """
    if isinstance(version, AsdfSpec):
        version = str(version.spec)
    return 'tag:{0}:{1}/{2}-{3}'.format(
        organization, standard, tag_name, version)


def split_tag_version(tag):
    """
    Split a tag into its base and version.
    """
    name, version = tag.rsplit('-', 1)
    version = AsdfVersion(version)
    return name, version


def join_tag_version(name, version):
    """
    Join the root and version of a tag back together.
    """
    return '{0}-{1}'.format(name, version)


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
        self._type_by_name = {}
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
                self._type_by_name[name] = asdftype
                add_type(asdftype)

        if self._version == 'latest':
            for name, versions in six.iteritems(index._versions_by_type_name):
                add_by_tag(name, versions[-1])
        else:
            try:
                version_map = get_version_map(self._version)
            except ValueError:
                raise ValueError(
                    "Don't know how to write out ASDF version {0}".format(
                        self._version))

            for name, _version in six.iteritems(version_map['tags']):
                add_by_tag(name, AsdfVersion(_version))

            # Now add any extension types that aren't known to the ASDF standard
            for name, versions in six.iteritems(index._versions_by_type_name):
                if name not in self._type_by_name:
                    add_by_tag(name, versions[-1])

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
        self._real_tag = {}
        self._unnamed_types = set()
        self._hooks_by_type = {}
        self._all_types = set()
        self._has_warned = {}

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

    def _get_version_mismatch(self, name, version, latest_version):
        warning_string = None

        if (latest_version.major, latest_version.minor) != \
                (version.major, version.minor):
            warning_string = \
                "'{}' with version {} found in file{{}}, but latest " \
                "supported version is {}".format(
                    name, version, latest_version)

        return warning_string

    def _warn_version_mismatch(self, ctx, tag, warning_string, fname):
        if warning_string is not None:
            # Ensure that only a single warning occurs per tag per AsdfFile
            # TODO: If it is useful to only have a single warning per file on
            # disk, then use `fname` in the key instead of `ctx`.
            if not (ctx, tag) in self._has_warned:
                warnings.warn(warning_string.format(fname))
                self._has_warned[(ctx, tag)] = True

    def fix_yaml_tag(self, ctx, tag, ignore_version_mismatch=True):
        """
        Given a YAML tag, adjust it to the best supported version.

        If there is no exact match, this finds the newest version
        understood that is still less than the version in file.  Or,
        the earliest understood version if none are less than the
        version in the file.

        If ``ignore_version_mismatch==False``, this function raises a warning
        if it could not find a match where the major and minor numbers are the
        same.
        """
        warning_string = None

        name, version = split_tag_version(tag)

        fname = " '{}'".format(ctx._fname) if ctx._fname else ''

        if tag in self._type_by_tag:
            asdftype = self._type_by_tag[tag]
            # Issue warnings for the case where there exists a class for the
            # given tag due to the 'supported_versions' attribute being
            # defined, but this tag is not the latest version of the type.
            # This prevents 'supported_versions' from affecting the behavior of
            # warnings that are purely related to YAML validation.
            if not ignore_version_mismatch and hasattr(asdftype, '_latest_version'):
                warning_string = self._get_version_mismatch(
                    name, version, asdftype._latest_version)
                self._warn_version_mismatch(ctx, tag, warning_string, fname)
            return tag

        if tag in self._best_matches:
            best_tag, warning_string = self._best_matches[tag]

            if not ignore_version_mismatch:
                self._warn_version_mismatch(ctx, tag, warning_string, fname)

            return best_tag

        versions = self._versions_by_type_name.get(name)
        if versions is None:
            return tag

        # The versions list is kept sorted, so bisect can be used to
        # quickly find the best option.
        i = bisect.bisect_left(versions, version)
        i = max(0, i - 1)

        if not ignore_version_mismatch:
            warning_string = self._get_version_mismatch(
                name, version, versions[-1])
            self._warn_version_mismatch(ctx, tag, warning_string, fname)

        best_version = versions[i]
        best_tag = join_tag_version(name, best_version)
        self._best_matches[tag] = best_tag, warning_string
        if tag != best_tag:
            self._real_tag[best_tag] = tag
        return best_tag

    def get_real_tag(self, tag):
        if tag in self._real_tag:
            return self._real_tag[tag]
        elif tag in self._type_by_tag:
            return tag
        return None

    def from_yaml_tag(self, ctx, tag):
        """
        From a given YAML tag string, return the corresponding
        AsdfType definition.
        """
        tag = self.fix_yaml_tag(ctx, tag)
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
    # required dependencies for an AsdfType are missing.
    plural, verb = ('s', 'are') if len(cls.requires) else ('', 'is')
    message = "{0} package{1} {2} required to instantiate '{3}'".format(
        util.human_list(cls.requires), plural, verb, tree._tag)
    # This error will be handled by yamlutil.tagged_tree_to_custom_tree, which
    # will cause a warning to be issued indicating that the tree failed to be
    # converted.
    raise TypeError(message)


class ExtensionTypeMeta(type):
    """
    Custom class constructor for extension types.
    """
    _import_cache = {}

    @classmethod
    def _has_required_modules(cls, requires):
        for string in requires:
            has_module = True
            match = MODULE_RE.match(string)
            modname, _, version = match.groups()
            if modname in cls._import_cache:
                if not cls._import_cache[modname]:
                    return False
            try:
                module = importlib.import_module(modname)
                if version and hasattr(module, '__version__'):
                    if module.__version__ < version:
                        has_module = False
            except ImportError:
                has_module = False
            finally:
                cls._import_cache[modname] = has_module
                if not has_module:
                    return False
        return True

    @classmethod
    def _find_in_bases(cls, attrs, bases, name, default=None):
        if name in attrs:
            return attrs[name]
        for base in bases:
            if hasattr(base, name):
                return getattr(base, name)
        return default

    @property
    def versioned_siblings(mcls):
        return getattr(mcls, '__versioned_siblings') or []

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

        cls = super(ExtensionTypeMeta, mcls).__new__(mcls, name, bases, attrs)

        if hasattr(cls, 'version'):
            if not isinstance(cls.version, (AsdfVersion, AsdfSpec)):
                cls.version = AsdfVersion(cls.version)

        if hasattr(cls, 'name'):
            if isinstance(cls.name, six.string_types):
                if 'yaml_tag' not in attrs:
                    cls.yaml_tag = cls.make_yaml_tag(cls.name)
            elif isinstance(cls.name, list):
                pass
            elif cls.name is not None:
                raise TypeError("name must be string or list")

        if hasattr(cls, 'supported_versions'):
            if not isinstance(cls.supported_versions, (list, set)):
                cls.supported_versions = [cls.supported_versions]
            supported_versions = set()
            for version in cls.supported_versions:
                if not isinstance(version, (AsdfVersion, AsdfSpec)):
                    version = AsdfVersion(version)
                # This should cause an exception for invalid input
                supported_versions.add(version)
            # We need to convert back to a list here so that the 'in' operator
            # uses actual comparison instead of hash equality
            cls.supported_versions = list(supported_versions)
            siblings = list()
            for version in cls.supported_versions:
                if version != cls.version:
                    new_attrs = copy(attrs)
                    new_attrs['version'] = version
                    new_attrs['supported_versions'] = set()
                    new_attrs['_latest_version'] = cls.version
                    siblings.append(
                       ExtensionTypeMeta. __new__(mcls, name, bases, new_attrs))
            setattr(cls, '__versioned_siblings', siblings)

        return cls


class AsdfTypeMeta(ExtensionTypeMeta):
    """
    Keeps track of `AsdfType` subclasses that are created, and stores them in
    `AsdfTypeIndex`.
    """
    def __new__(mcls, name, bases, attrs):
        cls = super(AsdfTypeMeta, mcls).__new__(mcls, name, bases, attrs)
        # Classes using this metaclass get added to the list of built-in
        # extensions
        _all_asdftypes.add(cls)

        return cls


class ExtensionType(object):
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

    supported_versions : set
        If provided, indicates explicit compatibility with the given set of
        versions. Other versions of the same schema that are not included in
        this set will not be converted to custom types with this class.

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
    supported_versions = set()
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
            cls.version,
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

    @classmethod
    def incompatible_version(cls, version):
        """
        If this tag class explicitly identifies compatible versions then this
        checks whether a given version is compatible or not. Otherwise, all
        versions are assumed to be compatible.

        Child classes can override this method to affect how version
        compatiblity for this type is determined.
        """
        if cls.supported_versions:
            if version not in cls.supported_versions:
                return True
        return False


@six.add_metaclass(AsdfTypeMeta)
@six.add_metaclass(util.InheritDocstrings)
class AsdfType(ExtensionType):
    """
    Base class for all built-in ASDF types. Types that inherit this class will
    be automatically added to the list of built-ins. This should *not* be used
    for user-defined extensions.
    """

@six.add_metaclass(ExtensionTypeMeta)
@six.add_metaclass(util.InheritDocstrings)
class CustomType(ExtensionType):
    """
    Base class for all user-defined types. Unlike classes that inherit
    AsdfType, classes that inherit this class will *not* automatically be added
    to the list of built-ins. This should be used for user-defined extensions.
    """
