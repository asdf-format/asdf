# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Implementation of command for displaying differences between two ASDF files.
"""


import os
import sys
from numpy import array_equal
try:
    # Provides cross-platform color support
    import colorama
    colorama.init()
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    RESET = colorama.Style.RESET_ALL
except ImportError:
    from sys import platform
    # These platforms should support ansi color codes
    if platform.startswith('linux') or platform.startswith('darwin'):
        RED = '\x1b[31m'
        GREEN = '\x1b[32m'
        RESET = '\x1b[0m'
    else:
        RED = ''
        GREEN = ''
        RESET = ''

from .main import Command
from .. import AsdfFile
from .. import treeutil
from ..tagged import Tagged
from ..util import human_list
from ..tags.core.ndarray import NDArrayType


__all__ = ['diff']


RESET_NEWLINE = RESET + '\n'
NDARRAY_TAG = 'core/ndarray'
LIST_MARKER = '-'
THIS_MARKER = GREEN + "> "
THAT_MARKER = RED + "< "


class Diff(Command): # pragma: no cover
    """This class is the plugin implementation for the asdftool runner."""
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            str("diff"), help="Report differences between two ASDF files",
            description="""Reports differences between two ASDF files""")

        parser.add_argument(
            'filenames', metavar='asdf_file', nargs=2,
            help="The ASDF files to compare.")

        parser.add_argument(
            '-m', '--minimal', action='store_true',
            help="Show minimal differences between the two files")

        parser.set_defaults(func=cls.run)
        return parser

    @classmethod
    def run(cls, args):
        return diff(args.filenames, args.minimal)

class ArrayNode(object):
    """This class is used to represent unique dummy nodes in the diff tree. In
    general these dummy nodes will be list elements that we want to keep track
    of but not necessarily display. This allows the diff output to be
    cleaner."""
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return hash(self.name)

class PrintTree(object):
    """This class is used to remember the nodes in the tree that have already
    been displayed in the diff output.
    """
    def __init__(self):
        self.__tree = dict(visited=False, children=dict())

    def get_print_list(self, node_list):
        at_end = False
        print_list = []
        current = self.__tree
        for node in ['tree'] + node_list:
            if at_end:
                print_list.append(node)
            elif not node in current['children']:
                print_list.append(node)
                at_end = True
            elif not current['children'][node]['visited']:
                print_list.append(node)
            else:
                print_list.append(None)
            if not at_end:
                current = current['children'][node]
        return print_list

    def __setitem__(self, node_list, visit):
        assert isinstance(node_list, list)
        current = self.__tree
        for node in ['tree'] + node_list:
            if not node in current['children']:
                current['children'][node] = dict(visited=True, children=dict())
            current = current['children'][node]

class DiffContext(object):
    """Class that contains context data of the diff to be computed"""
    def __init__(self, asdf0, asdf1, iostream, minimal=False):
        self.asdf0 = asdf0
        self.asdf1 = asdf1
        self.iostream = iostream
        self.minimal = minimal
        self.print_tree = PrintTree()

def print_tree_context(diff_ctx, node_list, other, use_marker, last_was_list):
    """Print context information indicating location in ASDF tree."""
    prefix = ""
    marker = THAT_MARKER if other else THIS_MARKER
    for node in diff_ctx.print_tree.get_print_list(node_list):
        if node is not None:
            node = LIST_MARKER if isinstance(node, ArrayNode) else node + ":"
            # All of this logic is just to make the display of arrays prettier
            if use_marker:
                line_prefix = " " if last_was_list else marker + prefix[2:]
                line_suffix = "" if node == LIST_MARKER else RESET_NEWLINE
            else:
                line_prefix = prefix
                line_suffix = RESET_NEWLINE
            diff_ctx.iostream.write(line_prefix + node + line_suffix)
            last_was_list = node == LIST_MARKER
        prefix += "  "
    diff_ctx.print_tree[node_list] = True
    return last_was_list

def print_in_tree(diff_ctx, node_list, thing, other, use_marker=False,
                  last_was_list=False, ignore_lwl=False):
    """Recursively print tree context and diff information about object."""
    last_was_list = print_tree_context(
                        diff_ctx, node_list, other, use_marker, last_was_list)
    # If tree element is list, recursively print list contents
    if isinstance(thing, list):
        for i, subthing in enumerate(thing):
            key = ArrayNode("{}_{}".format(node_list[-1], i))
            last_was_list = print_in_tree(
                diff_ctx, node_list+[key], subthing, other, use_marker=True,
                last_was_list=last_was_list, ignore_lwl=ignore_lwl)
    # If tree element is dictionary, recursively print dictionary contents
    elif isinstance(thing, dict):
        for key in sorted(thing.keys()):
            last_was_list = print_in_tree(
                diff_ctx, node_list+[key], thing[key], other, use_marker=True,
                last_was_list=last_was_list, ignore_lwl=ignore_lwl)
    # Print difference between leaf objects (no need to recurse further)
    else:
        use_marker = not last_was_list or ignore_lwl
        marker = THAT_MARKER if other else THIS_MARKER
        prefix = marker + "  " * len(node_list) if use_marker else " "
        diff_ctx.iostream.write(prefix + str(thing) + RESET_NEWLINE)
        last_was_list = False
    return last_was_list

def compare_objects(diff_ctx, obj0, obj1, keys=[]):
    """Displays diff of two objects if they are not equal"""
    if obj0 != obj1:
        print_in_tree(diff_ctx, keys, obj0, False, ignore_lwl=True)
        print_in_tree(diff_ctx, keys, obj1, True, ignore_lwl=True)

def print_dict_diff(diff_ctx, tree, node_list, keys, other):
    """Recursively traverses dictionary object and displays differences"""
    for key in keys:
        if diff_ctx.minimal:
            nodes = node_list
            key = key
        else:
            nodes = node_list+[key]
            key = tree[key]
        use_marker = not diff_ctx.minimal
        print_in_tree(diff_ctx, nodes, key, other, use_marker=use_marker)

def compare_ndarrays(diff_ctx, array0, array1, keys):
    """Compares two ndarray objects"""
    ignore_keys = set(['source', 'data'])
    compare_dicts(diff_ctx, array0, array1, keys, ignore_keys)

    differences = []
    for field in ['shape', 'datatype']:
        if array0[field] != array1[field]:
            differences.append(field)

    array0 = NDArrayType.from_tree(array0, diff_ctx.asdf0)
    array1 = NDArrayType.from_tree(array1, diff_ctx.asdf1)
    if not array_equal(array0, array1):
        differences.append('contents')

    if differences:
        prefix = "  " * (len(keys) + 1)
        msg = "ndarrays differ by {}".format(human_list(differences))
        diff_ctx.iostream.write(prefix + RED + msg + RESET_NEWLINE)

def both_are_ndarrays(tree0, tree1):
    """Returns True if both inputs correspond to ndarrays, False otherwise"""
    if not (isinstance(tree0, Tagged) and isinstance(tree1, Tagged)):
        return False
    if not (NDARRAY_TAG in tree0._tag and NDARRAY_TAG in tree1._tag):
        return False
    return True

def compare_dicts(diff_ctx, dict0, dict1, keys, ignores=set()):
    """Recursively compares two dictionary objects"""
    keys0 = set(dict0.keys()) - ignores
    keys1 = set(dict1.keys()) - ignores
    # Recurse into subtree elements that are shared by both trees
    for key in sorted(keys0 & keys1):
        obj0 = dict0[key]
        obj1 = dict1[key]
        compare_trees(diff_ctx, obj0, obj1, keys=keys+[key])
    # Display subtree elements existing only in this tree
    print_dict_diff(diff_ctx, dict0, keys, sorted(keys0-keys1), False)
    # Display subtree elements existing only in that tree
    print_dict_diff(diff_ctx, dict1, keys, sorted(keys1-keys0), True)

def compare_trees(diff_ctx, tree0, tree1, keys=[]):
    """Recursively traverses two ASDF tree and compares them"""
    if both_are_ndarrays(tree0, tree1):
        compare_ndarrays(diff_ctx, tree0, tree1, keys)
    elif isinstance(tree0, dict) and isinstance(tree1, dict):
        compare_dicts(diff_ctx, tree0, tree1, keys)
    elif isinstance(tree0, list) and isinstance(tree1, list):
        for i, (obj0, obj1) in enumerate(zip(tree0, tree1)):
            key = ArrayNode("item_{}".format(i))
            compare_trees(diff_ctx, obj0, obj1, keys+[key])
    else:
        compare_objects(diff_ctx, tree0, tree1, keys)

def diff(filenames, minimal, iostream=sys.stdout):
    """Top-level implementation of diff algorithm"""
    try:
        with AsdfFile.open(filenames[0], _force_raw_types=True) as asdf0:
            with AsdfFile.open(filenames[1], _force_raw_types=True) as asdf1:
                diff_ctx = DiffContext(asdf0, asdf1, iostream, minimal=minimal)
                compare_trees(diff_ctx, asdf0.tree, asdf1.tree)
    except ValueError as error:
        raise RuntimeError(str(error))
