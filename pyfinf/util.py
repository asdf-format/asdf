# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


from __future__ import absolute_import, division, unicode_literals, print_function

import itertools

from astropy.extern.six.moves.urllib import parse as urlparse

import numpy as np


def human_list(l, separator="and"):
    """
    Formats a list for human readability.

    Parameters
    ----------
    l : sequence
        A sequence of strings

    separator : string, optional
        The word to use between the last two entries.  Default:
        ``"and"``.

    Returns
    -------
    formatted_list : string

    Examples
    --------
    >>> human_list(["vanilla", "strawberry", "chocolate"], "or")
    'vanilla, strawberry or chocolate'
    """
    if len(l) == 1:
        return l[0]
    else:
        return ', '.join(l[:-1]) + ' ' + separator + ' ' + l[-1]


def get_array_base(arr):
    """
    For a given Numpy array, finds the base array that "owns" the
    actual data.
    """
    base = arr
    while isinstance(base.base, np.ndarray):
        base = base.base
    return base


def get_base_uri(uri):
    """
    For a given URI, return the part without any fragment.
    """
    parts = urlparse.urlparse(uri)
    return urlparse.urlunparse(list(parts[:5]) + [''])


def nth_item(iterable, n, default=None):
    """
    Returns the nth item of an iterable or a default value.

    Support Python-style negative indexing.
    """
    if n < 0:
        l = list(iterable)
        try:
            return l[n]
        except IndexError:
            return default
    else:
        return next(itertools.islice(iterable, n, None), default)
