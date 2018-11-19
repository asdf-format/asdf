# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import bisect
import warnings
from functools import lru_cache
from collections import OrderedDict

from . import util
from .versioning import (AsdfVersion, get_version_map, default_version,
                         split_tag_version, join_tag_version)


__all__ = ['AsdfTypeIndex']


_BASIC_PYTHON_TYPES = [str, int, float, list, dict, tuple]


class _AsdfWriteTypeIndex:
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
            version_map = get_version_map(self._version)
            core_version_map = version_map['core']
            standard_version_map = version_map['standard']
        except ValueError:
            raise ValueError(
                "Don't know how to write out ASDF version {0}".format(
                    self._version))

        # Process all types defined in the ASDF version map. It is important to
        # make sure that tags that are associated with the core part of the
        # standard are processed first in order to handle subclasses properly.
        for name, _version in core_version_map.items():
            self._add_by_tag(index, name, AsdfVersion(_version))
        for name, _version in standard_version_map.items():
            self._add_by_tag(index, name, AsdfVersion(_version))

        # Now add any extension types that aren't known to the ASDF standard.
        # This expects that all types defined by ASDF will be encountered
        # before any types that are defined by external packages. This
        # allows external packages to override types that are also defined
        # by ASDF. The ordering is guaranteed due to the use of OrderedDict
        # for _versions_by_type_name, and due to the fact that the built-in
        # extension will always be processed first.
        for name, versions in index._versions_by_type_name.items():
            if name not in self._type_by_name:
                self._add_by_tag(index, name, versions[-1])

        for asdftype in index._unnamed_types:
            self._add_all_types(index, asdftype)

    def _should_overwrite(self, cls, new_type):
        existing_type = self._type_by_cls[cls]

        # Types that are provided by extensions from other packages should
        # only override the type index corresponding to the latest version
        # of ASDF.
        if existing_type.tag_base() != new_type.tag_base():
            return self._version == default_version

        return True

    def _add_type_to_index(self, index, cls, typ):
        if cls in self._type_by_cls and not self._should_overwrite(cls, typ):
            return

        self._type_by_cls[cls] = typ
        self._extension_by_cls[cls] = index._extension_by_type[typ]

    def _add_subclasses(self, index, typ, asdftype):
        for subclass in util.iter_subclasses(typ):
            # Do not overwrite the tag type for an existing subclass if the
            # new tag serializes a class that is higher in the type
            # hierarchy than the existing subclass.
            if subclass in self._class_by_subclass:
                if issubclass(self._class_by_subclass[subclass], typ):
                    # Allow for cases where a subclass tag is being
                    # overridden by a tag from another extension.
                    if (self._extension_by_cls[subclass] ==
                            index._extension_by_type[asdftype]):
                        continue
            self._class_by_subclass[subclass] = typ
            self._type_by_subclasses[subclass] = asdftype
            self._extension_by_cls[subclass] = index._extension_by_type[asdftype]

    def _add_all_types(self, index, asdftype):
        self._add_type_to_index(index, asdftype, asdftype)
        for typ in asdftype.types:
            self._add_type_to_index(index, typ, asdftype)
            self._add_subclasses(index, typ, asdftype)

        if asdftype.handle_dynamic_subclasses:
            for typ in asdftype.types:
                self._types_with_dynamic_subclasses[typ] = asdftype

    def _add_by_tag(self, index, name, version):
        tag = join_tag_version(name, version)
        if tag in index._type_by_tag:
            asdftype = index._type_by_tag[tag]
            self._type_by_name[name] = asdftype
            self._add_all_types(index, asdftype)

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


class AsdfTypeIndex:
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
