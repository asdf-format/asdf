"""
Implementation of command for displaying differences between two ASDF files.
"""

import argparse
import sys

import jmespath
import numpy as np
from numpy import array_equal

import asdf
from asdf.extension._serialization_context import BlockAccess
from asdf.tagged import Tagged

from .main import Command

__all__ = ["diff"]


NDARRAY_TAG = "core/ndarray"


class Diff(Command):  # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""

    @classmethod
    def setup_arguments(cls, subparsers):
        epilog = """
examples:
  diff two files:
    asdftool diff file_before.asdf file_after.asdf
  ignore differences in the file's ASDF metadata:
    asdftool diff file_before.asdf file_after.asdf -i '[asdf_library,history]'
  ignore differences in the 'foo' field of all objects in a list:
    asdftool diff file_before.asdf file_after.asdf -i 'path.to.some_list[*].foo'

See https://jmespath.org/ for more information on constructing
JMESPath expressions.
    """.strip()

        parser = subparsers.add_parser(
            "diff",
            description="Report differences between two ASDF files",
            epilog=epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            help="Report differences between two ASDF files",
        )

        parser.add_argument("filenames", metavar="asdf_file", nargs=2, help="The ASDF files to compare.")

        parser.add_argument(
            "-m",
            "--minimal",
            action="store_true",
            help="Show minimal differences between the two files.",
        )

        parser.add_argument(
            "-i",
            "--ignore",
            action="append",
            dest="ignore",
            help="JMESPath expression indicating tree nodes that should be ignored.",
        )

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        return diff(args.filenames, args.minimal, ignore=args.ignore)


class ArrayNode:
    """This class is used to represent unique dummy nodes in the diff tree. In
    general these dummy nodes will be list elements that we want to keep track
    of but not necessarily display. This allows the diff output to be
    cleaner."""

    def __init__(self, name, index):
        self.name = name
        self.index = index

    def __hash__(self):
        return hash(self.name)


class PrintTree:
    """This class is used to remember the nodes in the tree that have already
    been displayed in the diff output.
    """

    def __init__(self):
        self.__tree = {"visited": False, "children": {}}

    def get_print_list(self, node_list):
        at_end = False
        print_list = []
        current = self.__tree
        for node in ["tree", *node_list]:
            if at_end:
                print_list.append(node)
            elif node not in current["children"]:
                print_list.append(node)
                at_end = True
            elif not current["children"][node]["visited"]:
                print_list.append(node)
            else:
                print_list.append(None)
            if not at_end:
                current = current["children"][node]
        return print_list

    def __setitem__(self, node_list, visit):
        if not isinstance(node_list, list):
            msg = "node_list parameter must be an instance of list"
            raise TypeError(msg)
        current = self.__tree
        for node in ["tree", *node_list]:
            if node not in current["children"]:
                current["children"][node] = {"visited": True, "children": {}}
            current = current["children"][node]


class DiffContext:
    """Class that contains context data of the diff to be computed"""

    def __init__(self, asdf0, asdf1, iostream, minimal=False, ignore_ids=None):
        self.asdf0 = asdf0
        self.asdf1 = asdf1
        self.iostream = iostream
        self.minimal = minimal
        self.print_tree = PrintTree()

        if ignore_ids is None:
            self.ignore_ids = set()
        else:
            self.ignore_ids = ignore_ids

        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            RED = "\x1b[31m"
            GREEN = "\x1b[32m"
            RESET = "\x1b[0m"
        else:
            RED = ""
            GREEN = ""
            RESET = ""

        self.RESET_NEWLINE = RESET + "\n"
        self.LIST_MARKER = "-"
        self.THIS_MARKER = GREEN + "> "
        self.THAT_MARKER = RED + "< "


def print_tree_context(diff_ctx, node_list, other, use_marker, last_was_list):
    """Print context information indicating location in ASDF tree."""
    prefix = ""
    marker = diff_ctx.THAT_MARKER if other else diff_ctx.THIS_MARKER
    for node in diff_ctx.print_tree.get_print_list(node_list):
        if node is not None:
            node_ = diff_ctx.LIST_MARKER if isinstance(node, ArrayNode) else node + ":"
            # All of this logic is just to make the display of arrays prettier
            if use_marker:
                line_prefix = " " if last_was_list else marker + prefix[2:]
                line_suffix = "" if node_ == diff_ctx.LIST_MARKER else diff_ctx.RESET_NEWLINE
            else:
                line_prefix = prefix
                line_suffix = diff_ctx.RESET_NEWLINE
            diff_ctx.iostream.write(line_prefix + node_ + line_suffix)
            last_was_list = node_ == diff_ctx.LIST_MARKER
        prefix += "  "
    diff_ctx.print_tree[node_list] = True
    return last_was_list


def print_in_tree(diff_ctx, node_list, thing, other, use_marker=False, last_was_list=False, ignore_lwl=False):
    """Recursively print tree context and diff information about object."""
    last_was_list = print_tree_context(diff_ctx, node_list, other, use_marker, last_was_list)
    # If tree element is list, recursively print list contents
    if isinstance(thing, list):
        for i, subthing in enumerate(thing):
            key = ArrayNode(f"{node_list[-1]}_{i}", i)
            last_was_list = print_in_tree(
                diff_ctx,
                [*node_list, key],
                subthing,
                other,
                use_marker=True,
                last_was_list=last_was_list,
                ignore_lwl=ignore_lwl,
            )
    # If tree element is dictionary, recursively print dictionary contents
    elif isinstance(thing, dict):
        for key in sorted(thing.keys()):
            last_was_list = print_in_tree(
                diff_ctx,
                [*node_list, key],
                thing[key],
                other,
                use_marker=True,
                last_was_list=last_was_list,
                ignore_lwl=ignore_lwl,
            )
    # Print difference between leaf objects (no need to recurse further)
    else:
        use_marker = not last_was_list or ignore_lwl
        marker = diff_ctx.THAT_MARKER if other else diff_ctx.THIS_MARKER
        prefix = marker + "  " * len(node_list) if use_marker else " "
        diff_ctx.iostream.write(prefix + str(thing) + diff_ctx.RESET_NEWLINE)
        last_was_list = False
    return last_was_list


def compare_objects(diff_ctx, obj0, obj1, keys=None):
    """Displays diff of two objects if they are not equal"""
    keys = [] if keys is None else keys

    if obj0 != obj1:
        print_in_tree(diff_ctx, keys, obj0, False, ignore_lwl=True)
        print_in_tree(diff_ctx, keys, obj1, True, ignore_lwl=True)


def print_dict_diff(diff_ctx, tree, node_list, keys, other):
    """Recursively traverses dictionary object and displays differences"""
    for key in keys:
        if diff_ctx.minimal:
            nodes = node_list
            key_ = key
        else:
            nodes = [*node_list, key]
            key_ = tree[key]
        use_marker = not diff_ctx.minimal
        print_in_tree(diff_ctx, nodes, key_, other, use_marker=use_marker)


def _load_array(asdf_file, array_dict):
    # the array_dict may not be tagged if the array is inline
    # in this case just use what's in "data"
    if not hasattr(array_dict, "_tag"):
        return array_dict["data"]
    conv = asdf_file.extension_manager.get_converter_for_type(np.ndarray)
    sctx = asdf_file._create_serialization_context(BlockAccess.READ)
    return conv.from_yaml_tree(array_dict, array_dict._tag, sctx)


def _human_list(line, separator="and"):
    """
    Formats a list for human readability.

    Parameters
    ----------
    line : sequence
        A sequence of strings

    separator : string, optional
        The word to use between the last two entries.  Default:
        ``"and"``.

    Returns
    -------
    formatted_list : string

    Examples
    --------
    >>> _human_list(["vanilla", "strawberry", "chocolate"], "or")
    'vanilla, strawberry or chocolate'
    """
    if len(line) == 1:
        return line[0]

    return ", ".join(line[:-1]) + " " + separator + " " + line[-1]


def compare_ndarrays(diff_ctx, array0, array1, keys):
    """Compares two ndarray objects"""
    if isinstance(array0, list):
        array0 = {"data": array0}
    if isinstance(array1, list):
        array1 = {"data": array1}

    ignore_keys = {"source", "data"}
    compare_dicts(diff_ctx, array0, array1, keys, ignore_keys)

    differences = []
    for field in ["shape", "datatype"]:
        if array0.get(field) != array1.get(field):
            differences.append(field)

    value0 = _load_array(diff_ctx.asdf0, array0)
    value1 = _load_array(diff_ctx.asdf1, array1)

    if not array_equal(value0, value1):
        differences.append("contents")

    if differences:
        msg = f"ndarrays differ by {_human_list(differences)}"
        print_in_tree(diff_ctx, keys, msg, False, ignore_lwl=True)
        print_in_tree(diff_ctx, keys, msg, True, ignore_lwl=True)


def both_are_ndarrays(tree0, tree1):
    """Returns True if both inputs correspond to ndarrays, False otherwise"""
    if not (isinstance(tree0, Tagged) and isinstance(tree1, Tagged)):
        return False
    if not (NDARRAY_TAG in tree0._tag and NDARRAY_TAG in tree1._tag):
        return False
    return True


def compare_dicts(diff_ctx, dict0, dict1, keys, ignores=None):
    """Recursively compares two dictionary objects"""
    ignores = set() if ignores is None else ignores

    keys0 = set(dict0.keys()) - ignores
    keys1 = set(dict1.keys()) - ignores
    # Recurse into subtree elements that are shared by both trees
    for key in sorted(keys0 & keys1):
        obj0 = dict0[key]
        obj1 = dict1[key]
        compare_trees(diff_ctx, obj0, obj1, keys=[*keys, key])
    # Display subtree elements existing only in this tree
    print_dict_diff(diff_ctx, dict0, keys, sorted(keys0 - keys1), False)
    # Display subtree elements existing only in that tree
    print_dict_diff(diff_ctx, dict1, keys, sorted(keys1 - keys0), True)


def compare_trees(diff_ctx, tree0, tree1, keys=None):
    """Recursively traverses two ASDF tree and compares them"""
    keys = [] if keys is None else keys

    if id(tree0) in diff_ctx.ignore_ids and id(tree1) in diff_ctx.ignore_ids:
        return

    if both_are_ndarrays(tree0, tree1):
        compare_ndarrays(diff_ctx, tree0, tree1, keys)
    elif isinstance(tree0, dict) and isinstance(tree1, dict):
        compare_dicts(diff_ctx, tree0, tree1, keys)
    elif isinstance(tree0, list) and isinstance(tree1, list):
        for i, (obj0, obj1) in enumerate(zip(tree0, tree1)):
            key = ArrayNode(f"item_{i}", i)
            compare_trees(diff_ctx, obj0, obj1, [*keys, key])
    else:
        compare_objects(diff_ctx, tree0, tree1, keys)


def diff(filenames, minimal, iostream=sys.stdout, ignore=None):
    """
    Compare two ASDF files and write diff output to the stdout
    or the specified I/O stream.

    filenames : list of str
        List of ASDF filenames to compare.  Must be length 2.

    minimal : boolean
        Set to True to forego some pretty-printing to minimize
        the diff output.

    iostream : io.TextIOBase, optional
        Text-mode stream to write the diff, e.g., sys.stdout
        or an io.StringIO instance.  Defaults to stdout.

    ignore : list of str, optional
        List of JMESPath expressions indicating tree nodes that
        should be ignored.
    """
    ignore_expressions = [] if ignore is None else [jmespath.compile(e) for e in ignore]

    try:
        with (
            asdf.open(filenames[0], _force_raw_types=True) as asdf0,
            asdf.open(
                filenames[1],
                _force_raw_types=True,
            ) as asdf1,
        ):
            ignore_ids = set()
            for expression in ignore_expressions:
                for tree in [asdf0.tree, asdf1.tree]:
                    result = expression.search(tree)
                    if result is not None:
                        ignore_ids.add(id(result))
                    if isinstance(result, list):
                        for elem in result:
                            ignore_ids.add(id(elem))
                    elif isinstance(result, dict):
                        for value in result.values():
                            ignore_ids.add(id(value))

            diff_ctx = DiffContext(asdf0, asdf1, iostream, minimal=minimal, ignore_ids=ignore_ids)
            compare_trees(diff_ctx, asdf0.tree, asdf1.tree)

    except ValueError as err:
        raise RuntimeError(str(err)) from err
