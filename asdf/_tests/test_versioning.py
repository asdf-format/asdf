from itertools import combinations

from asdf.versioning import (
    AsdfVersion,
    asdf_standard_development_version,
    default_version,
    supported_versions,
)


def test_default_in_supported_versions():
    assert default_version in supported_versions


def test_development_is_not_default():
    assert default_version != asdf_standard_development_version


def test_version_constructor():
    ver0 = AsdfVersion("1.0.0")
    ver1 = AsdfVersion((1, 0, 0))
    ver2 = AsdfVersion([1, 0, 0])

    assert str(ver0) == "1.0.0"
    assert str(ver1) == "1.0.0"
    assert str(ver2) == "1.0.0"


def test_version_and_version_equality():
    ver0 = AsdfVersion("1.0.0")
    ver1 = AsdfVersion("1.0.0")

    assert ver0 is not ver1
    assert ver0 == ver1
    assert ver1 == ver0
    assert not (ver0 != ver1)
    assert not (ver1 != ver0)


def test_version_and_string_equality():
    version = AsdfVersion("1.0.0")
    string_ver = "1.0.0"

    assert version == string_ver
    assert string_ver == version
    assert not (version != string_ver)
    assert not (string_ver != version)


def test_version_and_tuple_equality():
    version = AsdfVersion("1.0.0")
    tuple_ver = (1, 0, 0)

    assert version == tuple_ver
    assert tuple_ver == version
    assert not (version != tuple_ver)
    assert not (tuple_ver != version)


def test_version_and_version_inequality():
    ver0 = AsdfVersion("1.0.0")
    ver1 = AsdfVersion("1.0.1")
    ver2 = AsdfVersion("1.1.0")
    ver3 = AsdfVersion("1.1.1")
    ver4 = AsdfVersion("2.0.0")
    ver5 = AsdfVersion("2.0.1")
    ver6 = AsdfVersion("2.1.0")
    ver7 = AsdfVersion("2.1.1")

    versions = [ver0, ver1, ver2, ver3, ver4, ver5, ver6, ver7]
    for x, y in combinations(versions, 2):
        assert not (x == y)
        assert x != y

    assert ver0 < ver1 < ver2 < ver3 < ver4 < ver5 < ver6 < ver7
    assert ver7 > ver6 > ver5 > ver4 > ver3 > ver2 > ver1 > ver0
    assert (ver0 < ver1 < ver2 < ver4 < ver3 < ver5 < ver6 < ver7) is False
    assert (ver7 > ver6 > ver5 > ver3 > ver4 > ver2 > ver1 > ver0) is False

    assert ver0 <= ver1 <= ver2 <= ver3 <= ver4 <= ver5 <= ver6 <= ver7
    assert ver7 >= ver6 >= ver5 >= ver4 >= ver3 >= ver2 >= ver1 >= ver0


def test_version_and_string_inequality():
    version = AsdfVersion("2.0.0")

    assert version > "1.0.0"
    assert version > "1.0.1"
    assert version > "1.1.0"
    assert version > "1.1.1"
    assert (version > "2.0.0") is False
    assert (version < "2.0.0") is False
    assert version < "2.0.1"
    assert version < "2.1.0"
    assert version < "2.1.1"

    assert version >= "1.0.0"
    assert version >= "1.0.1"
    assert version >= "1.1.0"
    assert version >= "1.1.1"
    assert version >= "2.0.0"
    assert version <= "2.0.0"
    assert version <= "2.0.1"
    assert version <= "2.1.0"
    assert version <= "2.1.1"

    assert "1.0.0" < version
    assert "1.0.1" < version
    assert "1.1.0" < version
    assert "1.1.1" < version
    assert ("2.0.0" < version) is False
    assert ("2.0.0" > version) is False
    assert "2.0.1" > version
    assert "2.1.0" > version
    assert "2.1.1" > version

    assert "1.0.0" <= version
    assert "1.0.1" <= version
    assert "1.1.0" <= version
    assert "1.1.1" <= version
    assert "2.0.0" <= version
    assert "2.0.0" >= version
    assert "2.0.1" >= version
    assert "2.1.0" >= version
    assert "2.1.1" >= version


def test_version_and_tuple_inequality():
    version = AsdfVersion("2.0.0")

    assert version > (1, 0, 0)
    assert version > (1, 0, 1)
    assert version > (1, 1, 0)
    assert version > (1, 1, 1)
    assert (version > (2, 0, 0)) is False
    assert (version < (2, 0, 0)) is False
    assert version < (2, 0, 1)
    assert version < (2, 1, 0)
    assert version < (2, 1, 1)

    assert version >= (1, 0, 0)
    assert version >= (1, 0, 1)
    assert version >= (1, 1, 0)
    assert version >= (1, 1, 1)
    assert version >= (2, 0, 0)
    assert version <= (2, 0, 0)
    assert version <= (2, 0, 1)
    assert version <= (2, 1, 0)
    assert version <= (2, 1, 1)

    assert (1, 0, 0) < version
    assert (1, 0, 1) < version
    assert (1, 1, 0) < version
    assert (1, 1, 1) < version
    assert ((2, 0, 0) < version) is False
    assert ((2, 0, 0) > version) is False
    assert (2, 0, 1) > version
    assert (2, 1, 0) > version
    assert (2, 1, 1) > version

    assert (1, 0, 0) <= version
    assert (1, 0, 1) <= version
    assert (1, 1, 0) <= version
    assert (1, 1, 1) <= version
    assert (2, 0, 0) <= version
    assert (2, 0, 0) >= version
    assert (2, 0, 1) >= version
    assert (2, 1, 0) >= version
    assert (2, 1, 1) >= version
