import warnings

from asdf.exceptions import AsdfDeprecationWarning

from . import _helpers

warnings.warn(
    "asdf.tests.helpers is deprecated. Please see asdf.testing.helpers",
    AsdfDeprecationWarning,
)


def __getattr__(name):
    warnings.warn(
        "asdf.tests.helpers is deprecated. Please see asdf.testing.helpers",
        AsdfDeprecationWarning,
    )
    return getattr(_helpers, name)
