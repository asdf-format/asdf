"""
Methods for getting and setting asdf global configuration
options.
"""
import threading
from contextlib import contextmanager
import copy

from . import entry_points
from .resource import ResourceMappingProxy, ResourceManager
from . import versioning
from ._helpers import validate_version
from .extension import ExtensionProxy

__all__ = ["AsdfConfig", "get_config", "config_context"]


DEFAULT_VALIDATE_ON_READ = True
DEFAULT_DEFAULT_VERSION = str(versioning.default_version)


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

        self._lock = threading.RLock()

    @property
    def resource_mappings(self):
        """
        Get the list of registered resource mapping instances.  Unless
        overridden by user configuration, this list contains every mapping
        registered with an entry point.

        Returns
        -------
        list of collections.abc.Mapping
        """
        if self._resource_mappings is None:
            with self._lock:
                if self._resource_mappings is None:
                    self._resource_mappings = entry_points.get_resource_mappings()
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
            resource_mappings = [mapping] + [
                r for r in self.resource_mappings
                if r != mapping
            ]
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
            Python package whose mappings will all be removed.
        """
        with self._lock:
            resource_mappings = self.resource_mappings
            if mapping is not None:
                mapping = ResourceMappingProxy.maybe_wrap(mapping)
                resource_mappings = [m for m in resource_mappings if m != mapping]
            if package is not None:
                resource_mappings = [m for m in resource_mappings if m.package_name != package]
            self._resource_mappings = resource_mappings
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
        Get the `ResourceManager` instance.  Includes resources from
        registered resource mappings and any mappings added at runtime.

        Returns
        -------
        asdf.resource.ResourceManager
        """
        if self._resource_manager is None:
            with self._lock:
                if self._resource_manager is None:
                    self._resource_manager = ResourceManager(self.resource_mappings)
        return self._resource_manager

    @property
    def extensions(self):
        """
        Get the list of registered `AsdfExtension` instances.

        Returns
        -------
        list of asdf.extension.AsdfExtension
        """
        if self._extensions is None:
            with self._lock:
                if self._extensions is None:
                    self._extensions = entry_points.get_extensions()
        return self._extensions

    def add_extension(self, extension):
        """
        Register a new extension.  The new extension will
        take precedence over all previously registered extensions.

        Parameters
        ----------
        extension : asdf.extension.AsdfExtension
        """
        with self._lock:
            extension = ExtensionProxy.maybe_wrap(extension)
            self._extensions = [extension] + [e for e in self.extensions if e != extension]

    def remove_extension(self, extension=None, *, package=None):
        """
        Remove a registered extension.

        Parameters
        ----------
        extension : asdf.extension.AsdfExtension, optional
            An extension instance to remove.
        package : str, optional
            A Python package name whose extensions will all be removed.
        """
        with self._lock:
            extensions = self.extensions
            if extension is not None:
                extension = ExtensionProxy.maybe_wrap(extension)
                extensions = [e for e in extensions if e != extension]
            if package is not None:
                extensions = [e for e in extensions if e.package_name != package]
            self._extensions = extensions

    def reset_extensions(self):
        """
        Reset extensions to the default list registered via entry points.
        """
        with self._lock:
            self._extensions = None

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

    def __repr__(self):
        return (
            "<AsdfConfig\n"
            "  validate_on_read: {}\n"
            "  default_version: {}\n"
            ">"
        ).format(
            self.validate_on_read,
            self.default_version,
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
    else:
        return _local.config_stack[-1]


@contextmanager
def config_context():
    """
    Context manager that temporarily overrides asdf configuration.
    The context yields an `asdf.config.AsdfConfig` instance that can be modified
    without affecting code outside of the context.
    """
    if len(_local.config_stack) == 0:
        base_config = _global_config
    else:
        base_config = _local.config_stack[-1]

    config = copy.copy(base_config)
    _local.config_stack.append(config)

    try:
        yield config
    finally:
        _local.config_stack.pop()
