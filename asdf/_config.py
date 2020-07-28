"""
Methods for getting and setting asdf global configuration
options.
"""
import threading
from contextlib import contextmanager
import copy

from . import entry_points
from .resource import ResourceManager, ResourceMappingProxy
from .extension import ExtensionProxy
from . import versioning
from ._helpers import validate_version


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
        self._default_extensions = None
        self._validate_on_read = DEFAULT_VALIDATE_ON_READ
        self._default_version = DEFAULT_DEFAULT_VERSION
        self._lock = threading.RLock()

    @property
    def resource_mappings(self):
        """
        Get the list of enabled resource Mapping instances.  Unless
        overridden by user configuration, this includes every Mapping
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
        Register a new resource Mapping.

        Parameters
        ----------
        mapping : collections.abc.Mapping
            map of `str` resource URI to `bytes` content
        """
        mapping = ResourceMappingProxy.maybe_wrap(mapping)

        with self._lock:
            if any(m.delegate is mapping.delegate for m in self.resource_mappings):
                return
            resource_mappings = self.resource_mappings.copy()
            resource_mappings.append(mapping)
            self._resource_mappings = resource_mappings
            self._resource_manager = None

    def remove_resource_mapping(self, mapping=None, *, package=None):
        """
        Remove a registered resource mapping.

        Parameters
        ----------
        mapping : collections.abc.Mapping, optional
            A Mapping instance to remove.
        package : str, optional
            A Python package name whose mappings will all be removed.
        """
        with self._lock:
            resource_mappings = self.resource_mappings
            if mapping is not None:
                mapping = ResourceMappingProxy.maybe_wrap(mapping)
                resource_mappings = [m for m in resource_mappings if m.delegate is not mapping.delegate]
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
        registered resource Mappings and any Mappings added at runtime.

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
        list of asdf.AsdfExtension
        """
        if self._extensions is None:
            with self._lock:
                if self._extensions is None:
                    self._extensions = entry_points.get_extensions()
        return self._extensions

    @property
    def default_extensions(self):
        """
        Get the list of `AsdfExtension` instances that are
        enabled by default for new files.

        Returns
        -------
        list of asdf.AsdfExtension
        """
        if self._default_extensions is None:
            with self._lock:
                if self._default_extensions is None:
                    self._default_extensions = [e for e in self.extensions if e.default_enabled]
        return self._default_extensions

    def add_extension(self, extension):
        """
        Register a new extension.

        Parameters
        ----------
        extension : asdf.AsdfExtension
        """
        extension = ExtensionProxy.maybe_wrap(extension)
        with self._lock:
            if any(e.delegate is extension.delegate for e in self.extensions):
                return
            extensions = self.extensions.copy()
            extensions.append(extension)
            self._extensions = extensions

            if extension.default_enabled and self._default_extensions is not None:
                default_extensions = self.default_extensions.copy()
                default_extensions.append(extension)
                self._default_extensions = default_extensions

    def remove_extension(self, extension=None, *, package=None):
        """
        Remove a registered extension.

        Parameters
        ----------
        extension : asdf.AsdfExtension, optional
            An extension to remove.
        package : str, optional
            A Python package name whose extensions will all be removed.
        """
        with self._lock:
            extensions = self.extensions
            default_extensions = self.default_extensions
            if extension is not None:
                extension = ExtensionProxy.maybe_wrap(extension)
                extensions = [e for e in extensions if e.delegate is not extension.delegate]
                default_extensions = [e for e in default_extensions if e.delegate is not extension.delegate]
            if package is not None:
                extensions = [e for e in extensions if e.package_name != package]
                default_extensions = [e for e in default_extensions if e.package_name != package]
            self._extensions = extensions
            self._default_extensions = default_extensions

    def add_default_extension(self, extension):
        """
        Add to the list of extensions that are enabled by default
        for new files.

        Parameters
        ----------
        extension : asdf.AsdfExtension
        """
        extension = ExtensionProxy.maybe_wrap(extension)
        with self._lock:
            if any(e.delegate is extension.delegate for e in self.default_extensions):
                return
            self.add_extension(extension)
            if not extension.default_enabled:
                # Make sure we're using the same wrapper here:
                extension = next(e for e in self.extensions if e.delegate is extension.delegate)
                default_extensions = self.default_extensions.copy()
                default_extensions.append(extension)
                self._default_extensions = default_extensions

    def remove_default_extension(self, extension=None, *, package=None):
        """
        Remove from the list of extensions that are enabled
        by default for new files.

        Parameters
        ----------
        extension : asdf.AsdfExtension, optional
            An extension instance to remove.
        package : str, optional
            A Python package name whose extensions will all be removed.
        """
        with self._lock:
            default_extensions = self.default_extensions
            if extension is not None:
                extension = ExtensionProxy.maybe_wrap(extension)
                default_extensions = [e for e in default_extensions if e.delegate is not extension.delegate]
            if package is not None:
                default_extensions = [e for e in default_extensions if e.package_name != package]
            self._default_extensions = default_extensions

    def reset_extensions(self):
        """
        Reset registered and default extensions to the list
        provided as entry points.
        """
        with self._lock:
            self._extensions = None
            self._default_extensions = None

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
            "  validate_on_read: {},\n"
            "  default_version: {},\n"
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
    one or more surrounding calls to `config_context`.

    Returns
    -------
    AsdfConfig
    """
    if len(_local.config_stack) == 0:
        return _global_config
    else:
        return _local.config_stack[-1]


@contextmanager
def config_context():
    """
    Context manager that temporarily overrides asdf configuration.
    The context yields an `AsdfConfig` instance that can be modified
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
