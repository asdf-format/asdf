# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
Manages external references in the YAML tree using the `JSON Reference
standard <http://tools.ietf.org/html/draft-pbryan-zyp-json-ref-03>`__
and `JSON Pointer standard <http://tools.ietf.org/html/rfc6901>`__.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

from collections import Sequence
import weakref

import numpy as np

from astropy.extern.six.moves.urllib import parse as urlparse

from .finftypes import FinfType
from . import tagged


__all__ = [
    'resolve_fragment', 'Reference', 'find_references', 'resolve_references']


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


class Reference(FinfType):
    yaml_tag = 'tag:yaml.org,2002:map'

    def __init__(self, finffile, uri, scope):
        self._finffile = weakref.ref(finffile)
        self._uri = uri
        self._scope = scope
        self._target = None

    def _get_target(self):
        if self._target is None:
            finffile = self._finffile().read_external(self._uri)
            parts = urlparse.urlparse(self._uri)
            fragment = parts.fragment
            self._target = resolve_fragment(finffile.tree, fragment)
        return self._target

    def __repr__(self):
        # repr alone should not force loading of the data
        if self._target is None:
            return "<Reference (unloaded) to '{0}'>".format(
                self._uri)
        else:
            return "<Reference to {0}>".format(repr(self._target))

    def __str__(self):
        # str alone should not force loading of the data
        if self._target is None:
            return "<Reference (unloaded) to '{0}'>".format(
                self._uri)
        else:
            return str(self._target)

    def __len__(self):
        return len(self._get_target())

    def __getattr__(self, attr):
        return getattr(self._get_target(), attr)

    def __getitem__(self, item):
        return self._get_target()[item]

    def __setitem__(self, item, val):
        self._get_target()[item] = val

    def __array__(self):
        return np.asarray(self._get_target())

    def __call__(self):
        return self._get_target()

    @classmethod
    def to_tree(self, data, ctx):
        return {'$ref': data._uri}

    @classmethod
    def validate(self, data):
        pass


def find_references(tree, ctx):
    """
    Find all of the JSON references in the tree, and convert them into
    `Reference` objects.
    """
    def do_find(tree):
        if isinstance(tree, dict) and '$ref' in tree:
            return Reference(ctx.finffile, tree['$ref'], None)
        return tree

    return tagged.walk_and_modify_with_tags(tree, do_find)


def resolve_references(tree, ctx):
    """
    Resolve all of the references in the tree, by loading the external
    data and inserting it directly into the tree.
    """
    def do_resolve(tree):
        if isinstance(tree, Reference):
            return tree()

        return tree

    tree = find_references(tree, ctx)

    return tagged.walk_and_modify_with_tags(tree, do_resolve)
