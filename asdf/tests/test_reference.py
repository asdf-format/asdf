# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io
import os

import numpy as np
from numpy.testing import assert_array_equal

import pytest

import asdf
from asdf import reference
from asdf import util
from asdf.tags.core import ndarray

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
    external_path = os.path.join(str(tmpdir), 'external.asdf')
    ext = asdf.AsdfFile(exttree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ext.write_to(external_path, all_array_storage='internal')

    external_path = os.path.join(str(tmpdir), 'external2.asdf')
    ff = asdf.AsdfFile(exttree)
    ff.write_to(external_path, all_array_storage='internal')

    tree = {
        # The special name "data" here must be an array.  This is
        # included so that such validation can be ignored when we just
        # have a "$ref".
        'data': {
            '$ref': 'external.asdf#/cool_stuff/a'
            },
        'science_data': {
            '$ref': 'external.asdf#/cool_stuff/a'
            },
        'science_data2': {
            '$ref': 'external2.asdf#/cool_stuff/a'
            },
        'foobar': {
            '$ref': 'external.asdf#/list_of_stuff/0',
            },
        'answer': {
            '$ref': 'external.asdf#/list_of_stuff/1'
            },
        'array': {
            '$ref': 'external.asdf#/list_of_stuff/2',
            },
        'whole_thing': {
            '$ref': 'external.asdf#'
            },
        'myself': {
            '$ref': '#',
            },
        'internal': {
            '$ref': '#science_data'
            }
        }

    def do_asserts(ff):
        assert 'unloaded' in repr(ff.tree['science_data'])
        assert 'unloaded' in str(ff.tree['science_data'])
        assert len(ff._external_asdf_by_uri) == 0

        assert_array_equal(ff.tree['science_data'], exttree['cool_stuff']['a'])
        assert len(ff._external_asdf_by_uri) == 1
        with pytest.raises((ValueError, RuntimeError)):
            # Assignment destination is readonly
            ff.tree['science_data'][0] = 42

        assert_array_equal(ff.tree['science_data2'], exttree['cool_stuff']['a'])
        assert len(ff._external_asdf_by_uri) == 2

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
        assert len(ff._external_asdf_by_uri) == 2

        assert_array_equal(ff.tree['internal'], exttree['cool_stuff']['a'])

    with asdf.AsdfFile(tree, uri=util.filepath_to_url(
            os.path.join(str(tmpdir), 'main.asdf'))) as ff:
        do_asserts(ff)

        internal_path = os.path.join(str(tmpdir), 'main.asdf')
        ff.write_to(internal_path)

    with asdf.open(internal_path) as ff:
        do_asserts(ff)

    with asdf.open(internal_path) as ff:
        assert len(ff._external_asdf_by_uri) == 0
        ff.resolve_references()
        assert len(ff._external_asdf_by_uri) == 2

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


@pytest.mark.remote_data
def test_external_reference_invalid(tmpdir):
    tree = {
        'foo': {
            '$ref': 'fail.asdf'
            }
        }

    ff = asdf.AsdfFile(tree)
    with pytest.raises(ValueError):
        ff.resolve_references()

    ff = asdf.AsdfFile(tree, uri="http://httpstat.us/404")
    with pytest.raises(IOError):
        ff.resolve_references()

    ff = asdf.AsdfFile(tree, uri=util.filepath_to_url(
        os.path.join(str(tmpdir), 'main.asdf')))
    with pytest.raises(IOError):
        ff.resolve_references()


def test_external_reference_invalid_fragment(tmpdir):
    exttree = {
        'list_of_stuff': [
            'foobar',
            42,
            np.array([7, 8, 9], np.float)
            ]
        }
    external_path = os.path.join(str(tmpdir), 'external.asdf')
    ff = asdf.AsdfFile(exttree)
    ff.write_to(external_path)

    tree = {
        'foo': {
            '$ref': 'external.asdf#/list_of_stuff/a'
            }
        }

    with asdf.AsdfFile(tree, uri=util.filepath_to_url(
            os.path.join(str(tmpdir), 'main.asdf'))) as ff:
        with pytest.raises(ValueError):
            ff.resolve_references()

    tree = {
        'foo': {
            '$ref': 'external.asdf#/list_of_stuff/3'
            }
        }

    with asdf.AsdfFile(tree, uri=util.filepath_to_url(
            os.path.join(str(tmpdir), 'main.asdf'))) as ff:
        with pytest.raises(ValueError):
            ff.resolve_references()


def test_make_reference(tmpdir):
    exttree = {
        # Include some ~ and / in the name to make sure that escaping
        # is working correctly
        'f~o~o/': {
            'a': np.array([0, 1, 2], np.float),
            'b': np.array([3, 4, 5], np.float)
            }
        }
    external_path = os.path.join(str(tmpdir), 'external.asdf')
    ext = asdf.AsdfFile(exttree)
    ext.write_to(external_path)

    with asdf.open(external_path) as ext:
        ff = asdf.AsdfFile()
        ff.tree['ref'] = ext.make_reference(['f~o~o/', 'a'])
        assert_array_equal(ff.tree['ref'], ext.tree['f~o~o/']['a'])

        ff.write_to(os.path.join(str(tmpdir), 'source.asdf'))

    with asdf.open(os.path.join(str(tmpdir), 'source.asdf')) as ff:
        assert ff.tree['ref']._uri == 'external.asdf#f~0o~0o~1/a'


def test_internal_reference(tmpdir):
    testfile = os.path.join(str(tmpdir), 'test.asdf')

    tree = {
        'foo': 2,
        'bar': {'$ref': '#'}
    }

    ff = asdf.AsdfFile(tree)
    ff.find_references()
    assert isinstance(ff.tree['bar'], reference.Reference)
    ff.resolve_references()
    assert ff.tree['bar']['foo'] == 2

    tree = {
        'foo': 2
    }
    ff = asdf.AsdfFile(
        tree, uri=util.filepath_to_url(os.path.abspath(testfile)))
    ff.tree['bar'] = ff.make_reference([])
    buff = io.BytesIO()
    ff.write_to(buff)
    buff.seek(0)
    ff = asdf.AsdfFile()
    content = asdf.AsdfFile()._open_impl(ff, buff, _get_yaml_content=True)
    assert b"{$ref: ''}" in content


def test_implicit_internal_reference(tmpdir):
    target = {"foo": "bar"}
    nested_in_dict = {"target": target}
    nested_in_list = [target]
    tree = {"target": target, "nested_in_dict": nested_in_dict, "nested_in_list": nested_in_list}

    assert tree["target"] is tree["nested_in_dict"]["target"]
    assert tree["target"] is tree["nested_in_list"][0]

    af = asdf.AsdfFile(tree)

    assert af["target"] is af["nested_in_dict"]["target"]
    assert af["target"] is af["nested_in_list"][0]

    output_path = os.path.join(str(tmpdir), "test.asdf")
    af.write_to(output_path)
    with asdf.open(output_path) as af:
        assert af["target"] is af["nested_in_dict"]["target"]
        assert af["target"] is af["nested_in_list"][0]
