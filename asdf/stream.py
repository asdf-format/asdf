import warnings

from .exceptions import AsdfDeprecationWarning
from .tags.core.stream import Stream  # noqa: F401

warnings.warn(
    "asdf.stream is deprecated. Please use asdf.tags.core.stream",
    AsdfDeprecationWarning,
)
