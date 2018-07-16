# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import io
import os
import re
import warnings

from jsonschema import ValidationError

import yaml
import pytest

import numpy as np
from numpy.testing import assert_array_equal

import asdf
from asdf import asdftypes
from asdf import extension
from asdf import resolver
from asdf import schema
from asdf import util
from asdf import yamlutil

from asdf.tests import helpers


class CustomExtension:
    """
    This is the base class that is used for extensions for custom tag
    classes that exist only for the purposes of testing.
    """
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
                 util.filepath_to_url(helpers.get_test_data_path('')) +
                 '/{url_suffix}.yaml')]


class TagReferenceType(asdftypes.CustomType):
    """
    This class is used by several tests below for validating foreign type
    references in schemas and ASDF files.
    """
    name = 'tag_reference'
    organization = 'nowhere.org'
    version = (1, 0, 0)
    standard = 'custom'

    @classmethod
    def from_tree(cls, tree, ctx):
        node = {}
        node['name'] = tree['name']
        node['things'] = yamlutil.tagged_tree_to_custom_tree(tree['things'], ctx)
        return node


@pytest.mark.importorskip('astropy')
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
        assert isinstance(ff.tree['not_unit'], str)

        assert ff.tree == {
            'unit': u.m,
            'not_unit': 'm'
            }


def test_read_json_schema():
    """Pytest to make sure reading JSON schemas succeeds.

    This was known to fail on Python 3.5 See issue #314 at
    https://github.com/spacetelescope/asdf/issues/314 for more details.
    """
    json_schema = helpers.get_test_data_path('example_schema.json')
    schema_tree = schema.load_schema(json_schema, resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema(tmpdir):
    schema_def = """
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "../core/ndarray-1.0.0"

required: [foobar]
...
    """
    schema_path = tmpdir.join('nugatory.yaml')
    schema_path.write(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_full_tag(tmpdir):
    schema_def = """
%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "tag:stsci.edu:asdf/core/ndarray-1.0.0"

required: [foobar]
...
    """
    schema_path = tmpdir.join('nugatory.yaml')
    schema_path.write(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


def test_load_schema_with_tag_address(tmpdir):
    schema_def = """
%YAML 1.1
%TAG !asdf! tag:stsci.edu:asdf/
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.0.0"
id: "http://stsci.edu/schemas/asdf/nugatory/nugatory-1.0.0"
tag: "tag:stsci.edu:asdf/nugatory/nugatory-1.0.0"

type: object
properties:
  foobar:
      $ref: "http://stsci.edu/schemas/asdf/core/ndarray-1.0.0"

required: [foobar]
...
    """
    schema_path = tmpdir.join('nugatory.yaml')
    schema_path.write(schema_def.encode())

    schema_tree = schema.load_schema(str(schema_path), resolve_references=True)
    schema.check_schema(schema_tree)


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
        name = 'custom'
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
    # This should cause a warning but not an error because without explicitly
    # providing an extension, our custom type will not be recognized and will
    # simply be converted to a raw type.
    with pytest.warns(None) as warning:
        with asdf.AsdfFile.open(buff):
            pass
    assert len(warning) == 1

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


def test_tag_reference_validation():
    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [TagReferenceType]

    yaml = """
custom: !<tag:nowhere.org:custom/tag_reference-1.0.0>
  name:
    "Something"
  things: !core/ndarray-1.0.0
    data: [1, 2, 3]
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff, extensions=[DefaultTypeExtension()]) as ff:
        custom = ff.tree['custom']
        assert custom['name'] == "Something"
        assert_array_equal(custom['things'], [1, 2, 3])


def test_foreign_tag_reference_validation():
    class ForeignTagReferenceType(asdftypes.CustomType):
        name = 'foreign_tag_reference'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'

        @classmethod
        def from_tree(cls, tree, ctx):
            node = {}
            node['a'] = yamlutil.tagged_tree_to_custom_tree(tree['a'], ctx)
            node['b'] = yamlutil.tagged_tree_to_custom_tree(tree['b'], ctx)
            return node

    class ForeignTypeExtension(CustomExtension):
        @property
        def types(self):
            return [TagReferenceType, ForeignTagReferenceType]

    yaml = """
custom: !<tag:nowhere.org:custom/foreign_tag_reference-1.0.0>
  a: !<tag:nowhere.org:custom/tag_reference-1.0.0>
    name:
      "Something"
    things: !core/ndarray-1.0.0
      data: [1, 2, 3]
  b: !<tag:nowhere.org:custom/tag_reference-1.0.0>
    name:
      "Anything"
    things: !core/ndarray-1.0.0
      data: [4, 5, 6]
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff, extensions=ForeignTypeExtension()) as ff:
        a = ff.tree['custom']['a']
        b = ff.tree['custom']['b']
        assert a['name'] == 'Something'
        assert_array_equal(a['things'], [1, 2, 3])
        assert b['name'] == 'Anything'
        assert_array_equal(b['things'], [4, 5, 6])


def test_self_reference_resolution():
    r = resolver.Resolver(CustomExtension().url_mapping, 'url')
    s = schema.load_schema(
        helpers.get_test_data_path('self_referencing-1.0.0.yaml'),
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


@pytest.mark.importorskip('astropy')
def test_type_missing_dependencies():

    class MissingType(asdftypes.AsdfType):
        name = 'missing'
        organization = 'nowhere.org'
        version = (1, 1, 0)
        standard = 'custom'
        types = ['asdfghjkl12345.foo']
        requires = ["ASDFGHJKL12345"]

    class DefaultTypeExtension(CustomExtension):
        @property
        def types(self):
            return [MissingType]

    yaml = """
custom: !<tag:nowhere.org:custom/missing-1.1.0>
  b: {foo: 42}
    """
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as w:
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

    with pytest.warns(None) as warnings:
        helpers.assert_roundtrip_tree(
            tree, tmpdir, extensions=[CustomTypeExtension()])

    assert len(warnings) == 0, helpers.display_warnings(warnings)

    assert called_custom_assert_equal[0] is True


def test_custom_validation_bad(tmpdir):
    custom_schema_path = helpers.get_test_data_path('custom_schema.yaml')
    asdf_file = os.path.join(str(tmpdir), 'out.asdf')

    # This tree does not conform to the custom schema
    tree = {'stuff': 42, 'other_stuff': 'hello'}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file using custom schema should fail
    with pytest.raises(ValidationError):
        with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
            pass

    # Opening file without custom schema should pass
    with asdf.open(asdf_file) as ff:
        pass

    # Opening file with custom schema should fail
    with pytest.raises(ValidationError):
        with asdf.open(asdf_file, custom_schema=custom_schema_path) as ff:
            pass


def test_custom_validation_good(tmpdir):
    custom_schema_path = helpers.get_test_data_path('custom_schema.yaml')
    asdf_file = os.path.join(str(tmpdir), 'out.asdf')

    # This tree conforms to the custom schema
    tree = {
        'foo': {'x': 42, 'y': 10},
        'bar': {'a': 'hello', 'b': 'banjo'}
    }

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path) as ff:
        pass


def test_custom_validation_with_definitions_good(tmpdir):
    custom_schema_path = helpers.get_test_data_path('custom_schema_definitions.yaml')
    asdf_file = os.path.join(str(tmpdir), 'out.asdf')

    # This tree conforms to the custom schema
    tree = {
        'thing': { 'biz': 'hello', 'baz': 'world' }
    }

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path) as ff:
        pass


def test_custom_validation_with_definitions_bad(tmpdir):
    custom_schema_path = helpers.get_test_data_path('custom_schema_definitions.yaml')
    asdf_file = os.path.join(str(tmpdir), 'out.asdf')

    # This tree does NOT conform to the custom schema
    tree = {
        'forb': { 'biz': 'hello', 'baz': 'world' }
    }

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file with custom schema should fail
    with pytest.raises(ValidationError):
        with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
            pass

    # Opening file without custom schema should pass
    with asdf.open(asdf_file) as ff:
        pass

    # Opening file with custom schema should fail
    with pytest.raises(ValidationError):
        with asdf.open(asdf_file, custom_schema=custom_schema_path) as ff:
            pass
