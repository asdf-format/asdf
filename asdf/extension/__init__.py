"""
Support for plugins that extend asdf to serialize
additional custom types.
"""
from ._extension import Extension, ExtensionProxy
from ._manager import ExtensionManager, get_cached_extension_manager
from ._manifest import ManifestExtension
from ._tag import TagDefinition
from ._converter import Converter, ConverterProxy
from ._compressor import Compressor
from ._legacy import (
    AsdfExtension,
    AsdfExtensionList,
    BuiltinExtension,
    default_extensions,
    get_default_resolver,
    get_cached_asdf_extension_list,
)


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
    # Legacy API
    "AsdfExtension",
    "AsdfExtensionList",
    "BuiltinExtension",
    "default_extensions",
    "get_default_resolver",
    "get_cached_asdf_extension_list",
]
