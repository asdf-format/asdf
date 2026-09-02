"""
Support for plugins that extend asdf to serialize
additional custom types.
"""

from ._compressor import Compressor
from ._converter import Converter, ConverterProxy
from ._extension import Extension, ExtensionLike, ExtensionProxy
from ._manager import ExtensionManager, get_cached_extension_manager
from ._manifest import ManifestExtension
from ._serialization_context import SerializationContext
from ._tag import TagDefinition
from ._validator import Validator

__all__ = [
    "Compressor",
    "Converter",
    "ConverterProxy",
    "Extension",
    "ExtensionLike",
    "ExtensionManager",
    "ExtensionProxy",
    "ManifestExtension",
    "SerializationContext",
    "TagDefinition",
    "Validator",
    "get_cached_extension_manager",
]
