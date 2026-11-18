"""
References from an ASDF tree to content in the same or another ASDF file.

References are written in the tree as ``{$ref: <uri>}`` using the `JSON
Reference standard <http://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__,
where the URI's fragment is a `JSON Pointer
<http://tools.ietf.org/html/rfc6901>`__ into the target file's tree.
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
    """
    A lazily-resolved JSON Reference to a node in an ASDF tree.

    A ``Reference`` stands in for the node it points to.  The target is
    loaded the first time it is needed, opening the external file if
    necessary, and attribute access, indexing, ``len()``, ``in`` and
    conversion to a numpy array are all forwarded to it.  `repr` and `str`
    do not load the target.

    Calling the reference returns the target itself.  Any keyword
    arguments are passed to `asdf.AsdfFile.open_external` if the external
    file has not been loaded yet.

    When a tree containing a ``Reference`` is written, it is written as a
    ``{$ref: <uri>}`` node, with the URI made relative to the file being
    written where possible.

    References are usually not created directly; see
    `asdf.AsdfFile.make_reference` and `asdf.AsdfFile.find_references`.

    Parameters
    ----------
    uri : str
        The URI of the referenced node, possibly relative, with a JSON
        Pointer to the node as its fragment, e.g.
        ``"target.asdf#/data/0"``.
    base_uri : str, optional
        The URI to resolve a relative ``uri`` against.  Defaults to the URI
        of ``asdffile``.
    asdffile : asdf.AsdfFile, optional
        The file containing the reference, used to open external files.
        Only a weak reference to it is kept.
    target : object, optional
        The referenced node, if it is already known, in which case it is
        not loaded from ``uri``.
    """

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
        """
        Return the referenced node, loading it first if necessary.

        Parameters
        ----------
        **kwargs
            Passed to `asdf.AsdfFile.open_external` when the external file
            has not been loaded yet.
        """
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
    asdffile : asdf.AsdfFile

    path : list of str and int, optional
        The parts of the path pointing to an item in this tree.
        If omitted, points to the root of the tree.

    Returns
    -------
    reference : Reference
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
