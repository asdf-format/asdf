"""
Support for plugins that provide access to resources such
as schemas.
"""
from collections.abc import Mapping
from pathlib import Path
import fnmatch
import os
import pkgutil
import sys

if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources

import asdf

from .util import get_class_name


__all__ = [
    "ResourceMappingProxy",
    "DirectoryResourceMapping",
    "ResourceManager",
    "JsonschemaResourceMapping",
    "get_core_resource_mappings",
]


class ResourceMappingProxy(Mapping):
    """
    Wrapper around a resource mapping that carries
    additional information on the package that provided
    the mapping.
    """
    @classmethod
    def maybe_wrap(self, delegate):
        if isinstance(delegate, ResourceMappingProxy):
            return delegate
        else:
            return ResourceMappingProxy(delegate)

    def __init__(self, delegate, package_name=None, package_version=None):
        if not isinstance(delegate, Mapping):
            raise TypeError("Resource mapping must implement the Mapping interface")

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
        """"
        Get the fully qualified class name of the mapping.

        Returns
        -------
        str
        """
        return self._class_name

    def __eq__(self, other):
        if isinstance(other, ResourceMappingProxy):
            return other.delegate is self.delegate
        else:
            return False

    def __hash__(self):
        return hash(id(self.delegate))

    def __repr__(self):
        if self.package_name is not None:
            package_description = "{}=={}".format(self.package_name, self.package_version)
        else:
            package_description = "(none)"

        return "<ResourceMappingProxy class: {} package: {} len: {}>".format(
            self.class_name,
            package_description,
            len(self),
        )


class DirectoryResourceMapping(Mapping):
    """
    Resource mapping that reads resource content
    from a directory or directory tree.

    Parameters
    ----------
    root : str or importlib.abc.Traversable
        Root directory (or directory-like Traversable) of the resource
        files.  `str` will be interpreted as a filesystem path.
    uri_prefix : str
        Prefix used to construct URIs from file paths.  The
        prefix will be prepended to paths relative to the root
        directory.
    recursive : bool, optional
        If `True`, recurse into subdirectories.  Defaults to `False`.
    filename_pattern : str, optional
        Glob pattern that identifies relevant filenames.
        Defaults to `"*.yaml"`.
    stem_filename : bool, optional
        If `True`, remove the filename's extension when
        constructing its URI.
    """
    def __init__(self, root, uri_prefix, recursive=False, filename_pattern="*.yaml", stem_filename=True):
        self._uri_to_file = {}
        self._recursive = recursive
        self._filename_pattern = filename_pattern
        self._stem_filename = stem_filename

        if isinstance(root, str):
            self._root = Path(root)
        else:
            self._root = root

        if uri_prefix.endswith("/"):
            self._uri_prefix = uri_prefix[:-1]
        else:
            self._uri_prefix = uri_prefix

        for file, path_components in self._iterate_files(self._root, []):
            self._uri_to_file[self._make_uri(file, path_components)] = file

    def _iterate_files(self, directory, path_components):
        for obj in directory.iterdir():
            if obj.is_file() and fnmatch.fnmatch(obj.name, self._filename_pattern):
                yield obj, path_components
            elif obj.is_dir() and self._recursive:
                yield from self._iterate_files(obj, path_components + [obj.name])

    def _make_uri(self, file, path_components):
        if self._stem_filename:
            filename = os.path.splitext(file.name)[0]
        else:
            filename = file.name

        return "/".join([self._uri_prefix] + path_components + [filename])

    def __getitem__(self, uri):
        return self._uri_to_file[uri].read_bytes()

    def __len__(self):
        return len(self._uri_to_file)

    def __iter__(self):
        yield from self._uri_to_file

    def __repr__(self):
        return "{}({!r}, {!r}, recursive={!r}, filename_pattern={!r}, stem_filename={!r})".format(
            self.__class__.__name__,
            self._root,
            self._uri_prefix,
            self._recursive,
            self._filename_pattern,
            self._stem_filename,
        )


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
            raise KeyError("Resource unavailable for URI: {}".format(uri))

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
        return "<ResourceManager len: {}>".format(self.__len__())


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
        return pkgutil.get_data("jsonschema", "schemas/{}".format(filename))

    def __len__(self):
        return len(_JSONSCHEMA_URI_TO_FILENAME)

    def __iter__(self):
        yield from _JSONSCHEMA_URI_TO_FILENAME

    def __repr__(self):
        return "JsonschemaResourceMapping()"


def get_core_resource_mappings():
    """
    Get the resource mapping instances for the core schemas.
    This method is registered with the asdf.resource_mappings entry point.
    """
    core_schemas_root = importlib_resources.files(asdf)/"schemas"/"stsci.edu"
    if not core_schemas_root.is_dir():
        # In an editable install, the schemas can be found in the
        # asdf-standard submodule.
        core_schemas_root = Path(__file__).parent.parent/"asdf-standard"/"schemas"/"stsci.edu"
        if not core_schemas_root.is_dir():
            raise RuntimeError("Unable to locate core schemas")

    resources_root = importlib_resources.files(asdf)/"resources"
    if not resources_root.is_dir():
        # In an editable install, the resources can be found in the
        # asdf-standard submodule.
        resources_root = Path(__file__).parent.parent/"asdf-standard"/"resources"
        if not resources_root.is_dir():
            raise RuntimeError("Unable to locate core resources")

    return [
        DirectoryResourceMapping(core_schemas_root, "http://stsci.edu/schemas", recursive=True),
        DirectoryResourceMapping(resources_root / "asdf-format.org", "asdf://asdf-format.org", recursive=True),
        JsonschemaResourceMapping(),
    ]
