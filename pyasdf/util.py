# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


from __future__ import absolute_import, division, unicode_literals, print_function

import itertools
import math

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
    last_base = base = arr
    while isinstance(base.base, np.ndarray):
        last_base = base
        base = base.base
    return base, last_base


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


def iter_subclasses(cls):
    """
    Returns all subclasses of a class.
    """
    for x in cls.__subclasses__():
        yield x
        for y in iter_subclasses(x):
            yield y


def calculate_padding(content_size, pad_blocks, block_size):
    """
    Calculates the amount of extra space to add to a block given the
    user's request for the amount of extra space.  Care is given so
    that the total of size of the block with padding is evenly
    divisible by block size.

    Parameters
    ----------
    content_size : int
        The size of the actual content

    pad_blocks : float or bool
        If `False`, add no padding (always return 0).  If `True`, add
        a default amount of padding of 10% If a float, it is a factor
        to multiple content_size by to get the new total size.

    block_size : int
        The filesystem block size to use.

    Returns
    -------
    nbytes : int
        The number of extra bytes to add for padding.
    """
    if not pad_blocks:
        return 0
    if pad_blocks is True:
        pad_blocks = 1.1
    new_size = content_size * pad_blocks
    new_size = int((math.ceil(
        float(new_size) / block_size) + 1) * block_size)
    return max(new_size - content_size, 0)
