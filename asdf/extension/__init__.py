"""
Support for plugins that extend asdf to serialize
additional custom types.
"""
import warnings

from asdf.exceptions import AsdfDeprecationWarning

from . import _legacy
from ._compressor import Compressor
from ._converter import Converter, ConverterProxy
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
    # Legacy API
    "AsdfExtension",
    "AsdfExtensionList",
    "BuiltinExtension",
    "default_extensions",
    "get_default_resolver",
    "get_cached_asdf_extension_list",
]


def get_cached_asdf_extension_list(extensions):
    """
    Get a previously created AsdfExtensionList for the specified
    extensions, or create and cache one if necessary.  Building
    the type index is expensive, so it helps performance to reuse
    the index when possible.
    Parameters
    ----------
    extensions : list of asdf.extension.AsdfExtension
    Returns
    -------
    asdf.extension.AsdfExtensionList
    """
    from ._legacy import get_cached_asdf_extension_list

    warnings.warn(
        "get_cached_asdf_extension_list is deprecated. "
        "Please see the new extension API "
        "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
        AsdfDeprecationWarning,
    )
    return get_cached_asdf_extension_list(extensions)


def get_default_resolver():
    """
    Get the resolver that includes mappings from all installed extensions.
    """
    from ._legacy import get_default_resolver

    warnings.warn(
        "get_default_resolver is deprecated. "
        "Please see the new extension API "
        "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
        AsdfDeprecationWarning,
    )
    return get_default_resolver()


_deprecated_legacy = {
    "default_extensions",
    "AsdfExtension",
    "AsdfExtensionList",
    "BuiltinExtension",
}


def __getattr__(name):
    if name in _deprecated_legacy:
        warnings.warn(
            f"{name} is deprecated. "
            "Please see the new extension API "
            "https://asdf.readthedocs.io/en/stable/asdf/extending/converters.html",
            AsdfDeprecationWarning,
        )
        return getattr(_legacy, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
