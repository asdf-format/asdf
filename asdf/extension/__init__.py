"""
Support for plugins that extend asdf to serialize
additional custom types.
"""


from ._compressor import Compressor
from ._converter import Converter, ConverterProxy, Reconvert
from ._extension import Extension, ExtensionProxy
from ._manager import ExtensionManager, get_cached_extension_manager
from ._manifest import ManifestExtension
from ._tag import TagDefinition
from ._validator import Validator

__all__ = [
    # New API
    "Extension",
    "ExtensionProxy",
    "ManifestExtension",
    "ExtensionManager",
    "get_cached_extension_manager",
    "TagDefinition",
    "Converter",
    "ConverterProxy",
    "Compressor",
    "Validator",
    "Reconvert",
]
