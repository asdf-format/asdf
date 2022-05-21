"""
Utilities for displaying the content of an ASDF tree.

Normally these tools only will introspect dicts, lists, and primitive values
(with an exception for arrays). However, if the object that is generated
by the converter mechanism has a __asdf_traverse__() method, then it will
call that method expecting a dict or list to be returned. The method can
return what it thinks is suitable for display.
"""
import re

import numpy as np

from .schema import load_schema
from .tags.core.ndarray import NDArrayType
from .treeutil import get_children
from .util import is_primitive

__all__ = [
    "DEFAULT_MAX_ROWS",
    "DEFAULT_MAX_COLS",
    "DEFAULT_SHOW_VALUES",
    "render_tree",
    "format_bold",
    "format_faint",
    "format_italic",
]


DEFAULT_MAX_ROWS = 24
DEFAULT_MAX_COLS = 120
DEFAULT_SHOW_VALUES = True

EXTENSION_MANAGER = None


def render_tree(
    node,
    max_rows=DEFAULT_MAX_ROWS,
    max_cols=DEFAULT_MAX_COLS,
    show_values=DEFAULT_SHOW_VALUES,
    filters=[],
    identifier="root",
    refresh_extension_manager=False,
):
    """
    Render a tree as text with indents showing depth.
    """
    info = _NodeInfo.from_root_node(identifier, node, refresh_extension_manager=refresh_extension_manager)

    if len(filters) > 0:
        if not _filter_tree(info, filters):
            return []

    renderer = _TreeRenderer(
        max_rows,
        max_cols,
        show_values,
    )
    return renderer.render(info)


def format_bold(value):
    """
    Wrap the input value in the ANSI escape sequence for increased intensity.
    """
    return _format_code(value, 1)


def format_faint(value):
    """
    Wrap the input value in the ANSI escape sequence for decreased intensity.
    """
    return _format_code(value, 2)


def format_italic(value):
    """
    Wrap the input value in the ANSI escape sequence for italic.
    """
    return _format_code(value, 3)


def _format_code(value, code):
    return "\x1B[{}m{}\x1B[0m".format(code, value)


def _get_schema_for_property(schema, attr):
    subschema = schema.get("properties", {}).get(attr, None)
    if subschema is not None:
        return subschema
    subschema = schema.get("properties", {}).get("patternProperties", None)
    if subschema:
        for key in subschema:
            if re.search(key, attr):
                return subschema[key]
    return {}


class _NodeInfo:
    """
    Container for a node, its state of visibility, and values used to display it.
    """

    @classmethod
    def from_root_node(cls, root_identifier, root_node, schema=None, refresh_extension_manager=False):
        """
        Build a _NodeInfo tree from the given ASDF root node.
        Intentionally processes the tree in breadth-first order so that recursively
        referenced nodes are displayed at their shallowest reference point.
        """
        from .asdf import AsdfFile, get_config
        from .extension import ExtensionManager

        af = AsdfFile()
        if refresh_extension_manager:
            config = get_config()
            af._extension_manager = ExtensionManager(config.extensions)
        extmgr = af.extension_manager

        current_nodes = [(None, root_identifier, root_node)]
        seen = set()
        root_info = None
        current_depth = 0
        while True:
            next_nodes = []

            for parent, identifier, node in current_nodes:
                if (isinstance(node, dict) or isinstance(node, tuple) or cls.supports_info(node)) and id(node) in seen:
                    info = _NodeInfo(parent, identifier, node, current_depth, recursive=True)
                    parent.children.append(info)
                else:
                    info = _NodeInfo(parent, identifier, node, current_depth)
                    if root_info is None:
                        root_info = info
                    if parent is not None:
                        if parent.schema is not None and not cls.supports_info(node):
                            # Extract subschema if it exists
                            subschema = _get_schema_for_property(parent.schema, identifier)
                            info.schema = subschema
                            info.title = subschema.get("title", None)
                        parent.children.append(info)
                    seen.add(id(node))
                    if cls.supports_info(node):
                        tnode = node.__asdf_traverse__()
                        # Look for a title for the attribute if it is a tagged object
                        tag = node._tag
                        tagdef = extmgr.get_tag_definition(tag)
                        schema_uri = tagdef.schema_uris[0]
                        schema = load_schema(schema_uri)
                        info.schema = schema
                        info.title = schema.get("title", None)
                    else:
                        tnode = node
                    if parent is None:
                        info.schema = schema
                    for child_identifier, child_node in get_children(tnode):
                        next_nodes.append((info, child_identifier, child_node))
                        # extract subschema if appropriate

            if len(next_nodes) == 0:
                break

            current_nodes = next_nodes
            current_depth += 1

        return root_info

    def __init__(self, parent, identifier, node, depth, recursive=False, visible=True):
        self.parent = parent
        self.identifier = identifier
        self.node = node
        self.depth = depth
        self.recursive = recursive
        self.visible = visible
        self.children = []
        self.title = None
        self.schema = None

    @classmethod
    def supports_info(cls, node):
        """
        This method determines if the node is an instance of a class that
        supports introspection by the info machinery. This determined by
        the presence of a __asdf_traverse__ method.
        """
        return hasattr(node, "__asdf_traverse__")

    @property
    def visible_children(self):
        return [c for c in self.children if c.visible]

    @property
    def parent_node(self):
        if self.parent is None:
            return None
        else:
            return self.parent.node


def _filter_tree(info, filters):
    """
    Remove nodes from the tree that get caught in the filters.
    Mutates the tree.
    """
    filtered_children = []
    for child in info.children:
        if _filter_tree(child, filters):
            filtered_children.append(child)
    info.children = filtered_children

    return len(info.children) > 0 or all(f(info.node, info.identifier) for f in filters)


class _TreeRenderer:
    """
    Render a _NodeInfo tree with indent showing depth.
    """

    def __init__(self, max_rows, max_cols, show_values):
        self._max_rows = max_rows
        self._max_cols = max_cols
        self._show_values = show_values

    def render(self, info):
        self._mark_visible(info)

        lines, elided = self._render(info, set(), True)

        if elided:
            lines.append(format_faint(format_italic("Some nodes not shown.")))

        return lines

    def _mark_visible(self, root_info):
        """
        Select nodes to display, respecting max_rows.  Nodes at lower
        depths will be prioritized.
        """
        if isinstance(self._max_rows, tuple):
            self._mark_visible_tuple(root_info)
        else:
            self._mark_visible_int(root_info)

    def _mark_visible_int(self, root_info):
        """
        Select nodes to display, obeying max_rows as an overall limit on
        the number of lines returned.
        """
        if self._max_rows is None:
            return

        if self._max_rows < 2:
            root_info.visible = False
            return

        current_infos = [root_info]
        # Reserve one row for the root node, and another for the
        # "Some nodes not shown." message.
        rows_left = self._max_rows - 2
        while True:
            next_infos = []

            for info in current_infos:
                if rows_left >= len(info.children):
                    rows_left -= len(info.children)
                    next_infos.extend(info.children)
                elif rows_left > 1:
                    for child in info.children[rows_left - 1 :]:
                        child.visible = False
                    next_infos.extend(info.children[0 : rows_left - 1])
                    rows_left = 0
                else:
                    for child in info.children:
                        child.visible = False

            if len(next_infos) == 0:
                break

            current_infos = next_infos

    def _mark_visible_tuple(self, root_info):
        """
        Select nodes to display, obeying the per-node max_rows value for
        each tree depth.
        """
        max_rows = (None,) + self._max_rows

        current_infos = [root_info]
        while True:
            next_infos = []

            for info in current_infos:
                if info.depth + 1 < len(max_rows):
                    rows_left = max_rows[info.depth + 1]
                    if rows_left is None or rows_left >= len(info.children):
                        next_infos.extend(info.children)
                    elif rows_left > 1:
                        for child in info.children[rows_left - 1 :]:
                            child.visible = False
                        next_infos.extend(info.children[0 : rows_left - 1])
                    else:
                        for child in info.children:
                            child.visible = False
                else:
                    for child in info.children:
                        child.visible = False

            if len(next_infos) == 0:
                break

            current_infos = next_infos

    def _render(self, info, active_depths, is_tail):
        """
        Render the tree.  Called recursively on child nodes.

        is_tail indicates if the child is the last of the children,
        needed to indicate the proper connecting character in the tree
        display. Likewise, active_depths is used to track which preceeding
        depths are incomplete thus need continuing lines preceding in
        the tree display.
        """
        lines = []

        if info.visible == False:
            return lines, True

        lines.append(self._render_node(info, active_depths, is_tail))

        elided = len(info.visible_children) < len(info.children)

        for i, child in enumerate(info.visible_children):
            if i == len(info.children) - 1:
                child_is_tail = True
                child_active_depths = active_depths
            else:
                child_is_tail = False
                child_active_depths = active_depths.union({info.depth})

            child_list, child_elided = self._render(child, child_active_depths, child_is_tail)
            lines.extend(child_list)
            elided = elided or child_elided

        num_visible_children = len(info.visible_children)
        if num_visible_children > 0 and num_visible_children != len(info.children):
            hidden_count = len(info.children) - num_visible_children
            prefix = self._make_prefix(info.depth + 1, active_depths, True)
            message = format_faint(format_italic(str(hidden_count) + " not shown"))
            lines.append("{}{}".format(prefix, message))

        return lines, elided

    def _render_node(self, info, active_depths, is_tail):
        prefix = self._make_prefix(info.depth, active_depths, is_tail)
        value = self._render_node_value(info)

        if isinstance(info.parent_node, list) or isinstance(info.parent_node, tuple):
            line = "{}[{}] {}".format(prefix, format_bold(info.identifier), value)
        else:
            line = "{}{} {}".format(prefix, format_bold(info.identifier), value)

        if info.title is not None:
            line = line + format_faint(format_italic(" # " + info.title))
        visible_children = info.visible_children
        if len(visible_children) == 0 and len(info.children) > 0:
            line = line + format_italic(" ...")

        if info.recursive:
            line = line + " " + format_faint(format_italic("(recursive reference)"))

        if self._max_cols is not None and len(line) > self._max_cols:
            message = " (truncated)"
            line = line[0 : (self._max_cols - len(message))] + format_faint(format_italic(message))

        return line

    def _render_node_value(self, info):
        rendered_type = type(info.node).__name__
        if is_primitive(info.node) and self._show_values:
            return "({}): {}".format(rendered_type, info.node)
        elif isinstance(info.node, NDArrayType) or isinstance(info.node, np.ndarray):
            return "({}): shape={}, dtype={}".format(rendered_type, info.node.shape, info.node.dtype.name)
        else:
            return "({})".format(rendered_type)

    def _make_prefix(self, depth, active_depths, is_tail):
        """
        Create a prefix for a displayed node, accounting for depth
        and including lines that show connections to other nodes.
        """
        prefix = ""

        if depth < 1:
            return prefix

        if depth >= 2:
            for n in range(0, depth - 1):
                if n in active_depths:
                    prefix = prefix + "│ "
                else:
                    prefix = prefix + "  "

        if is_tail:
            prefix = prefix + "└─"
        else:
            prefix = prefix + "├─"

        return format_faint(prefix)
