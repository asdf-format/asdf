"""
Support for plugins that extend asdf to serialize
additional custom types.
"""
from ._compressor import Compressor
from ._converter import Converter, ConverterProxy
from ._extension import Extension, ExtensionProxy
from ._legacy import (
    AsdfExtension,
    AsdfExtensionList,
    BuiltinExtension,
    default_extensions,
    get_default_resolver,
)
from ._manager import ExtensionManager
from ._manifest import ManifestExtension
from ._tag import TagDefinition
from ._validator import Validator

__all__ = [
    # New API
    "Extension",
    "ExtensionProxy",
    "ManifestExtension",
    "ExtensionManager",
    "TagDefinition",
    "Converter",
    "ConverterProxy",
    "Compressor",
    "Validator",
    # Legacy API
    "AsdfExtension",
    "AsdfExtensionList",
    "BuiltinExtension",
    "default_extensions",
    "get_default_resolver",
]
