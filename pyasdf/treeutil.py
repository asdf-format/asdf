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
    seen = set()

    def recurse(tree):
        tree_id = id(tree)

        if tree_id in seen:
            return

        seen.add(tree_id)

        if isinstance(tree, dict):
            for val in six.itervalues(tree):
                recurse(val)
        elif isinstance(tree, (list, tuple)):
            for val in tree:
                recurse(val)

        callback(tree)

    return recurse(top)


def iter_tree(top):
    """
    Iterate over all nodes in a tree, in depth-first order.

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
    seen = set()

    def recurse(tree):
        tree_id = id(tree)

        if tree_id in seen:
            return

        seen.add(tree_id)

        if isinstance(tree, (list, tuple)):
            for val in tree:
                for sub in recurse(val):
                    yield sub
        elif isinstance(tree, dict):
            for val in six.itervalues(tree):
                for sub in recurse(val):
                    yield sub

        yield tree

    return recurse(top)


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
        instance and a json id and may return a different instance in
        order to modify the tree.

        The json id is the context under which any relative URLs
        should be resolved.  It may be `None` if no ids are in the file

        The callback is called on an instance after all of its
        children have been visited (depth-first order).

    Returns
    -------
    tree : object
        The modified tree.

    """
    def recurse(tree, seen, json_id):
        if id(tree) in seen:
            return tree

        if isinstance(tree, dict):
            if 'id' in tree:
                json_id = tree['id']
            new_seen = seen | set([id(tree)])
            result = tree.__class__()
            for key, val in six.iteritems(tree):
                val = recurse(val, new_seen, json_id)
                if val is not None:
                    result[key] = val
            if hasattr(tree, '_tag'):
                result = tag_object(tree._tag, result)
        elif isinstance(tree, (list, tuple)):
            new_seen = seen | set([id(tree)])
            result = tree.__class__(
                [recurse(val, new_seen, json_id) for val in tree])
            if hasattr(tree, '_tag'):
                result = tag_object(tree._tag, result)
        else:
            result = tree

        result = callback(result, json_id)

        return result

    return recurse(top, set(), None)
