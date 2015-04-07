# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

import numpy as np

from astropy.extern import six
from astropy.tests.helper import pytest
from astropy import units as u

from jsonschema import ValidationError

import yaml

from .. import asdf
from .. import asdftypes
from .. import block
from .. import resolver
from .. import schema
from .. import treeutil

from . import helpers


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def test_violate_toplevel_schema():
    tree = {'fits': 'This does not look like a FITS file'}

    with pytest.raises(ValidationError):
        asdf.AsdfFile(tree)

    ff = asdf.AsdfFile()
    ff.tree['fits'] = 'This does not look like a FITS file'
    with pytest.raises(ValidationError):
        buff = io.BytesIO()
        ff.write_to(buff)


def test_tagging_scalars():
    yaml = """
unit: !unit/unit
  m
not_unit:
  m
    """

    buff = helpers.yaml_to_asdf(yaml)
    ff = asdf.AsdfFile.read(buff)

    assert isinstance(ff.tree['unit'], u.UnitBase)
    assert not isinstance(ff.tree['not_unit'], u.UnitBase)
    assert isinstance(ff.tree['not_unit'], six.text_type)

    assert ff.tree == {
        'unit': u.m,
        'not_unit': 'm'
        }


def test_validate_all_schema():
    # Make sure that the schemas themselves are valid.

    def validate_schema(path):
        with open(path, 'rb') as fd:
            schema_tree = yaml.load(fd)
        schema.check_schema(schema_tree)

    src = os.path.join(os.path.dirname(__file__), '../schemas')
    for root, dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith('.yaml'):
                continue
            yield validate_schema, os.path.join(root, fname)


def test_all_schema_examples():
    # Make sure that the examples in the schema files (and thus the
    # ASDF standard document) are valid.

    def test_example(args):
        fname, example = args
        buff = helpers.yaml_to_asdf('example: ' + example.strip())
        with asdf.AsdfFile() as ff:
            # Add a dummy block so that the ndarray examples
            # work
            ff.blocks.add(block.Block(np.empty((1024))))
            try:
                ff.read(buff)
            except:
                print("From file:", fname)
                raise

            # Just test we can write it out.  A roundtrip test
            # wouldn't always yield the correct result, so those have
            # to be covered by "real" unit tests.
            buff = io.BytesIO()
            ff.write_to(buff)

    def find_examples_in_schema(path):
        with open(path, 'rb') as fd:
            schema_tree = yaml.load(fd)

        examples = []

        def find_example(node):
            if (isinstance(node, dict) and
                'examples' in node and
                isinstance(node['examples'], list)):
                for desc, example in node['examples']:
                    examples.append(example)

        treeutil.walk(schema_tree, find_example)

        return examples

    src = os.path.join(os.path.dirname(__file__), '../schemas')
    for root, dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith('.yaml'):
                continue
            for example in find_examples_in_schema(
                    os.path.join(root, fname)):
                yield test_example, (fname, example)


def test_schema_caching():
    # Make sure that if we request the same URL, we get the *exact
    # same* object, to ensure the cache is working.
    s1 = schema.load_schema(
        'http://stsci.edu/schemas/asdf/0.1.0/core/asdf')
    s2 = schema.load_schema(
        'http://stsci.edu/schemas/asdf/0.1.0/core/asdf')
    assert s1 is s2


def test_flow_style():
    class CustomFlowStyleType(dict, asdftypes.AsdfType):
        name = 'custom_flow'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

    class CustomFlowStyleExtension:
        @property
        def types(self):
            return [CustomFlowStyleType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/1.0.0/',
                     'file://' + TEST_DATA_PATH + '/{url_suffix}.yaml')]

    tree = {
        'custom_flow': CustomFlowStyleType({'a': 42, 'b': 43})
    }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, extensions=CustomFlowStyleExtension())
    with ff.write_to(buff):
        pass

    assert b'  a: 42\n  b: 43' in buff.getvalue()


def test_style():
    class CustomStyleType(str, asdftypes.AsdfType):
        name = 'custom_style'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

    class CustomStyleExtension:
        @property
        def types(self):
            return [CustomStyleType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/1.0.0/',
                     'file://' + TEST_DATA_PATH + '/{url_suffix}.yaml')]

    tree = {
        'custom_style': CustomStyleType("short")
    }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, extensions=CustomStyleExtension())
    with ff.write_to(buff):
        pass

    assert b'|-\n  short\n' in buff.getvalue()


def test_property_order():
    tree = {'foo': np.ndarray([1, 2, 3])}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    with ff.write_to(buff):
        pass

    ndarray_schema = schema.load_schema(
        'http://stsci.edu/schemas/asdf/0.1.0/core/ndarray')
    property_order = ndarray_schema['anyOf'][1]['propertyOrder']

    last_index = 0
    for prop in property_order:
        index = buff.getvalue().find(prop.encode('utf-8') + b':')
        if index != -1:
            assert index > last_index
            last_index = index
