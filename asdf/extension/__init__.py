"""
Support for plugins that extend asdf to serialize
additional custom types.
"""
from ._extension import ExtensionProxy
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
    "ExtensionProxy",
    # Legacy API
    "AsdfExtension",
    "AsdfExtensionList",
    "BuiltinExtension",
    "default_extensions",
    "get_default_resolver",
    "get_cached_asdf_extension_list",
]
