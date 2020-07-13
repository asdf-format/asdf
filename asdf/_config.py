"""
Methods for getting and setting asdf global configuration
options.
"""
import threading
from contextlib import contextmanager
import copy

from . import entry_points
from .resource import ResourceManager


DEFAULT_VALIDATE_ON_READ = True


class AsdfConfig:
    """
    Container for ASDF configuration options.  Users are not intended to
    construct this object directly; instead, use the `asdf.get_config` and
    `asdf.config_context` module methods.
    """

    def __init__(
        self,
        resource_mappings=None,
        resource_manager=None,
        validate_on_read=None,
    ):
        self._resource_mappings = resource_mappings
        self._resource_manager = resource_manager

        if validate_on_read is None:
            self._validate_on_read = DEFAULT_VALIDATE_ON_READ
        else:
            self._validate_on_read = validate_on_read

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
        with self._lock:
            resource_mappings = self.resource_mappings.copy()
            resource_mappings.append(mapping)
            self._resource_mappings = resource_mappings
            self._resource_manager = None

    def remove_resource_mapping(self, mapping):
        """
        Remove a registered resource mapping.

        Parameters
        ----------
        mapping : collections.abc.Mapping
        """
        with self._lock:
            resource_mappings = [m for m in self.resource_mappings if m is not mapping]
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

    def __repr__(self):
        return (
            "AsdfConfig(\n"
            "  resource_mappings=[...],\n"
            "  validate_on_read={!r},\n"
            ")"
        ).format(self.validate_on_read)


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
