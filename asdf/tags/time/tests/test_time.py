# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import six
import pytest
import datetime
from collections import OrderedDict

astropy = pytest.importorskip('astropy')
from astropy import time

import numpy as np

from .... import asdf, AsdfFile
from .... import tagged
from .... import yamlutil
from .... import schema as asdf_schema
from ....tests import helpers


def _walk_schema(schema, callback, ctx={}):
    def recurse(schema, path, combiner, ctx):
        if callback(schema, path, combiner, ctx, recurse):
            return

        for c in ['allOf', 'not']:
            for sub in schema.get(c, []):
                recurse(sub, path, c, ctx)

        for c in ['anyOf', 'oneOf']:
            for i, sub in enumerate(schema.get(c, [])):
                recurse(sub, path + [i], c, ctx)

        if schema.get('type') == 'object':
            for key, val in six.iteritems(schema.get('properties', {})):
                recurse(val, path + [key], combiner, ctx)

        if schema.get('type') == 'array':
            items = schema.get('items', {})
            if isinstance(items, list):
                for i, item in enumerate(items):
                    recurse(item, path + [i], combiner, ctx)
            elif len(items):
                recurse(items, path + ['items'], combiner, ctx)

    recurse(schema, [], None, ctx)


def _flatten_combiners(schema):
    newschema = OrderedDict()

    def add_entry(path, schema, combiner):
        # TODO: Simplify?
        cursor = newschema
        for i in range(len(path)):
            part = path[i]
            if isinstance(part, int):
                cursor = cursor.setdefault('items', [])
                while len(cursor) <= part:
                    cursor.append({})
                cursor = cursor[part]
            elif part == 'items':
                cursor = cursor.setdefault('items', OrderedDict())
            else:
                cursor = cursor.setdefault('properties', OrderedDict())
                if i < len(path) - 1 and isinstance(path[i+1], int):
                    cursor = cursor.setdefault(part, [])
                else:
                    cursor = cursor.setdefault(part, OrderedDict())

        cursor.update(schema)

    def callback(schema, path, combiner, ctx, recurse):
        type = schema.get('type')
        schema = OrderedDict(schema)
        if type == 'object':
            del schema['properties']
        elif type == 'array':
            del schema['items']
        if 'allOf' in schema:
            del schema['allOf']
        if 'anyOf' in schema:
            del schema['anyOf']

        add_entry(path, schema, combiner)

    _walk_schema(schema, callback)

    return newschema


def test_time(tmpdir):
    time_array = time.Time(
        np.arange(100), format="unix")

    tree = {
        'large_time_array': time_array
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_time_with_location(tmpdir):
    # See https://github.com/spacetelescope/asdf/issues/341
    from astropy import units as u
    from astropy.coordinates.earth import EarthLocation

    location = EarthLocation(x=[1,2]*u.m, y=[3,4]*u.m, z=[5,6]*u.m)

    t = time.Time([1,2], location=location, format='cxcsec')

    tree = {'time': t}

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_isot(tmpdir):
    tree = {
        'time': time.Time('2000-01-01T00:00:00.000')
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)

    ff = asdf.AsdfFile(tree)
    tree = yamlutil.custom_tree_to_tagged_tree(ff.tree, ff)
    assert isinstance(tree['time'], six.text_type)


def test_time_tag():
    schema = asdf_schema.load_schema(
        'http://stsci.edu/schemas/asdf/time/time-1.1.0',
        resolve_references=True)
    schema = _flatten_combiners(schema)

    date = time.Time(datetime.datetime.now())
    tree = {'date': date}
    asdf = AsdfFile(tree=tree)
    instance = yamlutil.custom_tree_to_tagged_tree(tree['date'], asdf)

    asdf_schema.validate(instance, schema=schema)

    tag = 'tag:stsci.edu:asdf/time/time-1.1.0'
    date = tagged.tag_object(tag, date)
    tree = {'date': date}
    asdf = AsdfFile(tree=tree)
    instance = yamlutil.custom_tree_to_tagged_tree(tree['date'], asdf)

    asdf_schema.validate(instance, schema=schema)
