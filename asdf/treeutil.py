"""
Utility functions for managing tree-like data structures.
"""

import warnings

from . import _itertree, tagged
from .exceptions import AsdfDeprecationWarning, AsdfWarning

__all__ = ["walk", "iter_tree", "walk_and_modify", "get_children", "is_container", "PendingValue", "RemoveNode"]


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
    for node, edge in _itertree.depth_first(top):
        yield node


class _PendingValue:
    """
    Class of the PendingValue singleton instance.  The presence of the instance
    in an asdf tree indicates that extension code is failing to handle
    reference cycles.
    """

    def __repr__(self):
        return "PendingValue"


PendingValue = _PendingValue()


RemoveNode = _itertree.RemoveNode


def _get_json_id(top, edge):
    keys = []
    while edge and edge.key is not None:
        keys.append(edge.key)
        edge = edge.parent
    node = top
    if hasattr(node, "get") and isinstance(node.get("id", None), str):
        json_id = node["id"]
    else:
        json_id = None
    for key in keys[::-1]:
        if hasattr(node, "get") and isinstance(node.get("id", None), str):
            json_id = node["id"]
        node = node[key]
    return json_id


def _container_factory(obj):
    if isinstance(obj, tagged.TaggedDict):
        result = tagged.TaggedDict({k: None for k in obj})
        result._tag = obj._tag
    elif isinstance(obj, tagged.TaggedList):
        result = tagged.TaggedList([None] * len(obj))
        result._tag = obj._tag
    elif isinstance(obj, dict):
        result = obj.__class__({k: None for k in obj})
    elif isinstance(obj, list):
        result = obj.__class__([None] * len(obj))
    elif isinstance(obj, tuple):
        result = [None] * len(obj)
    else:
        raise NotImplementedError()
    return result


def walk_and_modify(top, callback, ignore_implicit_conversion=False, postorder=True, _track_id=False):
    """Modify a tree by walking it with a callback function.  It also has
    the effect of doing a deep copy.

    Parameters
    ----------
    top : object
        The root of the tree.  May be a dict, list or other Python object.

    callback : callable
        A function to call at each node in the tree.  It takes either
        one or two arguments:

        - an instance from the tree
        - a json id (optional) DEPRECATED

        It may return a different instance in order to modify the
        tree.  If the singleton instance `~asdf.treeutil._RemoveNode`
        is returned, the node will be removed from the tree.

        The json id optional argument is deprecated. This function
        will no longer track ids. The json id is the context under which
        any relative URLs should be resolved.  It may be `None` if no
        ids are in the file

        The tree is traversed depth-first, with order specified by the
        ``postorder`` argument.

    postorder : bool
        Determines the order in which the callable is invoked on nodes of
        the tree.  If `True`, the callable will be invoked on children
        before their parents.  If `False`, the callable is invoked on the
        parents first.  Defaults to `True`.

    ignore_implicit_conversion : bool
        Controls whether warnings should be issued when implicitly converting a
        given type instance in the tree into a serializable object. The primary
        case for this is currently ``namedtuple``.

        Defaults to `False`.

    Returns
    -------
    tree : object
        The modified tree.

    """

    if postorder:
        modify = _itertree.leaf_first_modify_and_copy
    else:
        modify = _itertree.depth_first_modify_and_copy

    if callback.__code__.co_argcount == 2 and not _track_id:
        _track_id = True
        warnings.warn("the json_id callback argument is deprecated", AsdfDeprecationWarning)

    if _track_id:

        def wrapped_callback(obj, edge):
            json_id = _get_json_id(top, edge)
            return callback(obj, json_id)

    else:

        def wrapped_callback(obj, edge):
            return callback(obj)

    if ignore_implicit_conversion:
        container_factory = _container_factory
    else:

        def container_factory(obj):
            if isinstance(obj, tuple) and type(obj) != tuple:
                warnings.warn(f"Failed to serialize instance of {type(obj)}, converting to list instead", AsdfWarning)
            return _container_factory(obj)

    return modify(top, wrapped_callback, container_factory=container_factory)


def _get_children(node):
    """
    Retrieve the children (and their dict keys or list/tuple indices) of
    an ASDF tree node.

    Parameters
    ----------
    node : object
        an ASDF tree node

    Returns
    -------
    list of (object, object) tuples
        list of (identifier, child node) tuples, or empty list if the
        node has no children (either it is an empty container, or is
        a non-container type)
    """
    if isinstance(node, dict):
        return list(node.items())

    if isinstance(node, (list, tuple)):
        return list(enumerate(node))

    return []


def get_children(node):
    warnings.warn("asdf.treeutil.get_children is deprecated", AsdfDeprecationWarning)
    return _get_children(node)


get_children.__doc__ = _get_children.__doc__


def _is_container(node):
    """
    Determine if an ASDF tree node is an instance of a "container" type
    (i.e., value may contain child nodes).

    Parameters
    ----------
    node : object
        an ASDF tree node

    Returns
    -------
    bool
        True if node is a container, False otherwise
    """
    return isinstance(node, (dict, list, tuple))


def is_container(node):
    warnings.warn("asdf.treeutil.is_container is deprecated", AsdfDeprecationWarning)
    return _is_container(node)


is_container.__doc__ = _is_container.__doc__
