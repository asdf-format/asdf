# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True

from jsonschema import ValidationError

import numpy as np

import pytest

import six

import yaml

from .. import asdf
from .. import asdftypes
from .. import block
from .. import resolver
from .. import schema
from .. import treeutil
from .. import util

from . import helpers


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


class CustomExtension:
    @property
    def types(self):
        return []

    @property
    def tag_mapping(self):
        return [('tag:nowhere.org:custom',
                 'http://nowhere.org/schemas/custom{tag_suffix}')]

    @property
    def url_mapping(self):
        return [('http://nowhere.org/schemas/custom/',
                 util.filepath_to_url(TEST_DATA_PATH) +
                 '/{url_suffix}.yaml')]


def test_violate_toplevel_schema():
    tree = {'fits': 'This does not look like a FITS file'}

    with pytest.raises(ValidationError):
        asdf.AsdfFile(tree)

    ff = asdf.AsdfFile()
    ff.tree['fits'] = 'This does not look like a FITS file'
    with pytest.raises(ValidationError):
        buff = io.BytesIO()
        ff.write_to(buff)


@pytest.mark.skipif('not HAS_ASTROPY')
def test_tagging_scalars():
    yaml = """
unit: !unit/unit-1.0.0
  m
not_unit:
  m
    """
    from astropy import units as u

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff) as ff:
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
        schema_tree = schema.load_schema(path, resolve_references=True)

        schema.check_schema(schema_tree)

    src = os.path.join(os.path.dirname(__file__), '../schemas')
    for root, dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith('.yaml'):
                continue
            if os.path.splitext(fname)[0] in (
                    'draft-01', 'asdf-schema-1.0.0'):
                continue
            yield validate_schema, os.path.join(root, fname)


def test_all_schema_examples():
    # Make sure that the examples in the schema files (and thus the
    # ASDF standard document) are valid.

    def test_example(args):
        fname, example = args
        buff = helpers.yaml_to_asdf('example: ' + example.strip())
        ff = asdf.AsdfFile(uri=util.filepath_to_url(os.path.abspath(fname)))

        # Fake an external file
        ff2 = asdf.AsdfFile({'data': np.empty((1024*1024*8), dtype=np.uint8)})
        ff._external_asdf_by_uri[
            util.filepath_to_url(
                os.path.abspath(
                    os.path.join(os.path.dirname(fname), 'external.asdf')))] = ff2

        # Add some dummy blocks so that the ndarray examples work
        for i in range(3):
            b = block.Block(np.empty((1024*1024*8), dtype=np.uint8))
            b._used = True
            ff.blocks.add(b)
        b._array_storage = "streamed"

        try:
            ff._open_impl(ff, buff)
        except:
            print("From file:", fname)
            raise

        # Just test we can write it out.  A roundtrip test
        # wouldn't always yield the correct result, so those have
        # to be covered by "real" unit tests.
        if b'external.asdf' not in buff.getvalue():
            buff = io.BytesIO()
            ff.write_to(buff)

    def find_examples_in_schema(path):
        with open(path, 'rb') as fd:
            schema_tree = yaml.load(fd)

        examples = []

        for node in treeutil.iter_tree(schema_tree):
            if (isinstance(node, dict) and
                'examples' in node and
                isinstance(node['examples'], list)):
                for desc, example in node['examples']:
                    examples.append(example)

        return examples

    tree = {
        'data': np.empty((1024*1024*8), dtype=np.uint8)
    }
    external = asdf.AsdfFile(tree)

    src = os.path.join(os.path.dirname(__file__), '../schemas')
    for root, dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith('.yaml'):
                continue
            path = os.path.join(root, fname)
            for example in find_examples_in_schema(path):
                yield test_example, (path, example)


def test_schema_caching():
    # Make sure that if we request the same URL, we get the *exact
    # same* object, to ensure the cache is working.
    s1 = schema.load_schema(
        'http://stsci.edu/schemas/asdf/core/asdf-1.0.0')
    s2 = schema.load_schema(
        'http://stsci.edu/schemas/asdf/core/asdf-1.0.0')
    assert s1 is s2


def test_flow_style():
    class CustomFlowStyleType(dict, asdftypes.AsdfType):
        name = 'custom_flow'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

    class CustomFlowStyleExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowStyleType]

    tree = {
        'custom_flow': CustomFlowStyleType({'a': 42, 'b': 43})
    }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, extensions=CustomFlowStyleExtension())
    ff.write_to(buff)

    assert b'  a: 42\n  b: 43' in buff.getvalue()


def test_style():
    class CustomStyleType(str, asdftypes.AsdfType):
        name = 'custom_style'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

    class CustomStyleExtension(CustomExtension):
        @property
        def types(self):
            return [CustomStyleType]

    tree = {
        'custom_style': CustomStyleType("short")
    }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, extensions=CustomStyleExtension())
    ff.write_to(buff)

    assert b'|-\n  short\n' in buff.getvalue()


def test_property_order():
    tree = {'foo': np.ndarray([1, 2, 3])}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    ndarray_schema = schema.load_schema(
        'http://stsci.edu/schemas/asdf/core/ndarray-1.0.0')
    property_order = ndarray_schema['anyOf'][1]['propertyOrder']

    last_index = 0
    for prop in property_order:
        index = buff.getvalue().find(prop.encode('utf-8') + b':')
        if index != -1:
            assert index > last_index
            last_index = index


def test_invalid_nested():
    class CustomType(str, asdftypes.AsdfType):
        name = 'custom_type'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

    class CustomTypeExtension(CustomExtension):
        @property
        def types(self):
            return [CustomType]

    yaml = """
custom: !<tag:nowhere.org:custom/custom-1.0.0>
  foo
    """
    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff):
        pass

    buff.seek(0)
    with pytest.raises(ValidationError):
        with asdf.AsdfFile.open(buff, extensions=[CustomTypeExtension()]):
            pass

    # Make sure tags get validated inside of other tags that know
    # nothing about them.
    yaml = """
array: !core/ndarray-1.0.0
  data: [0, 1, 2]
  custom: !<tag:nowhere.org:custom/custom-1.0.0>
    foo
    """
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.raises(ValidationError):
        with asdf.AsdfFile.open(buff, extensions=[CustomTypeExtension()]):
            pass


def test_invalid_schema():
    s = {'type': 'integer'}
    schema.check_schema(s)

    s = {'type': 'foobar'}
    with pytest.raises(ValidationError):
        schema.check_schema(s)


def test_defaults():
    s = {
        'type': 'object',
        'properties': {
            'a': {
                'type': 'integer',
                'default': 42
            }
        }
    }

    t = {}

    cls = schema._create_validator(schema.FILL_DEFAULTS)
    validator = cls(s)
    validator.validate(t, _schema=s)

    assert t['a'] == 42

    cls = schema._create_validator(schema.REMOVE_DEFAULTS)
    validator = cls(s)
    validator.validate(t, _schema=s)

    assert t == {}


def test_default_check_in_schema():
    s = {
        'type': 'object',
        'properties': {
            'a': {
                'type': 'integer',
                'default': 'foo'
            }
        }
    }

    with pytest.raises(ValidationError):
        schema.check_schema(s)


def test_fill_and_remove_defaults():
    class DefaultType(dict, asdftypes.AsdfType):
        name = 'default'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [DefaultType]

    yaml = """
custom: !<tag:nowhere.org:custom/default-1.0.0>
  b: {}
    """
    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff, extensions=[DefaultTypeExtension()]) as ff:
        assert 'a' in ff.tree['custom']
        assert ff.tree['custom']['a'] == 42
        assert ff.tree['custom']['b']['c'] == 82

    buff.seek(0)
    with asdf.AsdfFile.open(buff, extensions=[DefaultTypeExtension()],
                            do_not_fill_defaults=True) as ff:
        assert 'a' not in ff.tree['custom']
        assert 'c' not in ff.tree['custom']['b']
        ff.fill_defaults()
        assert 'a' in ff.tree['custom']
        assert ff.tree['custom']['a'] == 42
        assert 'c' in ff.tree['custom']['b']
        assert ff.tree['custom']['b']['c'] == 82
        ff.remove_defaults()
        assert 'a' not in ff.tree['custom']
        assert 'c' not in ff.tree['custom']['b']


def test_references_in_schema():
    r = resolver.Resolver(CustomExtension().url_mapping, 'url')
    s = schema.load_schema(
        os.path.join(TEST_DATA_PATH, 'self_referencing-1.0.0.yaml'),
        resolver=r,
        resolve_references=True)
    assert '$ref' not in repr(s)
    assert s['anyOf'][1] == s['anyOf'][0]


def test_large_literals():
    tree = {
        'large_int': (1 << 53),
    }

    with pytest.raises(ValidationError):
        asdf.AsdfFile(tree)

    tree = {
        'large_array': np.array([(1 << 53)], np.uint64)
    }

    ff = asdf.AsdfFile(tree)
    buff = io.BytesIO()
    ff.write_to(buff)

    ff.set_array_storage(ff.tree['large_array'], 'inline')
    buff = io.BytesIO()
    with pytest.raises(ValidationError):
        ff.write_to(buff)
        print(buff.getvalue())


@pytest.mark.skipif('not HAS_ASTROPY')
def test_type_missing_dependencies():
    from astropy.tests.helper import catch_warnings

    class MissingType(asdftypes.AsdfType):
        name = 'missing'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = ['asdfghjkl12345.foo']
        requires = ["ASDFGHJKL12345"]

    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [MissingType]

    yaml = """
custom: !<tag:nowhere.org:custom/missing-1.0.0>
  b: {foo: 42}
    """
    buff = helpers.yaml_to_asdf(yaml)
    with catch_warnings() as w:
        with asdf.AsdfFile.open(buff, extensions=[DefaultTypeExtension()]) as ff:
            assert ff.tree['custom']['b']['foo'] == 42

    assert len(w) == 1


def test_assert_roundtrip_with_extension(tmpdir):
    called_custom_assert_equal = [False]

    class CustomType(dict, asdftypes.AsdfType):
        name = 'custom_flow'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

        @classmethod
        def assert_equal(cls, old, new):
            called_custom_assert_equal[0] = True

    class CustomTypeExtension(CustomExtension):
        @property
        def types(self):
            return [CustomType]

    tree = {
        'custom': CustomType({'a': 42, 'b': 43})
    }

    def check(ff):
        assert isinstance(ff.tree['custom'], CustomType)

    helpers.assert_roundtrip_tree(tree, tmpdir, extensions=[CustomTypeExtension()])

    assert called_custom_assert_equal[0] is True
