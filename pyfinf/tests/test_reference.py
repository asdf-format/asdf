# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os

import numpy as np
from numpy.testing import assert_array_equal

from .. import finf
from ..tags import ndarray

from .helpers import assert_tree_match


def test_external_reference(tmpdir):
    exttree = {
        'cool_stuff': {
            'a': np.array([0, 1, 2], np.float),
            'b': np.array([3, 4, 5], np.float)
            },
        'list_of_stuff': [
            'foobar',
            42,
            np.array([7, 8, 9], np.float)
            ]
        }
    external_path = os.path.join(str(tmpdir), 'external.finf')
    with finf.FinfFile(exttree) as ff:
        ff.write_to(external_path)
    external_path = os.path.join(str(tmpdir), 'external2.finf')
    with finf.FinfFile(exttree) as ff:
        ff.write_to(external_path)

    tree = {
        # The special name "data" here must be an array.  This is
        # included so that such validation can be ignored when we just
        # have a "$ref".
        'data': {
            '$ref': 'external.finf#/cool_stuff/a'
            },
        'science_data': {
            '$ref': 'external.finf#/cool_stuff/a'
            },
        'science_data2': {
            '$ref': 'external2.finf#/cool_stuff/a'
            },
        'foobar': {
            '$ref': 'external.finf#/list_of_stuff/0',
            },
        'answer': {
            '$ref': 'external.finf#/list_of_stuff/1'
            },
        'array': {
            '$ref': 'external.finf#/list_of_stuff/2',
            },
        'whole_thing': {
            '$ref': 'external.finf#'
            },
        'myself': {
            '$ref': '#',
            },
        'internal': {
            '$ref': '#science_data'
            }
        }

    def do_asserts(ff):
        assert len(ff._external_finf_by_uri) == 0

        assert_array_equal(ff.tree['science_data'], exttree['cool_stuff']['a'])
        assert len(ff._external_finf_by_uri) == 1

        assert_array_equal(ff.tree['science_data2'], exttree['cool_stuff']['a'])
        assert len(ff._external_finf_by_uri) == 2

        assert ff.tree['foobar']() == 'foobar'
        assert ff.tree['answer']() == 42
        assert_array_equal(ff.tree['array'], exttree['list_of_stuff'][2])

        assert_tree_match(ff.tree['whole_thing'](), exttree)

        assert_array_equal(
            ff.tree['whole_thing']['cool_stuff']['a'],
            exttree['cool_stuff']['a'])

        assert_array_equal(
            ff.tree['myself']['science_data'],
            exttree['cool_stuff']['a'])
        # Make sure that referencing oneself doesn't make another call
        # to disk.
        assert len(ff._external_finf_by_uri) == 2

        assert_array_equal(ff.tree['internal'], exttree['cool_stuff']['a'])

    with finf.FinfFile(tree, uri=os.path.join(str(tmpdir), 'main.finf')) as ff:
        do_asserts(ff)

        internal_path = os.path.join(str(tmpdir), 'main.finf')
        ff.write_to(internal_path)

    with finf.FinfFile.read(internal_path) as ff:
        do_asserts(ff)

    with finf.FinfFile.read(internal_path) as ff:
        assert len(ff._external_finf_by_uri) == 0
        ff.resolve_references()
        assert len(ff._external_finf_by_uri) == 2

        assert isinstance(ff.tree['data'], ndarray.NDArrayType)
        assert isinstance(ff.tree['science_data'], ndarray.NDArrayType)

        assert_array_equal(ff.tree['science_data'], exttree['cool_stuff']['a'])
        assert_array_equal(ff.tree['science_data2'], exttree['cool_stuff']['a'])

        assert ff.tree['foobar'] == 'foobar'
        assert ff.tree['answer'] == 42
        assert_array_equal(ff.tree['array'], exttree['list_of_stuff'][2])

        assert_tree_match(ff.tree['whole_thing'], exttree)

        assert_array_equal(
            ff.tree['whole_thing']['cool_stuff']['a'],
            exttree['cool_stuff']['a'])

        assert_array_equal(
            ff.tree['myself']['science_data'],
            exttree['cool_stuff']['a'])

        assert_array_equal(ff.tree['internal'], exttree['cool_stuff']['a'])
