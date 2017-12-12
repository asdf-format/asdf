# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
Utility functions for managing tree-like data structures.
"""

import inspect

from .tagged import tag_object


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
    for x in iter_tree(top):
        callback(x)


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

        if isinstance(tree, (list, tuple)):
            seen.add(tree_id)
            for val in tree:
                for sub in recurse(val):
                    yield sub
            seen.remove(tree_id)
        elif isinstance(tree, dict):
            seen.add(tree_id)
            for val in tree.values():
                for sub in recurse(val):
                    yield sub
            seen.remove(tree_id)

        yield tree

    return recurse(top)


def walk_and_modify(top, callback):
    """Modify a tree by walking it with a callback function.  It also has
    the effect of doing a deep copy.

    Parameters
    ----------
    top : object
        The root of the tree.  May be a dict, list or other Python object.

    callback : callable
        A function to call at each node in the tree.  It takes either
        one or two arguments:

        - an instance from the tere
        - a json id (optional)

        It may return a different instance in order to modify the
        tree.

        The json id is the context under which any relative URLs
        should be resolved.  It may be `None` if no ids are in the file

        The callback is called on an instance after all of its
        children have been visited (depth-first order).

    Returns
    -------
    tree : object
        The modified tree.

    """
    # For speed reasons, there are two different versions of the inner
    # function

    seen = set()

    def recurse(tree):
        id_tree = id(tree)

        if id_tree in seen:
            return tree

        if isinstance(tree, dict):
            result = tree.__class__()
            seen.add(id_tree)
            for key, val in tree.items():
                val = recurse(val)
                if val is not None:
                    result[key] = val
            seen.remove(id_tree)
            if hasattr(tree, '_tag'):
                result = tag_object(tree._tag, result)
        elif isinstance(tree, (list, tuple)):
            seen.add(id_tree)
            result = tree.__class__(
                [recurse(val) for val in tree])
            seen.remove(id_tree)
            if hasattr(tree, '_tag'):
                result = tag_object(tree._tag, result)
        else:
            result = tree

        result = callback(result)

        return result

    def recurse_with_json_ids(tree, json_id):
        id_tree = id(tree)

        if id_tree in seen:
            return tree

        if isinstance(tree, dict):
            if 'id' in tree:
                json_id = tree['id']
            result = tree.__class__()
            seen.add(id_tree)
            for key, val in tree.items():
                val = recurse_with_json_ids(val, json_id)
                if val is not None:
                    result[key] = val
            seen.remove(id_tree)
            if hasattr(tree, '_tag'):
                result = tag_object(tree._tag, result)
        elif isinstance(tree, (list, tuple)):
            seen.add(id_tree)
            result = tree.__class__(
                [recurse_with_json_ids(val, json_id) for val in tree])
            seen.remove(id_tree)
            if hasattr(tree, '_tag'):
                result = tag_object(tree._tag, result)
        else:
            result = tree

        result = callback(result, json_id)

        return result

    if callback.__code__.co_argcount == 2:
        return recurse_with_json_ids(top, None)
    else:
        return recurse(top)
