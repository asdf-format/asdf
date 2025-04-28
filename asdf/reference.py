"""
Manages external references in the YAML tree using the `JSON Reference
standard <http://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__
and `JSON Pointer standard <http://tools.ietf.org/html/rfc6901>`__.
"""

import weakref
from collections.abc import Sequence
from contextlib import suppress

import numpy as np

from . import generic_io, treeutil, util
from .util import _patched_urllib_parse

__all__ = ["Reference", "find_references", "make_reference", "resolve_fragment", "resolve_references"]


def resolve_fragment(tree, pointer):
    """
    Resolve a JSON Pointer within the tree.
    """
    pointer = pointer.lstrip("/")
    parts = _patched_urllib_parse.unquote(pointer).split("/") if pointer else []

    for part in parts:
        part_ = part.replace("~1", "/").replace("~0", "~")

        if isinstance(tree, Sequence):
            # Array indexes should be turned into integers
            with suppress(ValueError):
                part_ = int(part_)

        try:
            tree = tree[part_]

        except (TypeError, LookupError) as err:
            msg = f"Unresolvable reference: '{pointer}'"
            raise ValueError(msg) from err

    return tree


class Reference:
    def __init__(self, uri, base_uri=None, asdffile=None, target=None):
        self._uri = uri
        if asdffile is not None:
            self._asdffile = weakref.ref(asdffile)
        self._base_uri = base_uri
        self._target = target

    def _get_target(self, **kwargs):
        if self._target is None:
            base_uri = self._base_uri
            if base_uri is None:
                base_uri = self._asdffile().uri
            uri = generic_io.resolve_uri(base_uri, self._uri)
            asdffile = self._asdffile().open_external(uri, **kwargs)
            parts = _patched_urllib_parse.urlparse(self._uri)
            fragment = parts.fragment
            self._target = resolve_fragment(asdffile.tree, fragment)
        return self._target

    def __repr__(self):
        # repr alone should not force loading of the reference
        if self._target is None:
            return f"<Reference (unloaded) to '{self._uri}'>"

        return f"<Reference to {self._target!r}>"

    def __str__(self):
        # str alone should not force loading of the reference
        if self._target is None:
            return f"<Reference (unloaded) to '{self._uri}'>"

        return str(self._target)

    def __len__(self):
        return len(self._get_target())

    def __getattr__(self, attr):
        if attr == "_tag":
            return None
        try:
            return getattr(self._get_target(), attr)
        except Exception as err:
            msg = f"No attribute '{attr}'"
            raise AttributeError(msg) from err

    def __getitem__(self, item):
        return self._get_target()[item]

    def __setitem__(self, item, val):
        self._get_target()[item] = val

    def __array__(self):
        return np.asarray(self._get_target())

    def __call__(self, **kwargs):
        return self._get_target(**kwargs)

    def __contains__(self, item):
        return item in self._get_target()


def find_references(tree, ctx):
    """
    Find all of the JSON references in the tree, and convert them into
    `Reference` objects.
    """

    def do_find(tree):
        if isinstance(tree, dict) and "$ref" in tree:
            return Reference(tree["$ref"], asdffile=ctx)
        return tree

    return treeutil.walk_and_modify(tree, do_find)


def resolve_references(tree, ctx, **kwargs):
    """
    Resolve all of the references in the tree, by loading the external
    data and inserting it directly into the tree.
    """

    def do_resolve(tree):
        if isinstance(tree, Reference):
            return tree(**kwargs)
        return tree

    tree = find_references(tree, ctx)

    return treeutil.walk_and_modify(tree, do_resolve)


def make_reference(asdffile, path):
    """
    Make a reference to a subtree of the given ASDF file.

    Parameters
    ----------
    asdffile : AsdfFile

    path : list of str and int, optional
        The parts of the path pointing to an item in this tree.
        If omitted, points to the root of the tree.

    Returns
    -------
    reference : reference.Reference
        A reference object.
    """
    path_str = "/".join(x.replace("~", "~0").replace("/", "~1") for x in path)
    target = resolve_fragment(asdffile.tree, path_str)

    if asdffile.uri is None:
        msg = "Can not make a reference to a AsdfFile without an associated URI."
        raise ValueError(msg)
    base_uri = util.get_base_uri(asdffile.uri)
    uri = base_uri + "#" + path_str
    return Reference(uri, target=target)
