# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
Utility functions for managing tree-like data structures.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.extern import six


def walk(top, callback):
    """
    Walking through a tree of objects, calling a given function at
    each node.

    Parameters
    ----------
    top : object
        The root of the tree.  May be a dict, list or other Python object.

    callback : callable
        A function to call at each node in the tree.

        The callback is called on an instance after all of its
        children have been visited (depth-first order).

    Returns
    -------
    tree : object
        The modified tree.
    """
    def recurse(tree):
        if isinstance(tree, dict):
            for val in six.itervalues(tree):
                recurse(val)
        elif isinstance(tree, (list, tuple)):
            for val in tree:
                recurse(val)

        callback(tree)

    return recurse(top)


def walk_and_modify(top, callback):
    """
    Modify a tree by walking it with a callback function.

    Parameters
    ----------
    top : object
        The root of the tree.  May be a dict, list or other Python object.

    callback : callable
        A function to call at each node in the tree.  It takes and
        instance and may return a different instance in order to
        modify the tree.

        The callback is called on an instance after all of its
        children have been visited (depth-first order).

    Returns
    -------
    tree : object
        The modified tree.
    """
    def recurse(tree):
        if isinstance(tree, dict):
            result = tree.__class__()
            for key, val in six.iteritems(tree):
                result[key] = recurse(val)
        elif isinstance(tree, (list, tuple)):
            result = tree.__class__([recurse(val) for val in tree])
        else:
            result = tree

        result = callback(result)

        return result

    return recurse(top)
