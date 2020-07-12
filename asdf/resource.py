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


__all__ = [
    "DirectoryResourceMapping",
    "ResourceManager",
    "JsonschemaResourceMapping",
    "get_core_resource_mappings",
]


class DirectoryResourceMapping(Mapping):
    """
    Resource mapping that reads resource content
    from a directory or directory tree.

    Parameters
    ----------
    root : str or importlib.resources.abc.Traversable
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
        Defaults to "*.yaml".
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
    resource_mappings : list of collections.abc.Mapping
        Underlying resource mappings.  In the case of
        a duplicate URI, the latest mapping in the list
        will override.
    """
    def __init__(self, resource_mappings):
        self._resource_mappings = resource_mappings

        self._mappings_by_uri = {}
        for mapping in resource_mappings:
            for uri in mapping:
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

    return [
        DirectoryResourceMapping(core_schemas_root, "http://stsci.edu/schemas", recursive=True),
        JsonschemaResourceMapping(),
    ]
