# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import io
import os
import sys
from fractions import Fraction

import pytest

import asdf
from asdf import types
from asdf import extension
from asdf import util
from asdf import versioning

from . import helpers, CustomTestType, CustomExtension


TEST_DATA_PATH = str(helpers.get_test_data_path(''))


class Fractional2dCoord:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class FractionWithInverse(Fraction):
    def __init__(self, *args, **kwargs):
        self._inverse = None

    @property
    def inverse(self):
        return self._inverse

    @inverse.setter
    def inverse(self, value):
        self._inverse = value


class FractionWithInverseType(asdf.CustomType):
    name = 'fraction_with_inverse'
    organization = 'nowhere.org'
    version = (1, 0, 0)
    standard = 'custom'
    types = [FractionWithInverse]

    @classmethod
    def to_tree(cls, node, ctx):
        return {
            "numerator": node.numerator,
            "denominator": node.denominator,
            "inverse": node.inverse
        }

    @classmethod
    def from_tree(cls, tree, ctx):
        result = FractionWithInverse(
            tree["numerator"],
            tree["denominator"]
        )
        yield result
        result.inverse = tree["inverse"]


class FractionWithInverseExtension(CustomExtension):
    @property
    def types(self):
        return [FractionWithInverseType]

    @property
    def tag_mapping(self):
        return [('tag:nowhere.org:custom',
                    'http://nowhere.org/schemas/custom{tag_suffix}')]

    @property
    def url_mapping(self):
        return [('http://nowhere.org/schemas/custom/',
                    util.filepath_to_url(TEST_DATA_PATH) + '/{url_suffix}.yaml')]


def fractiontype_factory():

    class FractionType(types.CustomType):
        name = 'fraction'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [Fraction]
        handle_dynamic_subclasses = True

        @classmethod
        def to_tree(cls, node, ctx):
            return [node.numerator, node.denominator]

        @classmethod
        def from_tree(cls, tree, ctx):
            return Fraction(tree[0], tree[1])

    return FractionType


def fractional2dcoordtype_factory():

    FractionType = fractiontype_factory()

    class Fractional2dCoordType(types.CustomType):
        name = 'fractional_2d_coord'
        organization = 'nowhere.org'
        standard = 'custom'
        version = (1, 0, 0)
        types = [Fractional2dCoord]

        @classmethod
        def to_tree(cls, node, ctx):
            return {
                "x": node.x,
                "y": node.y
            }

        @classmethod
        def from_tree(cls, tree, ctx):
            return Fractional2dCoord(tree["x"], tree["y"])


    class Fractional2dCoordExtension(CustomExtension):
        @property
        def types(self):
            return [FractionType, Fractional2dCoordType]

    return FractionType, Fractional2dCoordType, Fractional2dCoordExtension


def test_custom_tag():

    FractionType = fractiontype_factory()

    class FractionExtension(CustomExtension):
        @property
        def types(self):
            return [FractionType]

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
    with asdf.open(buff, extensions=FractionExtension()) as ff:
        assert ff.tree['a'] == Fraction(2, 3)

        buff = io.BytesIO()
        ff.write_to(buff)

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff, extensions=FractionCallable()) as ff:
        assert ff.tree['a'] == Fraction(2, 3)

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
        with asdf.open(buff, ignore_version_mismatch=False) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 1
    assert str(warning[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file, "
        "but latest supported version is 1.0.0")

    # Make sure warning is repeatable
    buff.seek(0)
    with pytest.warns(None) as warning:
        with asdf.open(buff, ignore_version_mismatch=False) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 1
    assert str(warning[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file, "
        "but latest supported version is 1.0.0")

    # Make sure the warning does not occur if it is being ignored (default)
    buff.seek(0)
    with pytest.warns(None) as warning:
        with asdf.open(buff) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(warning) == 0, helpers.display_warnings(warning)


    # If the major and minor match, there should be no warning.
    yaml = """
a: !core/complex-1.0.1
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as warning:
        with asdf.open(buff, ignore_version_mismatch=False) as ff:
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
        with asdf.open(testfile, ignore_version_mismatch=False) as ff:
            assert ff._fname == "file://{}".format(testfile)
            assert isinstance(ff.tree['a'], complex)

    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file "
        "'file://{}', but latest supported version is 1.0.0".format(testfile))


def test_version_mismatch_with_supported_versions():
    """Make sure that defining the supported_versions field does not affect
    whether or not schema mismatch warnings are triggered."""

    class CustomFlow:
        pass

    class CustomFlowType(CustomTestType):
        version = '1.1.0'
        supported_versions = ['1.0.0', '1.1.0']
        name = 'custom_flow'
        organization = 'nowhere.org'
        standard = 'custom'
        types = [CustomFlow]

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    c: 100
    d: 3.14
"""
    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(None) as w:
        asdf.open(buff, ignore_version_mismatch=False,
            extensions=CustomFlowExtension())
    assert len(w) == 1, helpers.display_warnings(w)
    assert str(w[0].message) == (
        "'tag:nowhere.org:custom/custom_flow' with version 1.0.0 found in "
        "file, but latest supported version is 1.1.0")


def test_versioned_writing(monkeypatch):
    from ..tags.core.complex import ComplexType

    # Create a bogus version map
    monkeypatch.setitem(versioning._version_map, '42.0.0', {
        'FILE_FORMAT': '42.0.0',
        'YAML_VERSION': '1.1',
        'tags': {
            'tag:stsci.edu:asdf/core/complex': '42.0.0',
            'tag:stscu.edu:asdf/core/asdf': '1.0.0'
        },
        # We need to insert these explicitly since we're monkeypatching
        'core': {
            'tag:stsci.edu:asdf/core/complex': '42.0.0',
            'tag:stscu.edu:asdf/core/asdf': '1.0.0'
        },
        'standard': {}
    })

    # Add bogus version to supported versions
    monkeypatch.setattr(versioning, 'supported_versions',
        versioning.supported_versions + [versioning.AsdfVersion('42.0.0')]
    )

    class FancyComplexType(types.CustomType):
        name = 'core/complex'
        organization = 'stsci.edu'
        standard = 'asdf'
        version = (42, 0, 0)
        types = [complex]

        @classmethod
        def to_tree(cls, node, ctx):
            return ComplexType.to_tree(node, ctx)

        @classmethod
        def from_tree(cls, tree, ctx):
            return ComplexType.from_tree(tree, ctx)

    class FancyComplexExtension:
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


def test_longest_match():
    class FancyComplexExtension:
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
    class NoModuleType(types.CustomType):
        # It seems highly unlikely that this would be a real module
        requires = ['qkjvqdja']

    class HasCorrectPytest(types.CustomType):
        # This means it requires 1.0.0 or greater, so it should succeed
        requires = ['pytest-1.0.0']

    class DoesntHaveCorrectPytest(types.CustomType):
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
        afile = asdf.open(buff)
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
        afile = asdf.open(buff, ignore_unrecognized_tag=True)
    assert len(warning) == 0


def test_newer_tag():
    # This test simulates a scenario where newer versions of CustomFlow
    # provides different keyword parameters that the older schema and tag class
    # do not account for. We want to test whether ASDF can handle this problem
    # gracefully and still provide meaningful data as output. The test case is
    # fairly contrived but we want to test whether ASDF can handle backwards
    # compatibility even when an explicit tag class for different versions of a
    # schema is not available.
    class CustomFlow:
        def __init__(self, c=None, d=None):
            self.c = c
            self.d = d

    class CustomFlowType(types.CustomType):
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
            return dict(c=data.c, d=data.d)

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    new_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    new_buff = helpers.yaml_to_asdf(new_yaml)
    new_data = asdf.open(new_buff, extensions=CustomFlowExtension())
    assert type(new_data.tree['flow_thing']) == CustomFlow

    old_yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.0.0>
    a: 100
    b: 3.14
"""
    old_buff = helpers.yaml_to_asdf(old_yaml)
    with pytest.warns(None) as warning:
        asdf.open(old_buff, extensions=CustomFlowExtension())

    assert len(warning) == 1, helpers.display_warnings(warning)
    # We expect this warning since it will not be possible to convert version
    # 1.0.0 of CustomFlow to a CustomType (by design, for testing purposes).
    assert str(warning[0].message).startswith(
        "Failed to convert "
        "tag:nowhere.org:custom/custom_flow-1.0.0 to custom type")

def test_incompatible_version_check():
    class TestType0(types.CustomType):
        supported_versions = versioning.AsdfSpec('>=1.2.0')

    assert TestType0.incompatible_version('1.1.0') == True
    assert TestType0.incompatible_version('1.2.0') == False
    assert TestType0.incompatible_version('2.0.1') == False

    class TestType1(types.CustomType):
        supported_versions = versioning.AsdfVersion('1.0.0')

    assert TestType1.incompatible_version('1.0.0') == False
    assert TestType1.incompatible_version('1.1.0') == True

    class TestType2(types.CustomType):
        supported_versions = '1.0.0'

    assert TestType2.incompatible_version('1.0.0') == False
    assert TestType2.incompatible_version('1.1.0') == True

    class TestType3(types.CustomType):
        # This doesn't make much sense, but it's just for the sake of example
        supported_versions = ['1.0.0', versioning.AsdfSpec('>=2.0.0')]

    assert TestType3.incompatible_version('1.0.0') == False
    assert TestType3.incompatible_version('1.1.0') == True
    assert TestType3.incompatible_version('2.0.0') == False
    assert TestType3.incompatible_version('2.0.1') == False

    class TestType4(types.CustomType):
        supported_versions = ['1.0.0', versioning.AsdfVersion('1.1.0')]

    assert TestType4.incompatible_version('1.0.0') == False
    assert TestType4.incompatible_version('1.0.1') == True
    assert TestType4.incompatible_version('1.1.0') == False
    assert TestType4.incompatible_version('1.1.1') == True

    class TestType5(types.CustomType):
        supported_versions = \
            [versioning.AsdfSpec('<1.0.0'), versioning.AsdfSpec('>=2.0.0')]

    assert TestType5.incompatible_version('0.9.9') == False
    assert TestType5.incompatible_version('2.0.0') == False
    assert TestType5.incompatible_version('2.0.1') == False
    assert TestType5.incompatible_version('1.0.0') == True
    assert TestType5.incompatible_version('1.1.0') == True

    with pytest.raises(ValueError):
        class TestType6(types.CustomType):
            supported_versions = 'blue'
    with pytest.raises(ValueError):
        class TestType7(types.CustomType):
            supported_versions = ['1.1.0', '2.2.0', 'blue']

def test_supported_versions():
    class CustomFlow:
        def __init__(self, c=None, d=None):
            self.c = c
            self.d = d

    class CustomFlowType(types.CustomType):
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

        @classmethod
        def to_tree(cls, data, ctx):
            if cls.version == '1.0.0':
                return dict(a=data.c, b=data.d)
            else:
                return dict(c=data.c, d=data.d)

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

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
    new_data = asdf.open(new_buff, extensions=CustomFlowExtension())
    assert type(new_data.tree['flow_thing']) == CustomFlow

    old_buff = helpers.yaml_to_asdf(old_yaml)
    old_data = asdf.open(old_buff, extensions=CustomFlowExtension())
    assert type(old_data.tree['flow_thing']) == CustomFlow

def test_unsupported_version_warning():
    class CustomFlow:
        pass

    class CustomFlowType(types.CustomType):
        version = '1.0.0'
        supported_versions = [(1,0,0)]
        name = 'custom_flow'
        organization = 'nowhere.org'
        standard = 'custom'
        types = [CustomFlow]

    class CustomFlowExtension(CustomExtension):
        @property
        def types(self):
            return [CustomFlowType]

    yaml = """
flow_thing:
  !<tag:nowhere.org:custom/custom_flow-1.1.0>
    c: 100
    d: 3.14
"""
    buff = helpers.yaml_to_asdf(yaml)

    with pytest.warns(None) as _warnings:
        asdf.open(buff, extensions=CustomFlowExtension())

    assert len(_warnings) == 1
    assert str(_warnings[0].message) == (
        "Version 1.1.0 of tag:nowhere.org:custom/custom_flow is not compatible "
        "with any existing tag implementations")

def test_extension_override(tmpdir):

    gwcs = pytest.importorskip('gwcs', '0.12.0')

    from asdf.extension import default_extensions
    default_extensions.reset()

    version = str(versioning.default_version)
    tmpfile = str(tmpdir.join('override.asdf'))

    with asdf.AsdfFile() as aa:
        wti = aa.type_index._write_type_indices[version]
        assert wti.from_custom_type(gwcs.WCS) is gwcs.tags.wcs.WCSType
        aa.tree['wcs'] = gwcs.WCS(output_frame='icrs')
        aa.write_to(tmpfile)

    with open(tmpfile, 'rb') as ff:
        contents = str(ff.read())
        assert gwcs.tags.wcs.WCSType.yaml_tag in contents


def test_extension_override_subclass(tmpdir):

    gwcs = pytest.importorskip('gwcs', '0.12.0')
    pytest.importorskip('astropy', '4.0.0')

    from asdf.extension import default_extensions
    default_extensions.reset()

    version = str(versioning.default_version)
    tmpfile = str(tmpdir.join('override.asdf'))

    class SubclassWCS(gwcs.WCS):
        pass

    with asdf.AsdfFile() as aa:
        wti = aa.type_index._write_type_indices[version]
        assert wti.from_custom_type(gwcs.WCS) is gwcs.tags.wcs.WCSType
        assert wti.from_custom_type(SubclassWCS) is gwcs.tags.wcs.WCSType
        # The duplication here is deliberate: make sure that nothing has changed
        assert wti.from_custom_type(gwcs.WCS) is gwcs.tags.wcs.WCSType
        aa.tree['wcs'] = SubclassWCS(output_frame='icrs')
        aa.write_to(tmpfile)

    with open(tmpfile, 'rb') as ff:
        contents = str(ff.read())
        assert gwcs.tags.wcs.WCSType.yaml_tag in contents


def test_tag_without_schema(tmpdir):

    tmpfile = str(tmpdir.join('foo.asdf'))

    class FooType(types.CustomType):
        name = 'foo'

        def __init__(self, a, b):
            self.a = a
            self.b = b

        @classmethod
        def from_tree(cls, tree, ctx):
            return cls(tree['a'], tree['b'])

        @classmethod
        def to_tree(cls, node, ctx):
            return dict(a=node.a, b=node.b)

        def __eq__(self, other):
            return self.a == other.a and self.b == other.b

    class FooExtension:
        @property
        def types(self):
            return [FooType]

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return []

    foo = FooType('hello', 42)
    tree = dict(foo=foo)

    with pytest.warns(UserWarning) as w:
        with asdf.AsdfFile(tree, extensions=FooExtension()) as af:
            af.write_to(tmpfile)
        # There are three validation passes when writing. Eventually this may
        # change
        assert len(w) == 3, helpers.display_warnings(w)
        assert str(w[0].message).startswith('Unable to locate schema file')
        assert str(w[1].message).startswith('Unable to locate schema file')
        assert str(w[2].message).startswith('Unable to locate schema file')

    with pytest.warns(UserWarning) as w:
        with asdf.AsdfFile(tree, extensions=FooExtension()) as ff:
            assert isinstance(ff.tree['foo'], FooType)
            assert ff.tree['foo'] == tree['foo']
        # There is only one validation pass when writing.
        assert len(w) == 1, helpers.display_warnings(w)
        assert str(w[0].message).startswith('Unable to locate schema file')


def test_subclass_decorator(tmpdir):

    tmpfile = str(tmpdir.join('subclass.asdf'))

    (FractionType, Fractional2dCoordType,
        Fractional2dCoordExtension) = fractional2dcoordtype_factory()

    extension = Fractional2dCoordExtension()

    coord = Fractional2dCoord(Fraction(2, 3), Fraction(7, 9))
    tree = dict(coord=coord)

    # First make sure the base type is serialized properly
    with asdf.AsdfFile(tree, extensions=extension) as af:
        af.write_to(tmpfile)

    with asdf.open(tmpfile, extensions=extension) as af:
        assert isinstance(af['coord'], Fractional2dCoord)
        assert af['coord'].x == coord.x
        assert af['coord'].y == coord.y

    # Now create a subclass
    @Fractional2dCoordType.subclass
    class Subclass2dCoord(Fractional2dCoord):
        pass

    subclass_coord = Subclass2dCoord(Fraction(2, 3), Fraction(7, 9))
    tree = dict(coord=subclass_coord)

    with asdf.AsdfFile(tree, extensions=extension) as af:
        af.write_to(tmpfile)

    with asdf.open(tmpfile, extensions=extension) as af:
        assert isinstance(af['coord'], Subclass2dCoord)
        assert af['coord'].x == subclass_coord.x
        assert af['coord'].y == subclass_coord.y


def test_subclass_decorator_custom_attribute(tmpdir):

    tmpfile = str(tmpdir.join('subclass.asdf'))

    (FractionType, Fractional2dCoordType,
        Fractional2dCoordExtension) = fractional2dcoordtype_factory()

    extension = Fractional2dCoordExtension()

    coord = Fractional2dCoord(Fraction(2, 3), Fraction(7, 9))
    tree = dict(coord=coord)

    # First make sure the base type is serialized properly
    with asdf.AsdfFile(tree, extensions=extension) as af:
        af.write_to(tmpfile)

    with asdf.open(tmpfile, extensions=extension) as af:
        assert isinstance(af['coord'], Fractional2dCoord)
        assert af['coord'].x == coord.x
        assert af['coord'].y == coord.y

    # Now create a subclass
    @Fractional2dCoordType.subclass(attribute='bizbaz')
    class Subclass2dCoord(Fractional2dCoord):
        pass

    subclass_coord = Subclass2dCoord(Fraction(2, 3), Fraction(7, 9))
    tree = dict(coord=subclass_coord)

    with asdf.AsdfFile(tree, extensions=extension) as af:
        af.write_to(tmpfile)

    tmp = asdf.AsdfFile()
    af_yaml = asdf.AsdfFile._open_asdf(tmp, tmpfile, _force_raw_types=True)
    assert 'bizbaz' in af_yaml['coord']
    assert 'Subclass2dCoord' in af_yaml['coord']['bizbaz']['name']
    af_yaml.close()

    with asdf.open(tmpfile, extensions=extension) as af:
        assert isinstance(af['coord'], Subclass2dCoord)
        assert af['coord'].x == subclass_coord.x
        assert af['coord'].y == subclass_coord.y


def test_subclass_decorator_attribute(tmpdir):

    tmpfile = str(tmpdir.join('subclass.asdf'))

    (FractionType, Fractional2dCoordType,
        Fractional2dCoordExtension) = fractional2dcoordtype_factory()

    extension = Fractional2dCoordExtension()

    @Fractional2dCoordType.subclass
    class Subclass2dCoord(Fractional2dCoord):
        def __init__(self, *args, custom=None, other=None, **kwargs):
            super().__init__(*args, **kwargs)
            self._custom = custom
            self._other = other

        @Fractional2dCoordType.subclass_property
        def custom(self):
            return self._custom

        @Fractional2dCoordType.subclass_property
        def other(self):
            return self._other

    subclass_coord = Subclass2dCoord(Fraction(2, 3), Fraction(7, 9),
                                     custom='testing', other=[1,2,3,4])
    tree = dict(coord=subclass_coord)

    with asdf.AsdfFile(tree, extensions=extension) as af:
        af.write_to(tmpfile)

    with asdf.open(tmpfile, extensions=extension) as af:
        assert isinstance(af['coord'], Subclass2dCoord)
        assert af['coord'].x == subclass_coord.x
        assert af['coord'].y == subclass_coord.y
        assert af['coord'].custom == 'testing'
        assert af['coord'].other == [1,2,3,4]


def test_subclass_decorator_warning():

    FractionType = fractiontype_factory()

    class FractionExtension(CustomExtension):
        @property
        def types(self):
            return [FractionType]

    @FractionType.subclass
    class MyFraction(Fraction):
        # We need to override __new__ since Fraction is immutable
        def __new__(cls, *args, custom='custom', **kwargs):
            self = super().__new__(cls, *args, **kwargs)
            self._custom_attribute = custom
            return self

        @FractionType.subclass_property
        def custom_attribute(self):
            return self._custom_attribute


    tree = dict(fraction=MyFraction(7, 9, custom='TESTING!'))

    with pytest.warns(UserWarning) as w:
        with asdf.AsdfFile(tree, extensions=FractionExtension()):
            pass
        assert len(w) == 1, helpers.display_warnings(w)
        assert str(w[0].message).startswith("Failed to add subclass attribute(s)")


def test_custom_reference_cycle(tmpdir):
    f1 = FractionWithInverse(3, 5)
    f2 = FractionWithInverse(5, 3)
    f1.inverse = f2
    f2.inverse = f1
    tree = {"fraction": f1}

    path = str(tmpdir.join("with_inverse.asdf"))

    with asdf.AsdfFile(tree, extensions=FractionWithInverseExtension()) as af:
        af.write_to(path)

    with asdf.open(path, extensions=FractionWithInverseExtension()) as af:
        assert af["fraction"].inverse.inverse is af["fraction"]
