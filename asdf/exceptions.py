from asdf._jsonschema import ValidationError

__all__ = [
    "AsdfConversionWarning",
    "AsdfDeprecationWarning",
    "AsdfManifestURIMismatchWarning",
    "AsdfPackageVersionWarning",
    "AsdfProvisionalAPIWarning",
    "AsdfWarning",
    "DelimiterNotFoundError",
    "ValidationError",
]


class AsdfWarning(Warning):
    """
    The base warning class from which all ASDF warnings should inherit.
    """


class AsdfDeprecationWarning(AsdfWarning, DeprecationWarning):
    """
    A warning class to indicate a deprecated feature.
    """


class AsdfConversionWarning(AsdfWarning):
    """
    Warning class used for failures to convert data into custom types.
    """


class AsdfBlockIndexWarning(AsdfWarning):
    """
    Warning class to indicate that a file was read with an invalid block index
    """


class DelimiterNotFoundError(ValueError):
    """
    Indicates that a delimiter was not found when reading or
    seeking through a file.
    """


class AsdfProvisionalAPIWarning(AsdfWarning, FutureWarning):
    """
    Used for provisional features where breaking API changes might be
    introduced at any point (including minor releases). These features
    are likely to be added in a future ASDF version. However, Use of
    provisional features is highly discouraged for production code.
    """


class AsdfPackageVersionWarning(AsdfWarning):
    """
    A warning indicating a package version mismatch
    """


class AsdfManifestURIMismatchWarning(AsdfWarning):
    """
    A warning indicaing that an extension registered with a manifest
    contains a id that does not match the uri of the manifest.
    """
