from .util import NotSet
from .providers import AsdfConverterProvider, get_registered_converter_providers, create_converters
from .converter import ConverterIndex


__all__ = ["get_config", "configure"]


class AsdfConfig:
    def __init__(
        self,
        converter_providers=None,
        converters=None,
        converter_index=None,
    ):
        self._converter_providers = converter_providers
        self._converters = converters
        self._converter_index = converter_index

    @property
    def converter_providers(self):
        if self._converter_providers is None:
            self._converter_providers = get_registered_converter_providers()

        return self._converter_providers

    @property
    def converters(self):
        if self._converters is None:
            self._converters = create_converters(self.converter_providers)

        return self._converters

    @property
    def converter_index(self):
        if self._converter_index is None:
            self._converter_index = ConverterIndex(self.converters)

        return self._converter_index


_config = AsdfConfig()


def get_config():
    return _config


class _ConfigContext:
    def __init__(self, original_config):
        self.original_config = original_config

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        global _config
        _config = self.original_config


def configure(
    converter_providers=NotSet,
):
    global _config
    original_config = _config

    if converter_providers is NotSet:
        converter_providers = _config._converter_providers
        converters = _config._converters
        converter_index = _config._converter_index
    else:
        converters = None
        converter_index = None

    _config = AsdfConfig(
        converter_providers=converter_providers,
        converters=converters,
        converter_index=converter_index,
    )

    return _ConfigContext(original_config)
