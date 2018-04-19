# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import abc
import warnings
from pkg_resources import iter_entry_points

import six
import importlib

from . import asdftypes
from . import resolver
from .util import get_class_name
from .exceptions import AsdfDeprecationWarning


__all__ = ['AsdfExtension', 'AsdfExtensionList']


@six.add_metaclass(abc.ABCMeta)
class AsdfExtension(object):
    """
    Abstract base class defining an extension to ASDF.
    """
    @classmethod
    def __subclasshook__(cls, C):
        if cls is AsdfExtension:
            return (hasattr(C, 'types') and
                    hasattr(C, 'tag_mapping') and
                    hasattr(C, 'url_mapping'))
        return NotImplemented

    @abc.abstractproperty
    def types(self):
        """
        A list of `asdf.CustomType` subclasses that describe how to store
        custom objects to and from ASDF.
        """
        pass

    @abc.abstractproperty
    def tag_mapping(self):
        """
        A list of 2-tuples or callables mapping YAML tag prefixes to JSON Schema
        URL prefixes.

        For each entry:

        - If a 2-tuple, the first part of the tuple is a YAML tag
          prefix to match.  The second part is a string, where case
          the following are available as Python formatting tokens:

          - ``{tag}``: the complete YAML tag.
          - ``{tag_suffix}``: the part of the YAML tag after the
            matched prefix.
          - ``{tag_prefix}``: the matched YAML tag prefix.

        - If a callable, it is passed the entire YAML tag must return
          the entire JSON schema URL if it matches, otherwise, return `None`.

        Note that while JSON Schema URLs uniquely define a JSON
        Schema, they do not have to actually exist on an HTTP server
        and be fetchable (much like XML namespaces).

        For example, to match all YAML tags with the
        ``tag:nowhere.org:custom` prefix to the
        ``http://nowhere.org/schemas/custom/`` URL prefix::

           return [('tag:nowhere.org:custom/',
                    'http://nowhere.org/schemas/custom/{tag_suffix}')]
        """
        pass

    @abc.abstractproperty
    def url_mapping(self):
        """
        A list of 2-tuples or callables mapping JSON Schema URLs to
        other URLs.  This is useful if the JSON Schemas are not
        actually fetchable at their corresponding URLs but are on the
        local filesystem, or, to save bandwidth, we have a copy of
        fetchable schemas on the local filesystem.  If neither is
        desirable, it may simply be the empty list.

        For each entry:

        - If a 2-tuple, the first part is a URL prefix to match.  The
          second part is a string, where the following are available
          as Python formatting tokens:

          - ``{url}``: The entire JSON schema URL
          - ``{url_prefix}``: The matched URL prefix
          - ``{url_suffix}``: The part of the URL after the prefix.

        - If a callable, it is passed the entire JSON Schema URL and
          must return a resolvable URL pointing to the schema content.
          If it doesn't match, should return `None`.

        For example, to map a remote HTTP URL prefix to files installed
        alongside as data alongside Python module::

            return [('http://nowhere.org/schemas/custom/1.0.0/',
                    asdf.util.filepath_to_url(
                        os.path.join(SCHEMA_PATH, 'stsci.edu')) +
                    '/{url_suffix}.yaml'
                   )]
        """
        pass


class AsdfExtensionList(object):
    """
    Manage a set of extensions that are in effect.
    """
    def __init__(self, extensions):
        tag_mapping = []
        url_mapping = []
        validators = {}
        self._type_index = asdftypes.AsdfTypeIndex()
        for extension in extensions:
            if not isinstance(extension, AsdfExtension):
                raise TypeError(
                    "Extension must implement asdftypes.AsdfExtension "
                    "interface")
            tag_mapping.extend(extension.tag_mapping)
            url_mapping.extend(extension.url_mapping)
            for typ in extension.types:
                self._type_index.add_type(typ, extension)
                validators.update(typ.validators)
                for sibling in typ.versioned_siblings:
                    self._type_index.add_type(sibling, extension)
                    validators.update(sibling.validators)
        self._tag_mapping = resolver.Resolver(tag_mapping, 'tag')
        self._url_mapping = resolver.Resolver(url_mapping, 'url')
        self._validators = validators

    @property
    def tag_to_schema_resolver(self):
        """Deprecated. Use `tag_mapping` instead"""
        warnings.warn(
            "The 'tag_to_schema_resolver' property is deprecated. Use "
            "'tag_mapping' instead.",
            AsdfDeprecationWarning)
        return self._tag_mapping

    @property
    def tag_mapping(self):
        return self._tag_mapping

    @property
    def url_mapping(self):
        return self._url_mapping

    @property
    def type_index(self):
        return self._type_index

    @property
    def validators(self):
        return self._validators


class BuiltinExtension(object):
    """
    This is the "extension" to ASDF that includes all the built-in
    tags.  Even though it's not really an extension and it's always
    available, it's built in the same way as an extension.
    """
    @property
    def types(self):
        return asdftypes._all_asdftypes

    @property
    def tag_mapping(self):
        return resolver.DEFAULT_TAG_TO_URL_MAPPING

    @property
    def url_mapping(self):
        return resolver.DEFAULT_URL_MAPPING


class _DefaultExtensions:
    def __init__(self):
        self._extensions = []
        self._extension_list = None
        self._package_metadata = {}

    def _load_installed_extensions(self, group='asdf_extensions'):
        self._extensions = []
        for entry_point in iter_entry_points(group=group):
            ext = entry_point.load()
            if not issubclass(ext, AsdfExtension):
                warnings.warn("Found entry point {}, from {} but it is not a "
                              "subclass of AsdfExtension, as expected. It is "
                              "being ignored.".format(ext, entry_point.dist))
                continue

            dist = entry_point.dist
            name = get_class_name(ext, instance=False)
            self._package_metadata[name] = (dist.project_name, dist.version)
            self._extensions.append(ext())

    @property
    def extensions(self):
        # This helps avoid a circular dependency with external packages
        if not self._extensions:
            self._load_installed_extensions()

        return self._extensions

    @property
    def extension_list(self):
        if self._extension_list is None:
            self._extension_list = AsdfExtensionList(self.extensions)

        return self._extension_list

    @property
    def package_metadata(self):
        return self._package_metadata

default_extensions = _DefaultExtensions()
