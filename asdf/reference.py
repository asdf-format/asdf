# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Manages external references in the YAML tree using the `JSON Reference
standard <http://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__
and `JSON Pointer standard <http://tools.ietf.org/html/rfc6901>`__.
"""


from collections.abc import Sequence
import weakref

import numpy as np

from urllib import parse as urlparse

from .types import AsdfType
from . import generic_io
from . import treeutil
from . import util

__all__ = [
    'resolve_fragment', 'Reference', 'find_references', 'resolve_references',
    'make_reference']


def resolve_fragment(tree, pointer):
    """
    Resolve a JSON Pointer within the tree.
    """
    pointer = pointer.lstrip(u"/")
    parts = urlparse.unquote(pointer).split(u"/") if pointer else []

    for part in parts:
        part = part.replace(u"~1", u"/").replace(u"~0", u"~")

        if isinstance(tree, Sequence):
            # Array indexes should be turned into integers
            try:
                part = int(part)
            except ValueError:
                pass
        try:
            tree = tree[part]
        except (TypeError, LookupError):
            raise ValueError(
                "Unresolvable reference: '{0}'".format(pointer))

    return tree


class Reference(AsdfType):
    yaml_tag = 'tag:yaml.org,2002:map'

    def __init__(self, uri, base_uri=None, asdffile=None, target=None):
        self._uri = uri
        if asdffile is not None:
            self._asdffile = weakref.ref(asdffile)
        self._base_uri = base_uri
        self._target = target

    def _get_target(self, do_not_fill_defaults=False):
        if self._target is None:
            base_uri = self._base_uri
            if base_uri is None:
                base_uri = self._asdffile().uri
            uri = generic_io.resolve_uri(base_uri, self._uri)
            asdffile = self._asdffile().open_external(
                uri, do_not_fill_defaults=do_not_fill_defaults)
            parts = urlparse.urlparse(self._uri)
            fragment = parts.fragment
            self._target = resolve_fragment(asdffile.tree, fragment)
        return self._target

    def __repr__(self):
        # repr alone should not force loading of the reference
        if self._target is None:
            return "<Reference (unloaded) to '{0}'>".format(
                self._uri)
        else:
            return "<Reference to {0}>".format(repr(self._target))

    def __str__(self):
        # str alone should not force loading of the reference
        if self._target is None:
            return "<Reference (unloaded) to '{0}'>".format(
                self._uri)
        else:
            return str(self._target)

    def __len__(self):
        return len(self._get_target())

    def __getattr__(self, attr):
        if attr == '_tag':
            return None
        try:
            return getattr(self._get_target(), attr)
        except Exception:
            raise AttributeError("No attribute '{0}'".format(attr))

    def __getitem__(self, item):
        return self._get_target()[item]

    def __setitem__(self, item, val):
        self._get_target()[item] = val

    def __array__(self):
        return np.asarray(self._get_target())

    def __call__(self, do_not_fill_defaults=False):
        return self._get_target(do_not_fill_defaults=do_not_fill_defaults)

    def __contains__(self, item):
        return item in self._get_target()

    @classmethod
    def to_tree(self, data, ctx):
        if ctx.uri is not None:
            uri = generic_io.relative_uri(ctx.uri, data._uri)
        else:
            uri = data._uri
        return {'$ref': uri}

    @classmethod
    def validate(self, data):
        pass


def find_references(tree, ctx):
    """
    Find all of the JSON references in the tree, and convert them into
    `Reference` objects.
    """
    def do_find(tree, json_id):
        if isinstance(tree, dict) and '$ref' in tree:
            return Reference(tree['$ref'], json_id, asdffile=ctx)
        return tree

    return treeutil.walk_and_modify(
        tree, do_find, ignore_implicit_conversion=ctx._ignore_implicit_conversion)


def resolve_references(tree, ctx, do_not_fill_defaults=False):
    """
    Resolve all of the references in the tree, by loading the external
    data and inserting it directly into the tree.
    """
    def do_resolve(tree):
        if isinstance(tree, Reference):
            return tree(do_not_fill_defaults=do_not_fill_defaults)
        return tree

    tree = find_references(tree, ctx)

    return treeutil.walk_and_modify(
        tree, do_resolve, ignore_implicit_conversion=ctx._ignore_implicit_conversion)


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
    path_str = '/'.join(
        x.replace(u"~", u"~0").replace(u"/", u"~1")
        for x in path)
    target = resolve_fragment(asdffile.tree, path_str)

    if asdffile.uri is None:
        raise ValueError(
            "Can not make a reference to a AsdfFile without an associated URI.")
    base_uri = util.get_base_uri(asdffile.uri)
    uri = base_uri + '#' + path_str
    return Reference(uri, target=target)
