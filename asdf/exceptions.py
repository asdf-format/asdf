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

class DelimiterNotFoundError(ValueError):
    """
    Indicates that a delimiter was not found when reading or
    seeking through a file.
    """
