"""
Utilities for displaying the content of an ASDF tree.

Normally these tools only will introspect dicts, lists, and primitive values
(with an exception for arrays). However, if the object that is generated
by the converter mechanism has a __asdf_traverse__() method, then it will
call that method expecting a dict or list to be returned. The method can
return what it thinks is suitable for display.
"""

import sys

from ._node_info import create_tree
from .util import NotSet

__all__ = [
    "DEFAULT_MAX_COLS",
    "DEFAULT_MAX_ROWS",
    "DEFAULT_SHOW_VALUES",
    "render_tree",
]


DEFAULT_MAX_ROWS = 24
DEFAULT_MAX_COLS = 120
DEFAULT_SHOW_VALUES = True


def render_tree(
    node,
    max_rows=DEFAULT_MAX_ROWS,
    max_cols=DEFAULT_MAX_COLS,
    show_values=DEFAULT_SHOW_VALUES,
    filters=None,
    identifier="root",
    refresh_extension_manager=NotSet,
    extension_manager=None,
):
    """
    Render a tree as text with indents showing depth.
    """
    info = create_tree(
        key="title",
        node=node,
        identifier=identifier,
        filters=[] if filters is None else filters,
        refresh_extension_manager=refresh_extension_manager,
        extension_manager=extension_manager,
    )
    if info is None:
        return []

    renderer = _TreeRenderer(
        max_rows,
        max_cols,
        show_values,
    )
    return renderer.render(info)


class _TreeRenderer:
    """
    Render a _NodeInfo tree with indent showing depth.
    """

    def __init__(self, max_rows, max_cols, show_values):
        self._max_rows = max_rows
        self._max_cols = max_cols
        self._show_values = show_values
        self._isatty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def format_bold(self, value):
        """
        Wrap the input value in the ANSI escape sequence for increased intensity.
        """
        return self._format_code(value, 1)

    def format_faint(self, value):
        """
        Wrap the input value in the ANSI escape sequence for decreased intensity.
        """
        return self._format_code(value, 2)

    def format_italic(self, value):
        """
        Wrap the input value in the ANSI escape sequence for italic.
        """
        return self._format_code(value, 3)

    def _format_code(self, value, code):
        if not self._isatty:
            return f"{value}"
        return f"\x1b[{code}m{value}\x1b[0m"

    def render(self, info):
        self._mark_visible(info)

        lines, elided = self._render(info, set(), True)

        if elided:
            lines.append(self.format_faint(self.format_italic("Some nodes not shown.")))

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
        max_rows = (None, *self._max_rows)

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
        display. Likewise, active_depths is used to track which preceding
        depths are incomplete thus need continuing lines preceding in
        the tree display.
        """
        lines = []

        if info.visible is False:
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
            message = self.format_faint(self.format_italic(str(hidden_count) + " not shown"))
            lines.append(f"{prefix}{message}")

        return lines, elided

    def _render_node(self, info, active_depths, is_tail):
        prefix = self._make_prefix(info.depth, active_depths, is_tail)
        value = self._render_node_value(info)

        line = (
            f"{prefix}[{self.format_bold(info.identifier)}] {value}"
            if isinstance(info.parent_node, (list, tuple))
            else f"{prefix}{self.format_bold(info.identifier)} {value}"
        )

        if info.info is not None:
            line = line + self.format_faint(self.format_italic(" # " + info.info))
        visible_children = info.visible_children
        if len(visible_children) == 0 and len(info.children) > 0:
            line = line + self.format_italic(" ...")

        if info.recursive:
            line = line + " " + self.format_faint(self.format_italic("(recursive reference)"))

        if self._max_cols is not None and len(line) > self._max_cols:
            message = " (truncated)"
            line = line[0 : (self._max_cols - len(message))] + self.format_faint(self.format_italic(message))

        return line

    def _render_node_value(self, info):
        rendered_type = type(info.node).__name__

        if not info.children and self._show_values:
            try:
                s = f"{info.node}"
            except Exception:
                # if __str__ fails, don't fail info, instead use an empty string
                s = ""
            # if __str__ returns multiple lines also use an empty string
            if len(s.splitlines()) > 1:
                s = ""
            # if s is empty use the non-_show_values format below
            if s:
                return f"({rendered_type}): {s}"

        return f"({rendered_type})"

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
                prefix = prefix + "│ " if n in active_depths else prefix + "  "

        prefix = prefix + "└─" if is_tail else prefix + "├─"

        return self.format_faint(prefix)
