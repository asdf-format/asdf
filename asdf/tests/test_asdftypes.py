# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io
import os
import sys
import pytest

import asdf
from asdf import asdftypes
from asdf import extension
from asdf import util
from asdf import versioning

from . import helpers, CustomTestType


TEST_DATA_PATH = str(helpers.get_test_data_path(''))


def test_custom_tag():
    import fractions

    class FractionType(asdftypes.AsdfType):
        name = 'fraction'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [fractions.Fraction]

        @classmethod
        def to_tree(cls, node, ctx):
            return [node.numerator, node.denominator]

        @classmethod
        def from_tree(cls, tree, ctx):
            return fractions.Fraction(tree[0], tree[1])

    class FractionExtension(object):
        @property
        def types(self):
            return [FractionType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/{url_suffix}.yaml')]

    class FractionCallable(FractionExtension):
        @property
        def tag_mapping(self):
            def check(tag):
                prefix = 'tag:nowhere.org:custom'
                if tag.startswith(prefix):
                    return 'http://nowhere.org/schemas/custom' + tag[len(prefix):]
            return [check]

    yaml = """
a: !<tag:nowhere.org:custom/fraction-1.0.0>
  [2, 3]
b: !core/complex-1.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(
        buff, extensions=FractionExtension()) as ff:
        assert ff.tree['a'] == fractions.Fraction(2, 3)

        buff = io.BytesIO()
        ff.write_to(buff)

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(
            buff, extensions=FractionCallable()) as ff:
        assert ff.tree['a'] == fractions.Fraction(2, 3)

        buff = io.BytesIO()
        ff.write_to(buff)
        buff.close()


def test_version_mismatch():
    yaml = """
a: !core/complex-42.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as warning:
        with asdf.AsdfFile.open(buff, ignore_version_mismatch=False) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 1
    assert str(warning[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file, "
        "but latest supported version is 1.0.0")

    # Make sure warning is repeatable
    buff.seek(0)
    with pytest.warns(None) as warning:
        with asdf.AsdfFile.open(buff, ignore_version_mismatch=False) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 1
    assert str(warning[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file, "
        "but latest supported version is 1.0.0")

    # Make sure the warning does not occur if it is being ignored (default)
    buff.seek(0)
    with pytest.warns(None) as warning:
        with asdf.AsdfFile.open(buff) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 0, helpers.display_warnings(warning)


    # If the major and minor match, there should be no warning.
    yaml = """
a: !core/complex-1.0.1
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as warning:
        with asdf.AsdfFile.open(buff, ignore_version_mismatch=False) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 0


@pytest.mark.skipif(sys.platform.startswith('win'),
    reason='Avoid path manipulation on Windows')
def test_version_mismatch_file(tmpdir):
    testfile = os.path.join(str(tmpdir), 'mismatch.asdf')
    yaml = """
a: !core/complex-42.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with open(testfile, 'wb') as handle:
        handle.write(buff.read())

    with pytest.warns(None) as w:
        with asdf.AsdfFile.open(testfile, ignore_version_mismatch=False) as ff:
            assert ff._fname == "file://{}".format(testfile)
            assert isinstance(ff.tree['a'], complex)

    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file "
        "'file://{}', but latest supported version is 1.0.0".format(testfile))


def test_version_mismatch_with_supported_versions():
    """Make sure that defining the supported_versions field does not affect
    whether or not schema mismatch warnings are triggered."""

    class CustomFlow(object):
        pass

    class CustomFlowType(CustomTestType):
        version = '1.1.0'
        supported_versions = ['1.0.0', '1.1.0']
        name = 'custom_flow'
        organization = 'nowhere.org'
        standard = 'custom'
        types = [CustomFlow]

    class CustomFlowExtension(object):
        @property
        def types(self):
            return [CustomFlowType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/{url_suffix}.yaml')]

    yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    c: 100
    d: 3.14
"""
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as w:
        data = asdf.AsdfFile.open(
            buff, ignore_version_mismatch=False,
            extensions=CustomFlowExtension())
    assert len(w) == 1, helpers.display_warnings(w)
    assert str(w[0].message) == (
        "'tag:nowhere.org:custom/custom_flow' with version 1.0.0 found in "
        "file, but latest supported version is 1.1.0")


def test_versioned_writing():
    from ..tags.core.complex import ComplexType

    # Create a bogus version map
    versioning._version_map['42.0.0'] = {
        'FILE_FORMAT': '42.0.0',
        'YAML_VERSION': '1.1',
        'tags': {
            'tag:stsci.edu:asdf/core/complex': '42.0.0',
            'tag:stscu.edu:asdf/core/asdf': '1.0.0'
        }
    }

    versioning.supported_versions.append(versioning.AsdfVersion('42.0.0'))

    class FancyComplexType(ComplexType, asdftypes.CustomType):
        version = (42, 0, 0)

    # This is a sanity check to ensure that the custom FancyComplexType does
    # not get added to ASDF's built-in extension, since this would cause any
    # subsequent tests that rely on ComplexType to fail.
    assert not issubclass(FancyComplexType, asdftypes.AsdfTypeMeta)

    class FancyComplexExtension(object):
        @property
        def types(self):
            return [FancyComplexType]

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return [('http://stsci.edu/schemas/asdf/core/complex-42.0.0',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/complex-42.0.0.yaml')]

    tree = {'a': complex(0, -1)}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, version="42.0.0",
                       extensions=[FancyComplexExtension()])
    ff.write_to(buff)

    assert b'complex-42.0.0' in buff.getvalue()

    del versioning._version_map['42.0.0']
    versioning.supported_versions.pop()


def test_longest_match():
    class FancyComplexExtension(object):
        @property
        def types(self):
            return []

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return [('http://stsci.edu/schemas/asdf/core/',
                     'FOOBAR/{url_suffix}')]

    l = extension.AsdfExtensionList(
        [extension.BuiltinExtension(), FancyComplexExtension()])

    assert l.url_mapping(
        'http://stsci.edu/schemas/asdf/core/asdf-1.0.0') == 'FOOBAR/asdf-1.0.0'
    assert l.url_mapping(
        'http://stsci.edu/schemas/asdf/transform/transform-1.0.0') != 'FOOBAR/transform-1.0.0'


def test_module_versioning():
    class NoModuleType(asdftypes.AsdfType):
        # It seems highly unlikely that this would be a real module
        requires = ['qkjvqdja']

    class HasCorrectPytest(asdftypes.AsdfType):
        # This means it requires 1.0.0 or greater, so it should succeed
        requires = ['pytest-1.0.0']

    class DoesntHaveCorrectPytest(asdftypes.AsdfType):
        requires = ['pytest-91984.1.7']

    nmt = NoModuleType()
    hcp = HasCorrectPytest()
    # perhaps an unfortunate acroynm
    dhcp = DoesntHaveCorrectPytest()

    assert nmt.has_required_modules == False
    assert hcp.has_required_modules == True
    assert dhcp.has_required_modules == False


def test_undefined_tag():
    # This tests makes sure that ASDF still returns meaningful structured data
    # even when it encounters a schema tag that it does not specifically
    # implement as an extension
    from numpy import array

    yaml = """
undefined_data:
  !<tag:nowhere.org:custom/undefined_tag-1.0.0>
    - 5
    - {'message': 'there is no tag'}
    - !core/ndarray-1.0.0
      [[1, 2, 3], [4, 5, 6]]
    - !<tag:nowhere.org:custom/also_undefined-1.3.0>
        - !core/ndarray-1.0.0 [[7],[8],[9],[10]]
        - !core/complex-1.0.0 3.14j
"""
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as warning:
        afile = asdf.AsdfFile.open(buff)
        missing = afile.tree['undefined_data']

    assert missing[0] == 5
    assert missing[1] == {'message': 'there is no tag'}
    assert (missing[2] == array([[1, 2, 3], [4, 5, 6]])).all()
    assert (missing[3][0] == array([[7],[8],[9],[10]])).all()
    assert missing[3][1] == 3.14j

    # There are two undefined tags, so we expect two warnings
    assert len(warning) == 2
    for i, tag in enumerate(["also_undefined-1.3.0", "undefined_tag-1.0.0"]):
        assert str(warning[i].message) == (
            "tag:nowhere.org:custom/{} is not recognized, converting to raw "
            "Python data structure".format(tag))

    # Make sure no warning occurs if explicitly ignored
    buff.seek(0)
    with pytest.warns(None) as warning:
        afile = asdf.AsdfFile.open(buff, ignore_unrecognized_tag=True)
    assert len(warning) == 0


def test_newer_tag():
    # This test simulates a scenario where newer versions of CustomFlow
    # provides different keyword parameters that the older schema and tag class
    # do not account for. We want to test whether ASDF can handle this problem
    # gracefully and still provide meaningful data as output. The test case is
    # fairly contrived but we want to test whether ASDF can handle backwards
    # compatibility even when an explicit tag class for different versions of a
    # schema is not available.
    class CustomFlow(object):
        def __init__(self, c=None, d=None):
            self.c = c
            self.d = d

    class CustomFlowType(asdftypes.CustomType):
        version = '1.1.0'
        name = 'custom_flow'
        organization = 'nowhere.org'
        standard = 'custom'
        types = [CustomFlow]

        @classmethod
        def from_tree(cls, tree, ctx):
            kwargs = {}
            for name in tree:
                kwargs[name] = tree[name]
            return CustomFlow(**kwargs)

        @classmethod
        def to_tree(cls, data, ctx):
            tree = dict(c=data.c, d=data.d)

    class CustomFlowExtension(object):
        @property
        def types(self):
            return [CustomFlowType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/{url_suffix}.yaml')]

    new_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    new_buff = helpers.yaml_to_asdf(new_yaml)
    new_data = asdf.AsdfFile.open(new_buff, extensions=CustomFlowExtension())
    assert type(new_data.tree['flow_thing']) == CustomFlow

    old_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    a: 100
    b: 3.14
"""
    old_buff = helpers.yaml_to_asdf(old_yaml)
    with pytest.warns(None) as warning:
        asdf.AsdfFile.open(old_buff, extensions=CustomFlowExtension())

    assert len(warning) == 1, helpers.display_warnings(warning)
    # We expect this warning since it will not be possible to convert version
    # 1.0.0 of CustomFlow to a CustomType (by design, for testing purposes).
    assert str(warning[0].message).startswith(
        "Failed to convert "
        "tag:nowhere.org:custom/custom_flow-1.0.0 to custom type")

def test_incompatible_version_check():
    class TestType0(asdftypes.CustomType):
        supported_versions = versioning.AsdfSpec('>=1.2.0')

    assert TestType0.incompatible_version('1.1.0') == True
    assert TestType0.incompatible_version('1.2.0') == False
    assert TestType0.incompatible_version('2.0.1') == False

    class TestType1(asdftypes.CustomType):
        supported_versions = versioning.AsdfVersion('1.0.0')

    assert TestType1.incompatible_version('1.0.0') == False
    assert TestType1.incompatible_version('1.1.0') == True

    class TestType2(asdftypes.CustomType):
        supported_versions = '1.0.0'

    assert TestType2.incompatible_version('1.0.0') == False
    assert TestType2.incompatible_version('1.1.0') == True

    class TestType3(asdftypes.CustomType):
        # This doesn't make much sense, but it's just for the sake of example
        supported_versions = ['1.0.0', versioning.AsdfSpec('>=2.0.0')]

    assert TestType3.incompatible_version('1.0.0') == False
    assert TestType3.incompatible_version('1.1.0') == True
    assert TestType3.incompatible_version('2.0.0') == False
    assert TestType3.incompatible_version('2.0.1') == False

    class TestType4(asdftypes.CustomType):
        supported_versions = ['1.0.0', versioning.AsdfVersion('1.1.0')]

    assert TestType4.incompatible_version('1.0.0') == False
    assert TestType4.incompatible_version('1.0.1') == True
    assert TestType4.incompatible_version('1.1.0') == False
    assert TestType4.incompatible_version('1.1.1') == True

    class TestType5(asdftypes.CustomType):
        supported_versions = \
            [versioning.AsdfSpec('<1.0.0'), versioning.AsdfSpec('>=2.0.0')]

    assert TestType5.incompatible_version('0.9.9') == False
    assert TestType5.incompatible_version('2.0.0') == False
    assert TestType5.incompatible_version('2.0.1') == False
    assert TestType5.incompatible_version('1.0.0') == True
    assert TestType5.incompatible_version('1.1.0') == True

    with pytest.raises(ValueError):
        class TestType6(asdftypes.CustomType):
            supported_versions = 'blue'
    with pytest.raises(ValueError):
        class TestType6(asdftypes.CustomType):
            supported_versions = ['1.1.0', '2.2.0', 'blue']

def test_supported_versions():
    class CustomFlow(object):
        def __init__(self, c=None, d=None):
            self.c = c
            self.d = d

    class CustomFlowType(asdftypes.CustomType):
        version = '1.1.0'
        supported_versions = [(1,0,0), versioning.AsdfSpec('>=1.1.0')]
        name = 'custom_flow'
        organization = 'nowhere.org'
        standard = 'custom'
        types = [CustomFlow]

        @classmethod
        def from_tree(cls, tree, ctx):
            # Convert old schema to new CustomFlow type
            if cls.version == '1.0.0':
                return CustomFlow(c=tree['a'], d=tree['b'])
            else:
                return CustomFlow(**tree)
            return CustomFlow(**kwargs)

        @classmethod
        def to_tree(cls, data, ctx):
            if cls.version == '1.0.0':
                tree = dict(a=data.c, b=data.d)
            else:
                tree = dict(c=data.c, d=data.d)

    class CustomFlowExtension(object):
        @property
        def types(self):
            return [CustomFlowType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/{url_suffix}.yaml')]

    new_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    old_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    a: 100
    b: 3.14
"""
    new_buff = helpers.yaml_to_asdf(new_yaml)
    new_data = asdf.AsdfFile.open(new_buff, extensions=CustomFlowExtension())
    assert type(new_data.tree['flow_thing']) == CustomFlow

    old_buff = helpers.yaml_to_asdf(old_yaml)
    old_data = asdf.AsdfFile.open(old_buff, extensions=CustomFlowExtension())
    assert type(old_data.tree['flow_thing']) == CustomFlow

def test_unsupported_version_warning():
    class CustomFlow(object):
        pass

    class CustomFlowType(asdftypes.CustomType):
        version = '1.0.0'
        supported_versions = [(1,0,0)]
        name = 'custom_flow'
        organization = 'nowhere.org'
        standard = 'custom'
        types = [CustomFlow]

    class CustomFlowExtension(object):
        @property
        def types(self):
            return [CustomFlowType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/{url_suffix}.yaml')]

    yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    buff = helpers.yaml_to_asdf(yaml)

    with pytest.warns(None) as _warnings:
        data = asdf.AsdfFile.open(buff, extensions=CustomFlowExtension())

    assert len(_warnings) == 1
    assert str(_warnings[0].message) == (
        "Version 1.1.0 of tag:nowhere.org:custom/custom_flow is not compatible "
        "with any existing tag implementations")
