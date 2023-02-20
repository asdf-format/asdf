import warnings

from ._types import AsdfType, CustomType, ExtensionTypeMeta, format_tag
from .exceptions import AsdfDeprecationWarning

# This is not exhaustive, but represents the public API
from .versioning import join_tag_version, split_tag_version

__all__ = ["join_tag_version", "split_tag_version", "AsdfType", "CustomType", "format_tag", "ExtensionTypeMeta"]

warnings.warn(
    "The module asdf.asdftypes has been deprecated and will be removed in 3.0. Use asdf.types instead.",
    AsdfDeprecationWarning,
)
