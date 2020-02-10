"""
Utilities for searching ASDF trees.
"""
import inspect
import re
import typing
import builtins

from .util import NotSet
from ._display import render_tree, DEFAULT_MAX_ROWS, DEFAULT_MAX_COLS, DEFAULT_SHOW_VALUES, format_italic, format_faint
from .treeutil import get_children, is_container


__all__ = ["AsdfSearchResult"]


class AsdfSearchResult:
    """
    Result of a call to AsdfFile.search.
    """
    def __init__(self, identifiers, node, filters=[], parent_node=None, max_rows=DEFAULT_MAX_ROWS, max_cols=DEFAULT_MAX_COLS, show_values=DEFAULT_SHOW_VALUES):
        self._identifiers = identifiers
        self._node = node
        self._filters = filters
        self._parent_node = parent_node
        self._max_rows = max_rows
        self._max_cols = max_cols
        self._show_values = show_values

    def format(self, max_rows=NotSet, max_cols=NotSet, show_values=NotSet):
        """
        Change formatting parameters of the rendered tree.

        Parameters
        ----------
        max_rows : int, tuple, None, or NotSet, optional
            Maximum number of lines to print.  Nodes that cannot be
            displayed will be elided with a message.
            If int, constrain total number of displayed lines.
            If tuple, constrain lines per node at the depth corresponding \
                to the tuple index.
            If None, display all lines.
            If NotSet, retain existing value.

        max_cols : int, None or NotSet, optional
            Maximum length of line to print.  Nodes that cannot
            be fully displayed will be truncated with a message.
            If int, constrain length of displayed lines.
            If None, line length is unconstrained.
            If NotSet, retain existing value.

        show_values : bool or NotSet, optional
            Set to False to disable display of primitive values in
            the rendered tree.
            Set to NotSet to retain existign value.

        Returns
        -------
        AsdfSearchResult
            the reformatted search result
        """
        if max_rows is NotSet:
            max_rows = self._max_rows

        if max_cols is NotSet:
            max_cols = self._max_cols

        if show_values is NotSet:
            show_values = self._show_values

        return AsdfSearchResult(
            self._identifiers,
            self._node,
            filters=self._filters,
            parent_node=self._parent_node,
            max_rows=max_rows,
            max_cols=max_cols,
            show_values=show_values
        )

    def _maybe_compile_pattern(self, query):
        if isinstance(query, str):
            return re.compile(query)
        else:
            return query

    def _safe_equals(self, a, b):
        try:
            result = (a == b)
            if isinstance(result, bool):
                return result
            else:
                return False
        except Exception:
            return False

    def _get_fully_qualified_type(self, value):
        value_type = type(value)
        if value_type.__module__ == "builtins":
            return value_type.__name__
        else:
            return ".".join([value_type.__module__, value_type.__name__])

    def search(self, key=NotSet, type=NotSet, value=NotSet, filter=None):
        """
        Further narrow the search.

        Parameters
        ----------
        key : NotSet, str, or any other object
            Search query that selects nodes by dict key or list index.
            If NotSet, the node key is unconstrained.
            If str, the input is searched among keys/indexes as a regular
            expression pattern.
            If any other object, node's key or index must equal the queried key.

        type : NotSet, str, or builtins.type
            Search query that selects nodes by type.
            If NotSet, the node type is unconstrained.
            If str, the input is searched among (fully qualified) node type
            names as a regular expression pattern.
            If builtins.type, the node must be an instance of the input.

        value : NotSet, str, or any other object
            Search query that selects nodes by value.
            If NotSet, the node value is unconstrained.
            If str, the input is searched among values as a regular
            expression pattern.
            If any other object, node's value must equal the queried value.

        filter : callable
            Callable that filters nodes by arbitrary criteria.
            The callable accepts one or two arguments:

            - the node
            - the node's list index or dict key (optional)

            and returns True to retain the node, or False to remove it from
            the search results.

        Returns
        -------
        AsdfSearchResult
            the subsequent search result
        """
        if not (type is NotSet or isinstance(type, str) or isinstance(type, typing.Pattern) or isinstance(type, builtins.type)):
            raise TypeError("type must be NotSet, str, regular expression, or instance of builtins.type")

        # value and key arguments can be anything, but pattern and str have special behavior

        key = self._maybe_compile_pattern(key)
        type = self._maybe_compile_pattern(type)
        value = self._maybe_compile_pattern(value)

        filter = _wrap_filter(filter)

        def _filter(node, identifier):
            if isinstance(key, typing.Pattern):
                if key.search(str(identifier)) is None:
                    return False
            elif key is not NotSet:
                if not self._safe_equals(identifier, key):
                    return False

            if isinstance(type, typing.Pattern):
                fully_qualified_node_type = self._get_fully_qualified_type(node)
                if type.search(fully_qualified_node_type) is None:
                    return False
            elif isinstance(type, builtins.type):
                if not isinstance(node, type):
                    return False

            if isinstance(value, typing.Pattern):
                if is_container(node):
                    # The string representation of a container object tends to
                    # include the child object values, but that's probably not
                    # what searchers want.
                    return False
                elif value.search(str(node)) is None:
                    return False
            elif value is not NotSet:
                if not self._safe_equals(node, value):
                    return False

            if filter is not None:
                if not filter(node, identifier):
                    return False

            return True

        return AsdfSearchResult(
            self._identifiers,
            self._node,
            filters=self._filters + [_filter],
            parent_node=self._parent_node,
            max_rows=self._max_rows,
            max_cols=self._max_cols,
            show_values=self._show_values
        )

    @property
    def node(self):
        """
        Retrieve the leaf node of a tree with one search result.

        Returns
        -------
        object
            the single node of the search result
        """

        results = self.nodes
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0]
        else:
            raise RuntimeError("More than one result")

    @property
    def path(self):
        """
        Retrieve the path to the leaf node of a tree with one search result.

        Returns
        -------
        str
            the path to the searched node
        """
        results = self.paths
        if len(results) == 0:
            return None
        elif len(results) == 1:
            return results[0]
        else:
            raise RuntimeError("More than one result")

    @property
    def nodes(self):
        """
        Retrieve all leaf nodes in the search results.

        Returns
        -------
        list of object
            every node in the search results (breadth-first order)
        """
        results = []

        def _callback(identifiers, node, children):
            if all(f(node, identifiers[-1]) for f in self._filters):
                results.append(node)

        _walk_tree_breadth_first(self._identifiers, self._node, _callback)
        return results

    @property
    def paths(self):
        """
        Retrieve the paths to all leaf nodes in the search results.

        Returns
        -------
        list of str
            the path to every node in the search results
        """
        results = []

        def _callback(identifiers, node, children):
            if all(f(node, identifiers[-1]) for f in self._filters):
                results.append(_build_path(identifiers))

        _walk_tree_breadth_first(self._identifiers, self._node, _callback)
        return results

    def __repr__(self):
        lines = render_tree(
            self._node,
            max_rows=self._max_rows,
            max_cols=self._max_cols,
            show_values=self._show_values,
            filters=self._filters,
            identifier=self._identifiers[-1]
        )

        if len(lines) == 0:
            return format_faint(format_italic("No results found."))
        else:
            return "\n".join(lines)

    def __getitem__(self, key):
        if isinstance(self._node, dict) or isinstance(self._node, list) or isinstance(self._node, tuple):
            child = self._node[key]
        else:
            raise TypeError("This node cannot be indexed")

        return AsdfSearchResult(
            self._identifiers + [key],
            child,
            filters=self._filters,
            parent_node=self._node,
            max_rows=self._max_rows,
            max_cols=self._max_cols,
            show_values=self._show_values,
        )


def _walk_tree_breadth_first(root_identifiers, root_node, callback):
    """
    Walk the tree in breadth-first order (useful for prioritizing
    lower-depth nodes).
    """
    current_nodes = [(root_identifiers, root_node)]
    seen = set()
    while True:
        next_nodes = []

        for identifiers, node in current_nodes:
            if (isinstance(node, dict) or isinstance(node, list) or isinstance(node, tuple)) and id(node) in seen:
                continue

            children = get_children(node)
            callback(identifiers, node, [c for _, c in children])
            next_nodes.extend([(identifiers + [i], c) for i, c in children])
            seen.add(id(node))

        if len(next_nodes) == 0:
            break

        current_nodes = next_nodes


def _build_path(identifiers):
    """
    Generate the Python code needed to extract the identified node.
    """
    if len(identifiers) == 0:
        return ""
    else:
        return identifiers[0] + "".join("[{}]".format(repr(i)) for i in identifiers[1:])


def _wrap_filter(filter):
    """
    Ensure that filter callable accepts the expected number of arguments.
    """
    if filter is None:
        return None
    else:
        arity = len(inspect.signature(filter).parameters)
        if arity == 1:
            return lambda n, i: filter(n)
        elif arity == 2:
            return filter
        else:
            raise ValueError("filter must accept 1 or 2 arguments")
