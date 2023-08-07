"""
Implementation of the asdf.info(...) function.  This is just a thin wrapper
around _display module code.
"""
import pathlib
from contextlib import contextmanager

from ._display import DEFAULT_MAX_COLS, DEFAULT_MAX_ROWS, DEFAULT_SHOW_VALUES, render_tree
from .asdf import AsdfFile, open_asdf

__all__ = ["info"]


def info(node_or_path, max_rows=DEFAULT_MAX_ROWS, max_cols=DEFAULT_MAX_COLS, show_values=DEFAULT_SHOW_VALUES):
    """
    Print a rendering of an ASDF tree or sub-tree to stdout.

    Parameters
    ----------
    node_or_path : str, pathlib.Path, asdf.asdf.AsdfFile, or any ASDF tree node
        The tree or sub-tree to render.  Strings and Path objects
        will first be passed to asdf.open(...).

    max_rows : int, tuple, or None, optional
        Maximum number of lines to print.  Nodes that cannot be
        displayed will be elided with a message.
        If int, constrain total number of displayed lines.
        If tuple, constrain lines per node at the depth corresponding \
            to the tuple index.
        If None, display all lines.

    max_cols : int or None, optional
        Maximum length of line to print.  Nodes that cannot
        be fully displayed will be truncated with a message.
        If int, constrain length of displayed lines.
        If None, line length is unconstrained.

    show_values : bool, optional
        Set to False to disable display of primitive values in
        the rendered tree.
    """
    with _manage_node(node_or_path) as node:
        lines = render_tree(node, max_rows=max_rows, max_cols=max_cols, show_values=show_values, identifier="root")
        print("\n".join(lines))


@contextmanager
def _manage_node(node_or_path):
    if isinstance(node_or_path, (str, pathlib.Path)):
        with open_asdf(node_or_path) as af:
            yield af.tree

    elif isinstance(node_or_path, AsdfFile):
        yield node_or_path.tree

    else:
        yield node_or_path
