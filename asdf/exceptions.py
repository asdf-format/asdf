# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


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
