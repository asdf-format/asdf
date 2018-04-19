# -*- coding: utf-8 -*-
# This code was taken from sunpy, which is licensed under a 3-clause BSD style
# license - see licenses/SUNPY_LICENSE.rst
"""Sundry function and class decorators."""


__all__ = ['add_common_docstring']


class add_common_docstring(object):
    """
    A function decorator that will append and/or prepend an addendum
    to the docstring of the target function.


    Parameters
    ----------
    append : `str`, optional
        A string to append to the end of the functions docstring.

    prepend : `str`, optional
        A string to prepend to the start of the functions docstring.

    **kwargs : `dict`, optional
        A dictionary to format append and prepend strings.
    """

    def __init__(self, append=None, prepend=None, **kwargs):
        if kwargs:
            append = append.format(**kwargs)
            prepend = prepend.format(**kwargs)
        self.append = append
        self.prepend = prepend

    def __call__(self, func):
        func.__doc__ = func.__doc__ if func.__doc__ else ''
        self.append = self.append if self.append else ''
        self.prepend = self.prepend if self.prepend else ''
        if self.append and isinstance(func.__doc__, str):
            func.__doc__ += self.append
        if self.prepend and isinstance(func.__doc__, str):
            func.__doc__ = self.prepend + func.__doc__
        return func
