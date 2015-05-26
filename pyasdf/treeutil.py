# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
Utility functions for managing tree-like data structures.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.extern import six

from .tagged import Tagged, tag_object


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
    def recurse(tree, seen):
        if id(tree) in seen:
            return

        if isinstance(tree, dict):
            new_seen = seen | set([id(tree)])
            for val in six.itervalues(tree):
                recurse(val, new_seen)
        elif isinstance(tree, (list, tuple)):
            new_seen = seen | set([id(tree)])
            for val in tree:
                recurse(val, new_seen)

        callback(tree)

    return recurse(top, set())


def walk_and_modify(top, callback):
    """
    Modify a tree by walking it with a callback function.  It also has
    the effect of doing a deep copy.

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
    def recurse(tree, seen):
        if id(tree) in seen:
            return tree

        if isinstance(tree, dict):
            new_seen = seen | set([id(tree)])
            result = tree.__class__()
            for key, val in six.iteritems(tree):
                val = recurse(val, new_seen)
                if val is not None:
                    result[key] = val
            if isinstance(tree, Tagged):
                result = tag_object(tree.tag, result)
        elif isinstance(tree, (list, tuple)):
            new_seen = seen | set([id(tree)])
            result = tree.__class__([recurse(val, new_seen) for val in tree])
            if isinstance(tree, Tagged):
                result = tag_object(tree.tag, result)
        else:
            result = tree

        result = callback(result)

        return result

    return recurse(top, set())
