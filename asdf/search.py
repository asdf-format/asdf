"""
Utilities for searching ASDF trees.
"""

import builtins
import inspect
import re
import typing
import warnings

from ._display import DEFAULT_MAX_COLS, DEFAULT_MAX_ROWS, DEFAULT_SHOW_VALUES, render_tree
from ._node_info import collect_schema_info
from .treeutil import get_children, is_container
from .util import NotSet

__all__ = ["AsdfSearchResult"]


class AsdfSearchResult:
    """
    Result of a call to AsdfFile.search.
    """

    def __init__(
        self,
        identifiers,
        node,
        filters=None,
        parent_node=None,
        max_rows=DEFAULT_MAX_ROWS,
        max_cols=DEFAULT_MAX_COLS,
        show_values=DEFAULT_SHOW_VALUES,
    ):
        self._identifiers = identifiers
        self._node = node
        self._filters = [] if filters is None else filters
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
            show_values=show_values,
        )

    def _maybe_compile_pattern(self, query):
        if isinstance(query, str):
            return re.compile(query)

        return query

    def _safe_equals(self, a, b):
        try:
            result = a == b

        except Exception:
            return False

        if isinstance(result, bool):
            return result

        return False

    def _get_fully_qualified_type(self, value):
        value_type = type(value)
        if value_type.__module__ == "builtins":
            return value_type.__name__

        return ".".join([value_type.__module__, value_type.__name__])

    def search(self, key=NotSet, type_=NotSet, value=NotSet, filter_=None):
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

        type_ : NotSet, str, or builtins.type
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

        filter_ : callable
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
        if not (isinstance(type_, (str, typing.Pattern, builtins.type)) or type_ is NotSet):
            msg = "type must be NotSet, str, regular expression, or instance of builtins.type"
            raise TypeError(msg)

        # value and key arguments can be anything, but pattern and str have special behavior

        key = self._maybe_compile_pattern(key)
        type_ = self._maybe_compile_pattern(type_)
        value = self._maybe_compile_pattern(value)

        filter_ = _wrap_filter(filter_)

        def _filter(node, identifier):
            if isinstance(key, typing.Pattern):
                if key.search(str(identifier)) is None:
                    return False

            elif key is not NotSet and not self._safe_equals(identifier, key):
                return False

            if isinstance(type_, typing.Pattern):
                fully_qualified_node_type = self._get_fully_qualified_type(node)
                if type_.search(fully_qualified_node_type) is None:
                    return False

            elif isinstance(type_, builtins.type) and not isinstance(node, type_):
                return False

            if isinstance(value, typing.Pattern):
                if is_container(node):
                    # The string representation of a container object tends to
                    # include the child object values, but that's probably not
                    # what searchers want.
                    return False

                if value.search(str(node)) is None:
                    return False

            elif value is not NotSet and not self._safe_equals(node, value):
                return False

            if filter_ is not None and not filter_(node, identifier):
                return False

            return True

        return AsdfSearchResult(
            self._identifiers,
            self._node,
            filters=[*self._filters, _filter],
            parent_node=self._parent_node,
            max_rows=self._max_rows,
            max_cols=self._max_cols,
            show_values=self._show_values,
        )

    def replace(self, value):
        """
        Assign a new value in place of all leaf nodes in the
        search results.

        Parameters
        ----------
        value : object
        """
        results = []

        def _callback(identifiers, parent, node, children):
            if all(f(node, identifiers[-1]) for f in self._filters):
                results.append((identifiers[-1], parent))

        _walk_tree_breadth_first(self._identifiers, self._node, _callback)

        for identifier, parent in results:
            parent[identifier] = value

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

        if len(results) == 1:
            return results[0]

        msg = "More than one result"
        raise RuntimeError(msg)

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

        if len(results) == 1:
            return results[0]

        msg = "More than one result"
        raise RuntimeError(msg)

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

        def _callback(identifiers, parent, node, children):
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

        def _callback(identifiers, parent, node, children):
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
            identifier=self._identifiers[-1],
        )

        if len(lines) == 0:
            return "No results found."

        return "\n".join(lines)

    def schema_info(self, key="description", preserve_list=True, refresh_extension_manager=NotSet):
        """
        Get a nested dictionary of the schema information for a given key, relative to this search result.

        Parameters
        ----------
        key : str
            The key to look up.
            Default: "description"
        preserve_list : bool
            If True, then lists are preserved. Otherwise, they are turned into dicts.
        refresh_extension_manager : bool
            DEPRECATED
            If `True`, refresh the extension manager before looking up the
            key.  This is useful if you want to make sure that the schema
            data for a given key is up to date.
        """
        if refresh_extension_manager is not NotSet:
            warnings.warn("refresh_extension_manager is deprecated", DeprecationWarning)

        return collect_schema_info(
            key,
            None,
            self._node,
            filters=self._filters,
            preserve_list=preserve_list,
            refresh_extension_manager=refresh_extension_manager,
        )

    def __getitem__(self, key):
        if isinstance(self._node, (dict, list, tuple)) or hasattr(self._node, "__asdf_traverse__"):
            child = self._node.__asdf_traverse__()[key] if hasattr(self._node, "__asdf_traverse__") else self._node[key]
        else:
            msg = "This node cannot be indexed"
            raise TypeError(msg)

        return AsdfSearchResult(
            [*self._identifiers, key],
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
    current_nodes = [(root_identifiers, None, root_node)]
    seen = set()
    while True:
        next_nodes = []

        for identifiers, parent, node in current_nodes:
            if (isinstance(node, (dict, list, tuple)) or hasattr(node, "__asdf_traverse__")) and id(node) in seen:
                continue
            tnode = node.__asdf_traverse__() if hasattr(node, "__asdf_traverse__") else node
            children = get_children(tnode)
            callback(identifiers, parent, node, [c for _, c in children])
            next_nodes.extend([([*identifiers, i], node, c) for i, c in children])
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

    return identifiers[0] + "".join(f"[{i!r}]" for i in identifiers[1:])


def _wrap_filter(filter_):
    """
    Ensure that filter callable accepts the expected number of arguments.
    """
    if filter_ is None:
        return None

    arity = len(inspect.signature(filter_).parameters)
    if arity == 1:
        return lambda n, i: filter_(n)

    if arity == 2:
        return filter_

    msg = "filter must accept 1 or 2 arguments"
    raise ValueError(msg)
