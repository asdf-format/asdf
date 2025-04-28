"""
Methods for getting and setting asdf global configuration
options.
"""

import collections
import copy
import threading
import warnings
from contextlib import contextmanager

from . import _entry_points, util, versioning
from ._helpers import validate_version
from .exceptions import AsdfDeprecationWarning
from .extension import ExtensionProxy
from .resource import ResourceManager, ResourceMappingProxy

__all__ = ["AsdfConfig", "config_context", "get_config"]


DEFAULT_VALIDATE_ON_READ = True
DEFAULT_DEFAULT_VERSION = str(versioning.default_version)
DEFAULT_LEGACY_FILL_SCHEMA_DEFAULTS = True
DEFAULT_IO_BLOCK_SIZE = -1  # auto
DEFAULT_ARRAY_INLINE_THRESHOLD = None
DEFAULT_ALL_ARRAY_STORAGE = None
DEFAULT_ALL_ARRAY_COMPRESSION = "input"
DEFAULT_ALL_ARRAY_COMPRESSION_KWARGS = None
DEFAULT_DEFAULT_ARRAY_SAVE_BASE = True
DEFAULT_CONVERT_UNKNOWN_NDARRAY_SUBCLASSES = False
DEFAULT_LAZY_TREE = False


class AsdfConfig:
    """
    Container for ASDF configuration options.  Users are not intended to
    construct this object directly; instead, use the `asdf.get_config` and
    `asdf.config_context` module methods.
    """

    def __init__(self):
        self._resource_mappings = None
        self._resource_manager = None
        self._extensions = None
        self._validate_on_read = DEFAULT_VALIDATE_ON_READ
        self._default_version = DEFAULT_DEFAULT_VERSION
        self._legacy_fill_schema_defaults = DEFAULT_LEGACY_FILL_SCHEMA_DEFAULTS
        self._io_block_size = DEFAULT_IO_BLOCK_SIZE
        self._array_inline_threshold = DEFAULT_ARRAY_INLINE_THRESHOLD
        self._all_array_storage = DEFAULT_ALL_ARRAY_STORAGE
        self._all_array_compression = DEFAULT_ALL_ARRAY_COMPRESSION
        self._all_array_compression_kwargs = DEFAULT_ALL_ARRAY_COMPRESSION_KWARGS
        self._default_array_save_base = DEFAULT_DEFAULT_ARRAY_SAVE_BASE
        self._convert_unknown_ndarray_subclasses = DEFAULT_CONVERT_UNKNOWN_NDARRAY_SUBCLASSES
        self._lazy_tree = DEFAULT_LAZY_TREE

        self._lock = threading.RLock()

    @property
    def resource_mappings(self):
        """
        Get the list of registered resource mapping instances.  Unless
        overridden by user configuration, this list contains every mapping
        registered with an entry point.

        Returns
        -------
        list of asdf.resource.ResourceMappingProxy
        """
        if self._resource_mappings is None:
            with self._lock:
                if self._resource_mappings is None:
                    self._resource_mappings = _entry_points.get_resource_mappings()
        return self._resource_mappings

    def add_resource_mapping(self, mapping):
        """
        Register a new resource mapping.  The new mapping will
        take precedence over all previously registered mappings.

        Parameters
        ----------
        mapping : collections.abc.Mapping
            Map of `str` resource URI to `bytes` content
        """
        with self._lock:
            mapping = ResourceMappingProxy.maybe_wrap(mapping)

            # Insert at the beginning of the list so that
            # ResourceManager uses the new mapping first.
            resource_mappings = [mapping] + [r for r in self.resource_mappings if r != mapping]
            self._resource_mappings = resource_mappings
            self._resource_manager = None

    def remove_resource_mapping(self, mapping=None, *, package=None):
        """
        Remove a registered resource mapping.

        Parameters
        ----------
        mapping : collections.abc.Mapping, optional
            Mapping to remove.
        package : str, optional
            Remove only extensions provided by this package.  If the ``mapping``
            argument is omitted, then all mappings from this package will
            be removed.
        """
        if mapping is None and package is None:
            msg = "Must specify at least one of mapping or package"
            raise ValueError(msg)

        if mapping is not None:
            mapping = ResourceMappingProxy.maybe_wrap(mapping)

        def _remove_condition(m):
            result = True
            if mapping is not None:
                result = result and m == mapping
            if package is not None:
                result = result and m.package_name == package

            return result

        with self._lock:
            self._resource_mappings = [m for m in self.resource_mappings if not _remove_condition(m)]
            self._resource_manager = None

    def reset_resources(self):
        """
        Reset registered resource mappings to the default list
        provided as entry points.
        """
        with self._lock:
            self._resource_mappings = None
            self._resource_manager = None

    @property
    def resource_manager(self):
        """
        Get the `asdf.resource.ResourceManager` instance.  Includes resources from
        registered resource mappings and any mappings added at runtime.

        Returns
        -------
        `asdf.resource.ResourceManager`
        """
        if self._resource_manager is None:
            with self._lock:
                if self._resource_manager is None:
                    self._resource_manager = ResourceManager(self.resource_mappings)
        return self._resource_manager

    @property
    def extensions(self):
        """
        Get the list of registered extensions.

        Returns
        -------
        list of asdf.extension.ExtensionProxy
        """
        if self._extensions is None:
            with self._lock:
                if self._extensions is None:
                    self._extensions = _entry_points.get_extensions()
        return self._extensions

    def add_extension(self, extension):
        """
        Register a new extension.  The new extension will
        take precedence over all previously registered extensions.

        Parameters
        ----------
        extension : asdf.extension.Extension
        """
        with self._lock:
            extension = ExtensionProxy.maybe_wrap(extension)
            self._extensions = [extension] + [e for e in self.extensions if e != extension]

    def remove_extension(self, extension=None, *, package=None):
        """
        Remove a registered extension.

        Parameters
        ----------
        extension : asdf.extension.Extension or str, optional
            An extension instance or URI pattern to remove.
        package : str, optional
            Remove only extensions provided by this package.  If the ``extension``
            argument is omitted, then all extensions from this package will
            be removed.
        """
        if extension is None and package is None:
            msg = "Must specify at least one of extension or package"
            raise ValueError(msg)

        if extension is not None and not isinstance(extension, str):
            extension = ExtensionProxy.maybe_wrap(extension)

        def _remove_condition(e):
            result = True

            if isinstance(extension, str):
                result = result and util.uri_match(extension, e.extension_uri)
            elif isinstance(extension, ExtensionProxy):
                result = result and e == extension

            if package is not None:
                result = result and e.package_name == package

            return result

        with self._lock:
            self._extensions = [e for e in self.extensions if not _remove_condition(e)]

    def reset_extensions(self):
        """
        Reset extensions to the default list registered via entry points.
        """
        with self._lock:
            self._extensions = None

    @property
    def default_version(self):
        """
        Get the default ASDF Standard version used for
        new files.

        Returns
        -------
        str
        """
        return self._default_version

    @default_version.setter
    def default_version(self, value):
        """
        Set the default ASDF Standard version used for
        new files.

        Parameters
        ----------
        value : str
        """
        self._default_version = validate_version(value)

    @property
    def io_block_size(self):
        """
        Get the block size used when reading and writing
        files.

        Returns
        -------
        int
            Block size, or -1 to use the filesystem's
            preferred block size.
        """
        return self._io_block_size

    @io_block_size.setter
    def io_block_size(self, value):
        """
        Set the block size used when reading and writing
        files.

        Parameters
        ----------
        value : int
            Block size, or -1 to use the filesystem's
            preferred block size.
        """
        self._io_block_size = value

    @property
    def legacy_fill_schema_defaults(self):
        """
        Get the configuration that controls filling defaults
        from schemas for older ASDF Standard versions.  If
        `True`, missing default values will be filled from the
        schema when reading files from ASDF Standard <= 1.5.0.
        Later versions of the standard do not support removing
        or filling schema defaults.

        Returns
        -------
        bool
        """
        return self._legacy_fill_schema_defaults

    @legacy_fill_schema_defaults.setter
    def legacy_fill_schema_defaults(self, value):
        """
        Set the flag that controls filling defaults from
        schemas for older ASDF Standard versions.

        Parameters
        ----------
        value : bool
        """
        self._legacy_fill_schema_defaults = value

    @property
    def array_inline_threshold(self):
        """
        Get the threshold below which arrays are automatically written
        as inline YAML literals instead of binary blocks.  This number
        is compared to number of elements in the array.

        Returns
        -------
        int or None
            Integer threshold, or None to disable automatic selection
            of the array storage type.
        """
        return self._array_inline_threshold

    @array_inline_threshold.setter
    def array_inline_threshold(self, value):
        """
        Set the threshold below which arrays are automatically written
        as inline YAML literals instead of binary blocks.  This number
        is compared to number of elements in the array.

        Parameters
        ----------
        value : int or None
            Integer threshold, or None to disable automatic selection
            of the array storage type.
        """
        self._array_inline_threshold = value

    @property
    def all_array_storage(self):
        """
        Override the array storage type of all blocks
        in the file immediately before writing.  Must be one of the
        following strings or `None`:

        - ``internal``: The default.  The array data will be
          stored in a binary block in the same ASDF file.

        - ``external``: Store the data in a binary block in a
          separate ASDF file.

        - ``inline``: Store the data as YAML inline in the tree.
        """
        return self._all_array_storage

    @all_array_storage.setter
    def all_array_storage(self, value):
        if value not in (None, "internal", "external", "inline"):
            msg = f"Invalid value for all_array_storage: '{value}'"
            raise ValueError(msg)
        self._all_array_storage = value

    @property
    def all_array_compression(self):
        """
        Override the compression type on all binary blocks in the
        file.  Must be one of the following strings, `None` or a
        label supported by a `asdf.extension.Compressor`:

        - ``''`` or `None`: No compression.

        - ``zlib``: Use zlib compression.

        - ``bzp2``: Use bzip2 compression.

        - ``lz4``: Use lz4 compression.

        - ``input``: Use the same compression as in the file read.
          If there is no prior file, acts as None
        """
        return self._all_array_compression

    @all_array_compression.setter
    def all_array_compression(self, value):
        # local to avoid circular import
        from asdf._compression import validate

        self._all_array_compression = validate(value)

    @property
    def all_array_compression_kwargs(self):
        """
        Dictionary of keyword arguments provided to the compressor during
        block compression (or `None` for no keyword arguments)
        """
        return self._all_array_compression_kwargs

    @all_array_compression_kwargs.setter
    def all_array_compression_kwargs(self, value):
        if value is not None and not isinstance(value, collections.abc.Mapping):
            msg = f"Invalid value for all_array_compression_kwargs: '{value}'"
            raise ValueError(msg)
        self._all_array_compression_kwargs = value

    @property
    def default_array_save_base(self):
        """
        Option to control if when saving arrays the base array should be
        saved (so views of the same array will refer to offsets/strides of the
        same block).
        """
        return self._default_array_save_base

    @default_array_save_base.setter
    def default_array_save_base(self, value):
        if not isinstance(value, bool):
            msg = "default_array_save_base must be a bool"
            raise ValueError(msg)
        self._default_array_save_base = value

    @property
    def validate_on_read(self):
        """
        Get configuration that controls schema validation of
        ASDF files on read.

        Returns
        -------
        bool
        """
        return self._validate_on_read

    @validate_on_read.setter
    def validate_on_read(self, value):
        """
        Set the configuration that controls schema validation of
        ASDF files on read.  If `True`, newly opened files will
        be validated.

        Parameters
        ----------
        value : bool
        """
        self._validate_on_read = value

    @property
    def convert_unknown_ndarray_subclasses(self):
        """
        Get configuration that controls if ndarray subclasses
        (subclasses that aren't otherwise handled by a specific
        converter) are serialized as ndarray. If `True`, instances
        of these subclasses will appear in ASDF files as ndarrays
        and when loaded, will load as ndarrays.

        Note that these conversions will result in an
        AsdfConversionWarning being issued as this support for
        converting subclasses will be removed in a future version
        of ASDF.

        Returns
        -------
        bool
        """
        return self._convert_unknown_ndarray_subclasses

    @convert_unknown_ndarray_subclasses.setter
    def convert_unknown_ndarray_subclasses(self, value):
        if value:
            msg = (
                "Enabling convert_unknown_ndarray_subclasses is deprecated. "
                "Please add a Converter or install an extension that supports "
                "the ndarray subclass you'd like to convert"
            )
            warnings.warn(msg, AsdfDeprecationWarning)
        self._convert_unknown_ndarray_subclasses = value

    @property
    def lazy_tree(self):
        """
        Get configuration that controls if ASDF tree contents
        are lazily converted to custom objects or if all custom
        objects are created when the file is opened. See the
        ``lazy_tree`` argument for `asdf.open`.

        Returns
        -------
        bool
        """
        return self._lazy_tree

    @lazy_tree.setter
    def lazy_tree(self, value):
        self._lazy_tree = value

    def __repr__(self):
        return (
            "<AsdfConfig\n"
            f"  array_inline_threshold: {self.array_inline_threshold}\n"
            f"  all_array_storage: {self.all_array_storage}\n"
            f"  all_array_compression: {self.all_array_compression}\n"
            f"  all_array_compression_kwargs: {self.all_array_compression_kwargs}\n"
            f"  default_array_save_base: {self.default_array_save_base}\n"
            f"  convert_unknown_ndarray_subclasses: {self.convert_unknown_ndarray_subclasses}\n"
            f"  default_version: {self.default_version}\n"
            f"  io_block_size: {self.io_block_size}\n"
            f"  legacy_fill_schema_defaults: {self.legacy_fill_schema_defaults}\n"
            f"  validate_on_read: {self.validate_on_read}\n"
            f"  lazy_tree: {self.lazy_tree}\n"
            ">"
        )


class _ConfigLocal(threading.local):
    def __init__(self):
        self.config_stack = []


_global_config = AsdfConfig()
_local = _ConfigLocal()


def get_config():
    """
    Get the current config, which may have been altered by
    one or more surrounding calls to `asdf.config_context`.

    Returns
    -------
    asdf.config.AsdfConfig
    """
    if len(_local.config_stack) == 0:
        return _global_config

    return _local.config_stack[-1]


@contextmanager
def config_context():
    """
    Context manager that temporarily overrides asdf configuration.
    The context yields an `asdf.config.AsdfConfig` instance that can be modified
    without affecting code outside of the context.
    """
    base_config = _global_config if len(_local.config_stack) == 0 else _local.config_stack[-1]

    config = copy.copy(base_config)
    _local.config_stack.append(config)

    try:
        yield config
    finally:
        _local.config_stack.pop()
