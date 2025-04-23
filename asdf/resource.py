"""
Support for plugins that provide access to resources such
as schemas.
"""

import pkgutil
from collections.abc import Mapping

from asdf_standard import DirectoryResourceMapping as _DirectoryResourceMapping

from .util import get_class_name

__all__ = [
    "DirectoryResourceMapping",
    "JsonschemaResourceMapping",
    "ResourceManager",
    "ResourceMappingProxy",
]


class DirectoryResourceMapping(_DirectoryResourceMapping):
    """
    A resource mapping that reads resource content from a directory or directory tree.

    See :class:`~asdf_standard.resource.DirectoryResourceMapping` for details.
    """


class ResourceMappingProxy(Mapping):
    """
    Wrapper around a resource mapping that carries
    additional information on the package that provided
    the mapping.
    """

    @classmethod
    def maybe_wrap(cls, delegate):
        if isinstance(delegate, ResourceMappingProxy):
            return delegate

        return ResourceMappingProxy(delegate)

    def __init__(self, delegate, package_name=None, package_version=None):
        if not isinstance(delegate, Mapping):
            msg = "Resource mapping must implement the Mapping interface"
            raise TypeError(msg)

        self._delegate = delegate
        self._package_name = package_name
        self._package_version = package_version
        self._class_name = get_class_name(delegate)

    def __getitem__(self, uri):
        return self._delegate.__getitem__(uri)

    def __len__(self):
        return self._delegate.__len__()

    def __iter__(self):
        return self._delegate.__iter__()

    @property
    def delegate(self):
        """
        Get the wrapped mapping instance.

        Returns
        -------
        collections.abc.Mapping
        """
        return self._delegate

    @property
    def package_name(self):
        """
        Get the name of the Python package that provided this mapping.

        Returns
        -------
        str or None
            `None` if the mapping was added at runtime.
        """
        return self._package_name

    @property
    def package_version(self):
        """
        Get the version of the Python package that provided the mapping.

        Returns
        -------
        str or None
            `None` if the mapping was added at runtime.
        """
        return self._package_version

    @property
    def class_name(self):
        """ "
        Get the fully qualified class name of the mapping.

        Returns
        -------
        str
        """
        return self._class_name

    def __eq__(self, other):
        if isinstance(other, ResourceMappingProxy):
            return other.delegate is self.delegate

        return False

    def __hash__(self):
        return hash(id(self.delegate))

    def __repr__(self):
        if self.package_name is not None:
            package_description = f"{self.package_name}=={self.package_version}"
        else:
            package_description = "(none)"

        return f"<ResourceMappingProxy class: {self.class_name} package: {package_description} len: {len(self)}>"


class ResourceManager(Mapping):
    """
    Wraps multiple resource mappings into a single interface
    with some friendlier error handling.

    Parameters
    ----------
    resource_mappings : iterable of collections.abc.Mapping
        Underlying resource mappings.  In the case of a duplicate URI,
        the first mapping takes precedence.
    """

    def __init__(self, resource_mappings):
        self._resource_mappings = resource_mappings

        self._mappings_by_uri = {}
        for mapping in resource_mappings:
            for uri in mapping:
                if uri not in self._mappings_by_uri:
                    self._mappings_by_uri[uri] = mapping

    def __getitem__(self, uri):
        if uri not in self._mappings_by_uri:
            msg = f"Resource unavailable for URI: {uri}"
            raise KeyError(msg)

        content = self._mappings_by_uri[uri][uri]
        if isinstance(content, str):
            content = content.encode("utf-8")

        return content

    def __len__(self):
        return len(self._mappings_by_uri)

    def __iter__(self):
        yield from self._mappings_by_uri

    def __contains__(self, uri):
        # Implement __contains__ only for efficiency.
        return uri in self._mappings_by_uri

    def __repr__(self):
        return f"<ResourceManager len: {self.__len__()}>"


_JSONSCHEMA_URI_TO_FILENAME = {
    "http://json-schema.org/draft-04/schema": "draft4.json",
}


class JsonschemaResourceMapping(Mapping):
    """
    Resource mapping that fetches metaschemas from
    the jsonschema package.
    """

    def __getitem__(self, uri):
        filename = _JSONSCHEMA_URI_TO_FILENAME[uri]
        return pkgutil.get_data("asdf._jsonschema", f"schemas/{filename}")

    def __len__(self):
        return len(_JSONSCHEMA_URI_TO_FILENAME)

    def __iter__(self):
        yield from _JSONSCHEMA_URI_TO_FILENAME

    def __repr__(self):
        return "JsonschemaResourceMapping()"
