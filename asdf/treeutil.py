# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
"""
Utility functions for managing tree-like data structures.
"""

import warnings
import types
from contextlib import contextmanager

from . import tagged


__all__ = ["walk", "iter_tree", "walk_and_modify", "get_children", "is_container"]


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


class _TreeModificationContext:
    """
    Context of a call to walk_and_modify, which includes a map
    of already modified nodes, a list of generators to drain
    before exiting the call, and a set of node object ids that
    are currently pending modification.

    Instances of this class are context managers that track
    how many times they have been entered, and only drain
    generators and reset themselves when exiting the outermost
    context.  They are also collections that map unmodified
    nodes to the corresponding modified result.
    """
    def __init__(self):
        self._map = {}
        self._generators = []
        self._depth = 0
        self._pending = set()

    def add_generator(self, generator):
        """
        Add a generator that should be drained before exiting
        the outermost call to walk_and_modify.
        """
        self._generators.append(generator)

    def is_pending(self, node):
        """
        Return True if the node is already being modified.
        This will not be the case unless the node contains a
        reference to itself somewhere among its descendents.
        """
        return id(node) in self._pending

    @contextmanager
    def pending(self, node):
        """
        Context manager that marks a node as pending for the
        duration of the context.
        """
        if id(node) in self._pending:
            raise RuntimeError(
                "Unhandled cycle in tree.  This is possibly a bug "
                "in extension code, which should be yielding "
                "nodes that may contain reference cycles."
            )

        self._pending.add(id(node))
        try:
            yield self
        finally:
            self._pending.remove(id(node))

    def __enter__(self):
        self._depth += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._depth -= 1

        if self._depth == 0:
            # If we're back to 0 depth, then we're exiting
            # the outermost context, so it's time to drain
            # the generators and reset this object for next
            # time.
            if exc_type is None:
                self._drain_generators()
            self._generators = []
            self._map = {}
            self._pending = set()

    def _drain_generators(self):
        """
        Drain each generator we've accumulated during this
        call to walk_and_modify.
        """
        # Generator code may add yet more generators
        # to the list, so we need to loop until the
        # list is empty.
        while len(self._generators) > 0:
            generators = self._generators
            self._generators = []
            for generator in generators:
                for _ in generator:
                    # Subsequent yields of the generator should
                    # always return the same value.  What we're
                    # really doing here is executing the generator's
                    # remaining code, to further modify that first
                    # yielded object.
                    pass

    def __contains__(self, node):
        return id(node) in self._map

    def __getitem__(self, node):
        return self._map[id(node)][1]

    def __setitem__(self, node, result):
        if id(node) in self._map:
            # This indicates that an already defined
            # modified node is being replaced, which is an
            # error because it breaks references within the
            # tree.
            raise RuntimeError("Node already has an associated result")

        self._map[id(node)] = (node, result)


class _PendingValue:
    """
    Class of the PendingValue singleton instance.  The presence of the instance
    in an asdf tree indicates that extension code is failing to handle
    reference cycles.
    """
    def __repr__(self):
        return "PendingValue"


PendingValue = _PendingValue()


def walk_and_modify(top, callback, ignore_implicit_conversion=False, postorder=True, _context=None):
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
        case for this is currently `namedtuple`.

        Defaults to `False`.

    Returns
    -------
    tree : object
        The modified tree.

    """
    callback_arity = callback.__code__.co_argcount
    if callback_arity < 1 or callback_arity > 2:
        raise ValueError("Expected callback to accept one or two arguments")

    def _handle_generator(result):
        # If the result is a generator, generate one value to
        # extract the true result, then register the generator
        # to be drained later.
        if isinstance(result, types.GeneratorType):
            generator = result
            result = next(generator)
            _context.add_generator(generator)

        return result

    def _handle_callback(node, json_id):
        if callback_arity == 1:
            result = callback(node)
        else:
            result = callback(node, json_id)

        return _handle_generator(result)

    def _handle_mapping(node, json_id):
        result = node.__class__()
        if isinstance(node, tagged.Tagged):
            result._tag = node._tag

        pending_items = {}
        for key, value in node.items():
            if _context.is_pending(value):
                # The child node is pending modification, which means
                # it must be its own ancestor.  Assign the special
                # PendingValue instance for now, and note that we'll
                # need to fill in the real value later.
                pending_items[key] = value
                result[key] = PendingValue
            else:
                value = _recurse(value, json_id)
                if value is not None:
                    result[key] = value

        yield result

        if len(pending_items) > 0:
            # Now that we've yielded, the pending children should
            # be available.
            for key, value in pending_items.items():
                value = _recurse(value, json_id)
                if value is not None:
                    result[key] = value
                else:
                    # The callback may have decided to delete
                    # this node after all.
                    del result[key]

    def _handle_mutable_sequence(node, json_id):
        result = node.__class__()
        if isinstance(node, tagged.Tagged):
            result._tag = node._tag

        pending_items = {}
        for i, value in enumerate(node):
            if _context.is_pending(value):
                # The child node is pending modification, which means
                # it must be its own ancestor.  Assign the special
                # PendingValue instance for now, and note that we'll
                # need to fill in the real value later.
                pending_items[i] = value
                result.append(PendingValue)
            else:
                result.append(_recurse(value, json_id))

        yield result

        for i, value in pending_items.items():
            # Now that we've yielded, the pending children should
            # be available.
            result[i] = _recurse(value, json_id)

    def _handle_immutable_sequence(node, json_id):
        # Immutable sequences containing themselves are impossible
        # to construct (well, maybe possible in a C extension, but
        # we're not going to worry about that), so we don't need
        # to yield here.
        contents = [_recurse(value, json_id) for value in node]

        try:
            result = node.__class__(contents)
            if isinstance(node, tagged.Tagged):
                result._tag = node._tag
        except TypeError:
            # The derived class signature is different, so simply store the
            # list representing the contents. Currently this is primarly
            # intended to handle namedtuple and NamedTuple instances.
            if not ignore_implicit_conversion:
                msg = "Failed to serialize instance of {}, converting to list instead"
                warnings.warn(msg.format(type(node)))
            result = contents

        return result

    def _handle_children(node, json_id):
        if isinstance(node, dict):
            result = _handle_mapping(node, json_id)
        elif isinstance(node, tuple):
            result = _handle_immutable_sequence(node, json_id)
        elif isinstance(node, list):
            result = _handle_mutable_sequence(node, json_id)
        else:
            result = node

        return _handle_generator(result)

    def _recurse(node, json_id=None):
        if node in _context:
            # The node's modified result has already been
            # created, all we need to do is return it.  This
            # occurs when the tree contains multiple references
            # to the same object id.
            return _context[node]

        # Inform the context that we're going to start modifing
        # this node.
        with _context.pending(node):
            # Take note of the "id" field, in case we're modifying
            # a schema and need to know the namespace for resolving
            # URIs.
            if isinstance(node, dict) and "id" in node:
                json_id = node["id"]

            if postorder:
                # If this is a postorder modification, invoke the
                # callback on this node's children first.
                result = _handle_children(node, json_id)
                result = _handle_callback(result, json_id)
            else:
                # Otherwise, invoke the callback on the node first,
                # then its children.
                result = _handle_callback(node, json_id)
                result = _handle_children(result, json_id)

        # Store the result in the context, in case there are
        # additional references to the same node elsewhere in
        # the tree.
        _context[node] = result

        return result

    if _context is None:
        _context = _TreeModificationContext()

    with _context:
        return _recurse(top)
        # Generators will be drained here, if this is the outermost
        # call to walk_and_modify.


def get_children(node):
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
    elif isinstance(node, list) or isinstance(node, tuple):
        return list(enumerate(node))
    else:
        return []


def is_container(node):
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
    return isinstance(node, dict) or isinstance(node,list) or isinstance(node, tuple)
