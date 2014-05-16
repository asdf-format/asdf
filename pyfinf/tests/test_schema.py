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

from .. import block
from .. import finf
from .. import schema
from .. import treeutil

from . import helpers


def test_violate_toplevel_schema():
    tree = {'fits': 'This does not look like a FITS file'}

    with pytest.raises(ValidationError):
        finf.FinfFile(tree)

    ff = finf.FinfFile()
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

    buff = helpers.yaml_to_finf(yaml)
    ff = finf.FinfFile.read(buff)

    assert isinstance(ff.tree['unit'], u.UnitBase)
    assert not isinstance(ff.tree['not_unit'], u.UnitBase)
    assert isinstance(ff.tree['not_unit'], six.text_type)

    assert ff.tree == {
        'unit': u.m,
        'not_unit': 'm'
        }


def test_validate_all_schema():
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
    # FINF standard document) are valid.

    def test_schema_examples(path):
        with open(path, 'rb') as fd:
            schema_tree = yaml.load(fd)

        def test_example(node):
            if (isinstance(node, dict) and
                'examples' in node and
                isinstance(node['examples'], list)):
                for desc, example in node['examples']:
                    buff = helpers.yaml_to_finf('example: ' + example.strip())
                    with finf.FinfFile() as ff:
                        # Add a dummy block so that the ndarray examples
                        # work
                        ff.blocks.add(block.Block(np.empty((1024))))
                        print(len(ff.blocks))
                        ff.read(buff)

        treeutil.walk(schema_tree, test_example)

    src = os.path.join(os.path.dirname(__file__), '../schemas')
    for root, dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith('.yaml'):
                continue
            yield test_schema_examples, os.path.join(root, fname)
