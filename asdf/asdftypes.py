# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import re
import bisect
import warnings
import importlib
from collections import OrderedDict

import six
from copy import copy

from functools import lru_cache

from . import tagged
from . import util
from .versioning import AsdfVersion, AsdfSpec, get_version_map, default_version


__all__ = ['format_tag', 'CustomType', 'AsdfTypeIndex']


_BASIC_PYTHON_TYPES = [str, int, float, list, dict, tuple]

# regex used to parse module name from optional version string
MODULE_RE = re.compile(r'([a-zA-Z]+)(-(\d+\.\d+\.\d+))?')


def format_tag(organization, standard, version, tag_name):
    """
    Format a YAML tag.
    """
    tag = 'tag:{0}:{1}/{2}'.format(organization, standard, tag_name)

    if version is None:
        return tag

    if isinstance(version, AsdfSpec):
        version = str(version.spec)

    return "{0}-{1}".format(tag, version)


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

    In the future, this may be renamed to _ExtensionWriteTypeIndex since it is
    not specific to classes that inherit `AsdfType`.
    """
    _version_map = None

    def __init__(self, version, index):
        self._version = version

        self._type_by_cls = {}
        self._type_by_name = {}
        self._type_by_subclasses = {}
        self._class_by_subclass = {}
        self._types_with_dynamic_subclasses = {}
        self._extension_by_cls = {}
        self._extensions_used = set()

        try:
            version_map = get_version_map(self._version)['tags']
        except ValueError:
            raise ValueError(
                "Don't know how to write out ASDF version {0}".format(
                    self._version))

        def should_overwrite(cls, new_type):
            existing_type = self._type_by_cls[cls]

            # Types that are provided by extensions from other packages should
            # only override the type index corresponding to the latest version
            # of ASDF.
            if existing_type.tag_base() != new_type.tag_base():
                return self._version == default_version

            return True

        def add_type_to_index(cls, typ):
            if cls in self._type_by_cls and not should_overwrite(cls, typ):
                return

            self._type_by_cls[cls] = typ
            self._extension_by_cls[cls] = index._extension_by_type[typ]

        def add_subclasses(typ, asdftype):
            for subclass in util.iter_subclasses(typ):
                # Do not overwrite the tag type for an existing subclass if the
                # new tag serializes a class that is higher in the type
                # hierarchy than the existing subclass.
                if subclass in self._class_by_subclass:
                    if issubclass(self._class_by_subclass[subclass], typ):
                        continue
                self._class_by_subclass[subclass] = typ
                self._type_by_subclasses[subclass] = asdftype
                self._extension_by_cls[subclass] = index._extension_by_type[asdftype]

        def add_all_types(asdftype):
            add_type_to_index(asdftype, asdftype)
            for typ in asdftype.types:
                add_type_to_index(typ, asdftype)
                add_subclasses(typ, asdftype)

            if asdftype.handle_dynamic_subclasses:
                for typ in asdftype.types:
                    self._types_with_dynamic_subclasses[typ] = asdftype

        def add_by_tag(name, version):
            tag = join_tag_version(name, version)
            if tag in index._type_by_tag:
                asdftype = index._type_by_tag[tag]
                self._type_by_name[name] = asdftype
                add_all_types(asdftype)

        # Process all types defined in the ASDF version map 
        for name, _version in version_map.items():
            add_by_tag(name, AsdfVersion(_version))

        # Now add any extension types that aren't known to the ASDF standard.
        # This expects that all types defined by ASDF will be encountered
        # before any types that are defined by external packages. This
        # allows external packages to override types that are also defined
        # by ASDF. The ordering is guaranteed due to the use of OrderedDict
        # for _versions_by_type_name, and due to the fact that the built-in
        # extension will always be processed first.
        for name, versions in index._versions_by_type_name.items():
            if name not in self._type_by_name:
                add_by_tag(name, versions[-1])

        for asdftype in index._unnamed_types:
            add_all_types(asdftype)

    def _mark_used_extension(self, custom_type):
        self._extensions_used.add(self._extension_by_cls[custom_type])

    def _process_dynamic_subclass(self, custom_type):
        for key, val in self._types_with_dynamic_subclasses.items():
            if issubclass(custom_type, key):
                self._type_by_cls[custom_type] = val
                self._mark_used_extension(key)
                return val

        return None

    def from_custom_type(self, custom_type):
        """
        Given a custom type, return the corresponding `ExtensionType`
        definition.
        """
        asdftype = None

        # Try to find an exact class match first...
        try:
            asdftype = self._type_by_cls[custom_type]
        except KeyError:
            # ...failing that, match any subclasses
            try:
                asdftype = self._type_by_subclasses[custom_type]
            except KeyError:
                # ...failing that, try any subclasses that we couldn't
                # cache in _type_by_subclasses.  This generally only
                # includes classes that are created dynamically post
                # Python-import, e.g. astropy.modeling._CompoundModel
                # subclasses.
                return self._process_dynamic_subclass(custom_type)

        if asdftype is not None:
            extension = self._extension_by_cls.get(custom_type)
            if extension is not None:
                self._mark_used_extension(custom_type)
            else:
                # Handle the case where the dynamic subclass was identified as
                # a proper subclass above, but it has not yet been registered
                # as such.
                self._process_dynamic_subclass(custom_type)

        return asdftype


class AsdfTypeIndex(object):
    """
    An index of the known `ExtensionType` classes.

    In the future this class may be renamed to ExtensionTypeIndex, since it is
    not specific to classes that inherit `AsdfType`.
    """
    def __init__(self):
        self._write_type_indices = {}
        self._type_by_tag = {}
        # Use OrderedDict here to preserve the order in which types are added
        # to the type index. Since the ASDF built-in extension is always
        # processed first, this ensures that types defined by external packages
        # will always override corresponding types that are defined by ASDF
        # itself. However, if two different external packages define tags for
        # the same type, the result is currently undefined.
        self._versions_by_type_name = OrderedDict()
        self._best_matches = {}
        self._real_tag = {}
        self._unnamed_types = set()
        self._hooks_by_type = {}
        self._all_types = set()
        self._has_warned = {}
        self._extension_by_type = {}

    def add_type(self, asdftype, extension):
        """
        Add a type to the index.
        """
        self._all_types.add(asdftype)
        self._extension_by_type[asdftype] = extension

        if asdftype.yaml_tag is None and asdftype.name is None:
            return

        if isinstance(asdftype.name, list):
            yaml_tags = [asdftype.make_yaml_tag(name) for name in asdftype.name]
        elif isinstance(asdftype.name, str):
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

    def from_custom_type(self, custom_type, version=default_version):
        """
        Given a custom type, return the corresponding `ExtensionType`
        definition.
        """
        # Basic Python types should not ever have an AsdfType associated with
        # them.
        if custom_type in _BASIC_PYTHON_TYPES:
            return None

        write_type_index = self._write_type_indices.get(str(version))
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

    def get_hook_for_type(self, hookname, typ, version=default_version):
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

    def get_extensions_used(self, version=default_version):
        write_type_index = self._write_type_indices.get(str(version))
        if write_type_index is None:
            return []

        return list(write_type_index._extensions_used)


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
    Custom class constructor for tag types.
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
                if isinstance(typ, str):
                    typ = util.resolve_name(typ)
                new_types.append(typ)
            attrs['types'] = new_types

        cls = super(ExtensionTypeMeta, mcls).__new__(mcls, name, bases, attrs)

        if hasattr(cls, 'version'):
            if not isinstance(cls.version, (AsdfVersion, AsdfSpec)):
                cls.version = AsdfVersion(cls.version)

        if hasattr(cls, 'name'):
            if isinstance(cls.name, str):
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
    def names(cls):
        """
        Returns the name(s) represented by this tag type as a list.

        While some tag types represent only a single custom type, others
        represent multiple types. In the latter case, the `name` attribute of
        the extension is actually a list, not simply a string. This method
        normalizes the value of `name` by returning a list in all cases.

        Returns
        -------
            `list` of names represented by this tag type
        """
        if cls.name is None:
            return None

        return cls.name if isinstance(cls.name, list) else [cls.name]

    @classmethod
    def make_yaml_tag(cls, name, versioned=True):
        """
        Given the name of a type, returns a string representing its YAML tag.

        Parameters
        ----------
        name : str
            The name of the type. In most cases this will correspond to the
            `name` attribute of the tag type. However, it is passed as a
            parameter since some tag types represent multiple custom
            types.

        versioned : bool
            If `True`, the tag will be versioned. Otherwise, a YAML tag without
            a version will be returned.

        Returns
        -------
            `str` representing the YAML tag
        """
        return format_tag(
            cls.organization,
            cls.standard,
            cls.version if versioned else None,
            name)

    @classmethod
    def tag_base(cls):
        """
        Returns the base of the YAML tag for types represented by this class.

        This method returns the portion of the tag that represents the standard
        and the organization of any type represented by this class.

        Returns
        -------
            `str` representing the base of the YAML tag
        """
        return cls.make_yaml_tag('', versioned=False)

    @classmethod
    def to_tree(cls, node, ctx):
        """
        Converts instances of custom types into YAML representations.

        This method should be overridden by custom extension classes in order
        to define how custom types are serialized into YAML. The method must
        return a single Python object corresponding to one of the basic YAML
        types (dict, list, str, or number). However, the types can be nested
        and combined in order to represent more complex custom types.

        This method is called as part of the process of writing an `AsdfFile`
        object. Whenever a custom type (or a subclass of that type) that is
        listed in the `types` attribute of this class is encountered, this
        method will be used to serialize that type.

        The name `to_tree` refers to the act of converting a custom type into
        part of a YAML object tree.

        Parameters
        ----------
        node : `object`
            Instance of a custom type to be serialized. Will be an instance (or
            an instance of a subclass) of one of the types listed in the
            `types` attribute of this class.

        ctx : `AsdfFile`
            An instance of the `AsdfFile` object that is being written out.

        Returns
        -------
            A basic YAML type (`dict`, `list`, `str`, `int`, `float`, or
            `complex`) representing the properties of the custom type to be
            serialized. These types can be nested in order to represent more
            complex custom types.
        """
        return node.__class__.__bases__[0](node)

    @classmethod
    def to_tree_tagged(cls, node, ctx):
        """
        Converts instances of custom types into tagged objects.

        It is more common for custom tag types to override `to_tree` instead of
        this method. This method should only be overridden if it is necessary
        to modify the YAML tag that will be used to tag this object.

        Parameters
        ----------
        node : `object`
            Instance of a custom type to be serialized. Will be an instance (or
            an instance of a subclass) of one of the types listed in the
            `types` attribute of this class.

        ctx : `AsdfFile`
            An instance of the `AsdfFile` object that is being written out.

        Returns
        -------
            An instance of `asdf.tagged.Tagged`.
        """
        obj = cls.to_tree(node, ctx)
        return tagged.tag_object(cls.yaml_tag, obj, ctx=ctx)

    @classmethod
    def from_tree(cls, tree, ctx):
        """
        Converts basic types representing YAML trees into custom types.

        This method should be overridden by custom extension classes in order
        to define how custom types are deserialized from the YAML
        representation back into their original types. The method will return
        an instance of the original custom type.

        This method is called as part of the process of reading an ASDF file in
        order to construct an `AsdfFile` object. Whenever a YAML subtree is
        encountered that has a tag that corresponds to the `yaml_tag` property
        of this class, this method will be used to deserialize that tree back
        into an instance of the original custom type.

        Parameters
        ----------
        tree : `object` representing YAML tree
            An instance of a basic Python type (possibly nested) that
            corresponds to a YAML subtree.

        ctx : `AsdfFile`
            An instance of the `AsdfFile` object that is being constructed.

        Returns
        -------
            An instance of the custom type represented by this extension class.
        """
        return cls(tree)

    @classmethod
    def from_tree_tagged(cls, tree, ctx):
        """
        Converts from tagged tree into custom type.

        It is more common for extension classes to override `from_tree` instead
        of this method. This method should only be overridden if it is
        necessary to access the `_tag` property of the `Tagged` object
        directly.

        Parameters
        ----------
        tree : `asdf.tagged.Tagged` object representing YAML tree

        ctx : `AsdfFile`
            An instance of the `AsdfFile` object that is being constructed.

        Returns
        -------
            An instance of the custom type represented by this extension class.
        """
        return cls.from_tree(tree.data, ctx)

    @classmethod
    def incompatible_version(cls, version):
        """
        Indicates if given version is known to be incompatible with this type.

        If this tag class explicitly identifies compatible versions then this
        checks whether a given version is compatible or not (see
        `supported_versions`). Otherwise, all versions are assumed to be
        compatible.

        Child classes can override this method to affect how version
        compatiblity for this type is determined.

        Parameters
        ----------
        version : `str` or `~asdf.versioning.AsdfVersion`
            The version to test for compatibility.
        """
        if cls.supported_versions:
            if version not in cls.supported_versions:
                return True
        return False


@six.add_metaclass(AsdfTypeMeta)
class AsdfType(ExtensionType):
    """
    Base class for all built-in ASDF types. Types that inherit this class will
    be automatically added to the list of built-ins. This should *not* be used
    for user-defined extensions.
    """

@six.add_metaclass(ExtensionTypeMeta)
class CustomType(ExtensionType):
    """
    Base class for all user-defined types.
    """

    # These attributes are duplicated here with docstrings since a bug in
    # sphinx prevents the docstrings of class attributes from being inherited
    # properly (see https://github.com/sphinx-doc/sphinx/issues/741. The
    # docstrings are not included anywhere else in the class hierarchy since
    # this class is the only one exposed in the public API.
    name = None
    """
    `str` or `list`: The name of the type.
    """

    organization = 'stsci.edu'
    """
    `str`: The organization responsible for the type.
    """

    standard = 'asdf'
    """
    `str`: The standard the type is defined in.
    """

    version = (1, 0, 0)
    """
    `str`, `tuple`, `AsdfVersion`, or `AsdfSpec`: The version of the type.
    """

    supported_versions = set()
    """
    `set`: Versions that explicitly compatible with this extension class.

    If provided, indicates explicit compatibility with the given set
    of versions. Other versions of the same schema that are not included in
    this set will not be converted to custom types with this class. """

    types = []
    """
    `list`: List of types that this extension class can convert to/from YAML.

    Custom Python types that, when found in the tree, will be converted into
    basic types for YAML output. Can be either strings referring to the types
    or the types themselves."""

    handle_dynamic_subclasses = False
    """
    `bool`: Indicates whether dynamically generated subclasses can be serialized

    Flag indicating whether this type is capable of serializing subclasses
    of any of the types listed in ``types`` that are generated dynamically.
    """

    validators = {}
    """
    `dict`: Mapping JSON Schema keywords to validation functions for jsonschema.

    Useful if the type defines extra types of validation that can be
    performed.
    """

    requires = []
    """
    `list`: Python packages that are required to instantiate the object.
    """

    yaml_tag = None
    """
    `str`: The YAML tag to use for the type.

    If not provided, it will be automatically generated from name,
    organization, standard and version.
    """

    has_required_modules = True
    """
    `bool`: Indicates whether modules specified by `requires` are available.

    NOTE: This value is automatically generated. Do not set it in subclasses as
    it will be overwritten.
    """
