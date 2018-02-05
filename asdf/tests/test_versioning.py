# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import pytest
from itertools import combinations

from asdf.versioning import AsdfVersion, AsdfSpec


def test_version_constructor():
    ver0 = AsdfVersion('1.0.0')
    ver1 = AsdfVersion((1,0,0))
    ver2 = AsdfVersion([1,0,0])

    assert str(ver0) == '1.0.0'
    assert str(ver1) == '1.0.0'
    assert str(ver2) == '1.0.0'

def test_version_and_version_equality():
    ver0 = AsdfVersion('1.0.0')
    ver1 = AsdfVersion('1.0.0')

    assert ver0 is not ver1
    assert ver0 == ver1
    assert ver1 == ver0
    assert not (ver0 != ver1)
    assert not (ver1 != ver0)

def test_version_and_string_equality():
    version = AsdfVersion('1.0.0')
    string_ver = '1.0.0'

    assert version == string_ver
    assert string_ver == version
    assert not (version != string_ver)
    assert not (string_ver != version)

def test_version_and_tuple_equality():
    version = AsdfVersion('1.0.0')
    tuple_ver = (1,0,0)

    assert version == tuple_ver
    assert tuple_ver == version
    assert not (version != tuple_ver)
    assert not (tuple_ver != version)

def test_version_and_version_inequality():
    ver0 = AsdfVersion('1.0.0')
    ver1 = AsdfVersion('1.0.1')
    ver2 = AsdfVersion('1.1.0')
    ver3 = AsdfVersion('1.1.1')
    ver4 = AsdfVersion('2.0.0')
    ver5 = AsdfVersion('2.0.1')
    ver6 = AsdfVersion('2.1.0')
    ver7 = AsdfVersion('2.1.1')

    versions = [ver0, ver1, ver2, ver3, ver4, ver5, ver6, ver7]
    for x,y in combinations(versions, 2):
        assert not (x == y)
        assert x != y

    assert ver0 < ver1 < ver2 < ver3 < ver4 < ver5 < ver6 < ver7
    assert ver7 > ver6 > ver5 > ver4 > ver3 > ver2 > ver1 > ver0
    assert (ver0 < ver1 < ver2 < ver4 < ver3 < ver5 < ver6 < ver7) == False
    assert (ver7 > ver6 > ver5 > ver3 > ver4 > ver2 > ver1 > ver0) == False

    assert ver0 <= ver1 <= ver2 <= ver3 <= ver4 <= ver5 <= ver6 <= ver7
    assert ver7 >= ver6 >= ver5 >= ver4 >= ver3 >= ver2 >= ver1 >= ver0

def test_version_and_string_inequality():
    version = AsdfVersion('2.0.0')

    assert version > '1.0.0'
    assert version > '1.0.1'
    assert version > '1.1.0'
    assert version > '1.1.1'
    assert (version > '2.0.0') == False
    assert (version < '2.0.0') == False
    assert version < '2.0.1'
    assert version < '2.1.0'
    assert version < '2.1.1'

    assert version >= '1.0.0'
    assert version >= '1.0.1'
    assert version >= '1.1.0'
    assert version >= '1.1.1'
    assert version >= '2.0.0'
    assert version <= '2.0.0'
    assert version <= '2.0.1'
    assert version <= '2.1.0'
    assert version <= '2.1.1'

    assert '1.0.0' < version
    assert '1.0.1' < version
    assert '1.1.0' < version
    assert '1.1.1' < version
    assert ('2.0.0' < version) == False
    assert ('2.0.0' > version) == False
    assert '2.0.1' > version
    assert '2.1.0' > version
    assert '2.1.1' > version

    assert '1.0.0' <= version
    assert '1.0.1' <= version
    assert '1.1.0' <= version
    assert '1.1.1' <= version
    assert '2.0.0' <= version
    assert '2.0.0' >= version
    assert '2.0.1' >= version
    assert '2.1.0' >= version
    assert '2.1.1' >= version


def test_version_and_tuple_inequality():
    version = AsdfVersion('2.0.0')

    assert version > (1,0,0)
    assert version > (1,0,1)
    assert version > (1,1,0)
    assert version > (1,1,1)
    assert (version > (2,0,0)) == False
    assert (version < (2,0,0)) == False
    assert version < (2,0,1)
    assert version < (2,1,0)
    assert version < (2,1,1)

    assert version >= (1,0,0)
    assert version >= (1,0,1)
    assert version >= (1,1,0)
    assert version >= (1,1,1)
    assert version >= (2,0,0)
    assert version <= (2,0,0)
    assert version <= (2,0,1)
    assert version <= (2,1,0)
    assert version <= (2,1,1)

    assert (1,0,0) < version
    assert (1,0,1) < version
    assert (1,1,0) < version
    assert (1,1,1) < version
    assert ((2,0,0) < version) == False
    assert ((2,0,0) > version) == False
    assert (2,0,1) > version
    assert (2,1,0) > version
    assert (2,1,1) > version

    assert (1,0,0) <= version
    assert (1,0,1) <= version
    assert (1,1,0) <= version
    assert (1,1,1) <= version
    assert (2,0,0) <= version
    assert (2,0,0) >= version
    assert (2,0,1) >= version
    assert (2,1,0) >= version
    assert (2,1,1) >= version

def test_spec_version_match():
    spec = AsdfSpec('>=1.1.0')

    assert spec.match(AsdfVersion('1.1.0'))
    assert spec.match(AsdfVersion('1.2.0'))
    assert not spec.match(AsdfVersion('1.0.0'))
    assert not spec.match(AsdfVersion('1.0.9'))

def test_spec_version_select():
    spec = AsdfSpec('>=1.1.0')

    versions = [AsdfVersion(x) for x in ['1.0.0', '1.0.9', '1.1.0', '1.2.0']]
    assert spec.select(versions) == '1.2.0'
    assert spec.select(versions[:-1]) == '1.1.0'
    assert spec.select(versions[:-2]) == None

def test_spec_version_filter():
    spec = AsdfSpec('>=1.1.0')

    versions = [AsdfVersion(x) for x in ['1.0.0', '1.0.9', '1.1.0', '1.2.0']]
    for x,y in zip(spec.filter(versions), ['1.1.0', '1.2.0']):
        assert x == y

def test_spec_string_match():
    spec = AsdfSpec('>=1.1.0')

    assert spec.match('1.1.0')
    assert spec.match('1.2.0')
    assert not spec.match('1.0.0')
    assert not spec.match('1.0.9')

def test_spec_string_select():
    spec = AsdfSpec('>=1.1.0')

    versions = ['1.0.0', '1.0.9', '1.1.0', '1.2.0']
    assert spec.select(versions) == '1.2.0'
    assert spec.select(versions[:-1]) == '1.1.0'
    assert spec.select(versions[:-2]) == None

def test_spec_string_filter():
    spec = AsdfSpec('>=1.1.0')

    versions = ['1.0.0', '1.0.9', '1.1.0', '1.2.0']
    for x,y in zip(spec.filter(versions), ['1.1.0', '1.2.0']):
        assert x == y

def test_spec_tuple_match():
    spec = AsdfSpec('>=1.1.0')

    assert spec.match((1,1,0))
    assert spec.match((1,2,0))
    assert not spec.match((1,0,0))
    assert not spec.match((1,0,9))

def test_spec_tuple_select():
    spec = AsdfSpec('>=1.1.0')

    versions = [(1,0,0), (1,0,9), (1,1,0), (1,2,0)]
    assert spec.select(versions) == '1.2.0'
    assert spec.select(versions[:-1]) == '1.1.0'
    assert spec.select(versions[:-2]) == None

def test_spec_tuple_filter():
    spec = AsdfSpec('>=1.1.0')

    versions = [(1,0,0), (1,0,9), (1,1,0), (1,2,0)]
    for x,y in zip(spec.filter(versions), ['1.1.0', '1.2.0']):
        assert x == y

def test_spec_equal():
    """Make sure that equality means match"""
    spec = AsdfSpec('>=1.2.0')
    version0 = AsdfVersion('1.1.0')
    version1 = AsdfVersion('1.3.0')

    assert spec != version0
    assert version0 != spec
    assert spec == version1
    assert version1 == spec

    assert spec != '1.1.0'
    assert '1.1.0' != spec
    assert spec == '1.3.0'
    assert '1.3.0' == spec

    assert spec != (1, 1, 0)
    assert (1, 1, 0) != spec
    assert spec == (1, 3, 0)
    assert (1, 3, 0) == spec
