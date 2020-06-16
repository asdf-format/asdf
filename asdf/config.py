"""
Methods for getting and setting asdf global configuration
options.
"""
import threading

from .util import NotSet
from .providers import get_registered_converter_providers, create_converters
from .converter import ConverterIndex


__all__ = ["get_config", "configure", "config_context"]


class AsdfConfig:
    """
    Container for ASDF configuration options.  Users are not intended to
    construct this object directly; instead, use the `configure` and
    `config_context` module methods.
    """
    def __init__(
        self,
        converter_providers=None,
        converters=None,
        converter_index=None,
        validate_on_read=True,
    ):
        self._converter_providers = converter_providers
        self._converters = converters
        self._converter_index = converter_index
        self._validate_on_read = validate_on_read

        self._lock = threading.RLock()

    @property
    def converter_providers(self):
        """
        Get the list of `AsdfConverterProvider` instances.
        Unless overridden by user configuration, this will contain
        every provider registered as an entry point.

        Returns
        -------
        list of asdf.AsdfConverterProvider
        """
        if self._converter_providers is None:
            with self._lock:
                if self._converter_providers is None:
                    self._converter_providers = get_registered_converter_providers()

        return self._converter_providers

    @property
    def converters(self):
        """
        Get the list of `AsdfConverter` instances provided
        by the configured converter_providers.

        Returns
        -------
        list of asdf.AsdfConverter
        """
        if self._converters is None:
            with self._lock:
                if self._converters is None:
                    self._converters = create_converters(self.converter_providers)

        return self._converters

    @property
    def converter_index(self):
        """
        Get the `ConverterIndex` for the configured converters.

        Returns
        -------
        asdf.converter.ConverterIndex
        """

        if self._converter_index is None:
            with self._lock:
                if self._converter_index is None:
                    self._converter_index = ConverterIndex(self.converters)

        return self._converter_index

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

    def _merge(
        self,
        converter_providers=NotSet,
        validate_on_read=NotSet,
    ):
        if converter_providers is NotSet:
            converter_providers = self._converter_providers
            converters = self._converters
            converter_index = self._converter_index
        else:
            converters = None
            converter_index = None

        if validate_on_read is NotSet:
            validate_on_read = self._validate_on_read

        return AsdfConfig(
            converter_providers=converter_providers,
            converters=converters,
            converter_index=converter_index,
            validate_on_read=validate_on_read,
        )


class _ConfigLocal(threading.local):
    def __init__(self):
        self.config_stack = []


_global_config = AsdfConfig()
_local = _ConfigLocal()


def get_config():
    """
    Get the current config, which may have been altered by
    one or more containing `AsdfConfigContext`.

    Returns
    -------
    AsdfConfig
    """
    if len(_local.config_stack) == 0:
        return _global_config
    else:
        return _local.config_stack[-1]


def configure(
    converter_providers=NotSet,
    validate_on_read=NotSet,
):
    """
    Update the global asdf configuration.  This method is
    thread-safe in that it updates the config atomically,
    but calling this method after threads have been started
    can lead to race conditions.  Changes affect currently
    open `AsdfFile` instances.

    The default parameter value `NotSet` leaves that parameter
    set to its current value.

    Parameters
    ----------
    converter_providers : list of asdf.AsdfConverterProvider or None or NotSet
        `asdf.AsdfConverterProvider` instances to use when reading
        and writing ASDF files.  If `None`, all providers registered
        with entry points are used.

    validate_on_read : bool or NotSet
        If True, ASDF files will be validated against schemas on read.
    """
    global _global_config

    _global_config = _global_config._merge(
        converter_providers=converter_providers,
        validate_on_read=validate_on_read,
    )


class AsdfConfigContext:
    """
    Context manager that temporarily overrides asdf configuration.
    Users are not intended to construct this object directly; instead,
    use the `config_context` module method.
    """
    def __init__(self, **config_options):
        self._config_options = config_options

    def __enter__(self):
        if len(_local.config_stack) == 0:
            base_config = _global_config
        else:
            base_config = _local.config_stack[-1]

        config = base_config._merge(**self._config_options)
        _local.config_stack.append(config)
        return config

    def __exit__(self, exc_type, exc_value, traceback):
        _local.config_stack.pop()

    def __repr__(self):
        arg_string = ", ".join(["{}={!r}".format(k, v) for k, v in self._config_options if v is not NotSet])
        return "{}({})".format(self.__class__.__name__, arg_string)


def config_context(
    converter_providers=NotSet,
    validate_on_read=NotSet,
):
    """
    Create a context manager that temporarily overrides asdf
    configuration.  Overrides are only applied in the current
    thread.  Nested calls to this method are applied in order,
    with the innermost context overriding the others. Changes
    affect currently open `AsdfFile` instances.

    The default parameter value `NotSet` leaves that parameter
    set to its current value.

    Parameters
    ----------
    converter_providers : list of asdf.AsdfConverterProvider or None or NotSet
        `asdf.AsdfConverterProvider` instances to use when reading
        and writing ASDF files.  If `None`, all providers registered
        with entry points are used.

    validate_on_read : bool or NotSet
        If True, ASDF files will be validated against schemas on read.

    Returns
    -------
    AsdfConfigContext
    """
    return AsdfConfigContext(
        converter_providers=converter_providers,
        validate_on_read=validate_on_read,
    )
