from itertools import combinations

import pytest

from asdf.extension._legacy import default_extensions
from asdf.schema import load_schema
from asdf.versioning import (
    AsdfSpec,
    AsdfVersion,
    asdf_standard_development_version,
    default_version,
    get_version_map,
    join_tag_version,
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
    assert not (ver0 != ver1)  # noqa: SIM202
    assert not (ver1 != ver0)  # noqa: SIM202


def test_version_and_string_equality():
    version = AsdfVersion("1.0.0")
    string_ver = "1.0.0"

    assert version == string_ver
    assert string_ver == version
    assert not (version != string_ver)  # noqa: SIM202
    assert not (string_ver != version)  # noqa: SIM202


def test_version_and_tuple_equality():
    version = AsdfVersion("1.0.0")
    tuple_ver = (1, 0, 0)

    assert version == tuple_ver
    assert tuple_ver == version
    assert not (version != tuple_ver)  # noqa: SIM202
    assert not (tuple_ver != version)  # noqa: SIM202


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
        assert not (x == y)  # noqa: SIM201
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

    assert "1.0.0" < version  # noqa: SIM300
    assert "1.0.1" < version  # noqa: SIM300
    assert "1.1.0" < version  # noqa: SIM300
    assert "1.1.1" < version  # noqa: SIM300
    assert ("2.0.0" < version) is False  # noqa: SIM300
    assert ("2.0.0" > version) is False  # noqa: SIM300
    assert "2.0.1" > version  # noqa: SIM300
    assert "2.1.0" > version  # noqa: SIM300
    assert "2.1.1" > version  # noqa: SIM300

    assert "1.0.0" <= version  # noqa: SIM300
    assert "1.0.1" <= version  # noqa: SIM300
    assert "1.1.0" <= version  # noqa: SIM300
    assert "1.1.1" <= version  # noqa: SIM300
    assert "2.0.0" <= version  # noqa: SIM300
    assert "2.0.0" >= version  # noqa: SIM300
    assert "2.0.1" >= version  # noqa: SIM300
    assert "2.1.0" >= version  # noqa: SIM300
    assert "2.1.1" >= version  # noqa: SIM300


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

    assert (1, 0, 0) < version  # noqa: SIM300
    assert (1, 0, 1) < version  # noqa: SIM300
    assert (1, 1, 0) < version  # noqa: SIM300
    assert (1, 1, 1) < version  # noqa: SIM300
    assert ((2, 0, 0) < version) is False  # noqa: SIM300
    assert ((2, 0, 0) > version) is False  # noqa: SIM300
    assert (2, 0, 1) > version  # noqa: SIM300
    assert (2, 1, 0) > version  # noqa: SIM300
    assert (2, 1, 1) > version  # noqa: SIM300

    assert (1, 0, 0) <= version  # noqa: SIM300
    assert (1, 0, 1) <= version  # noqa: SIM300
    assert (1, 1, 0) <= version  # noqa: SIM300
    assert (1, 1, 1) <= version  # noqa: SIM300
    assert (2, 0, 0) <= version  # noqa: SIM300
    assert (2, 0, 0) >= version  # noqa: SIM300
    assert (2, 0, 1) >= version  # noqa: SIM300
    assert (2, 1, 0) >= version  # noqa: SIM300
    assert (2, 1, 1) >= version  # noqa: SIM300


def test_spec_version_match():
    spec = AsdfSpec(">=1.1.0")

    assert spec.match(AsdfVersion("1.1.0"))
    assert spec.match(AsdfVersion("1.2.0"))
    assert not spec.match(AsdfVersion("1.0.0"))
    assert not spec.match(AsdfVersion("1.0.9"))


def test_spec_version_select():
    spec = AsdfSpec(">=1.1.0")

    versions = [AsdfVersion(x) for x in ["1.0.0", "1.0.9", "1.1.0", "1.2.0"]]
    assert spec.select(versions) == "1.2.0"
    assert spec.select(versions[:-1]) == "1.1.0"
    assert spec.select(versions[:-2]) is None


def test_spec_version_filter():
    spec = AsdfSpec(">=1.1.0")

    versions = [AsdfVersion(x) for x in ["1.0.0", "1.0.9", "1.1.0", "1.2.0"]]
    for x, y in zip(spec.filter(versions), ["1.1.0", "1.2.0"]):
        assert x == y


def test_spec_string_match():
    spec = AsdfSpec(">=1.1.0")

    assert spec.match("1.1.0")
    assert spec.match("1.2.0")
    assert not spec.match("1.0.0")
    assert not spec.match("1.0.9")


def test_spec_string_select():
    spec = AsdfSpec(">=1.1.0")

    versions = ["1.0.0", "1.0.9", "1.1.0", "1.2.0"]
    assert spec.select(versions) == "1.2.0"
    assert spec.select(versions[:-1]) == "1.1.0"
    assert spec.select(versions[:-2]) is None


def test_spec_string_filter():
    spec = AsdfSpec(">=1.1.0")

    versions = ["1.0.0", "1.0.9", "1.1.0", "1.2.0"]
    for x, y in zip(spec.filter(versions), ["1.1.0", "1.2.0"]):
        assert x == y


def test_spec_tuple_match():
    spec = AsdfSpec(">=1.1.0")

    assert spec.match((1, 1, 0))
    assert spec.match((1, 2, 0))
    assert not spec.match((1, 0, 0))
    assert not spec.match((1, 0, 9))


def test_spec_tuple_select():
    spec = AsdfSpec(">=1.1.0")

    versions = [(1, 0, 0), (1, 0, 9), (1, 1, 0), (1, 2, 0)]
    assert spec.select(versions) == "1.2.0"
    assert spec.select(versions[:-1]) == "1.1.0"
    assert spec.select(versions[:-2]) is None


def test_spec_tuple_filter():
    spec = AsdfSpec(">=1.1.0")

    versions = [(1, 0, 0), (1, 0, 9), (1, 1, 0), (1, 2, 0)]
    for x, y in zip(spec.filter(versions), ["1.1.0", "1.2.0"]):
        assert x == y


def test_spec_equal():
    """Make sure that equality means match"""
    spec = AsdfSpec(">=1.2.0")
    version0 = AsdfVersion("1.1.0")
    version1 = AsdfVersion("1.3.0")

    assert spec != version0
    assert version0 != spec
    assert spec == version1
    assert version1 == spec

    assert spec != "1.1.0"
    assert "1.1.0" != spec  # noqa: SIM300
    assert spec == "1.3.0"
    assert "1.3.0" == spec  # noqa: SIM300

    assert spec != (1, 1, 0)
    assert (1, 1, 0) != spec  # noqa: SIM300
    assert spec == (1, 3, 0)
    assert (1, 3, 0) == spec  # noqa: SIM300


def _standard_versioned_tags():
    versions = supported_versions
    schema_types = ["core", "standard"]
    for version in versions:
        vm = get_version_map(version)
        for schema_type in schema_types:
            for tag_base, tag_version in vm[schema_type].items():
                tag = join_tag_version(tag_base, tag_version)
                value = (str(version), schema_type, tag)
                yield value


@pytest.fixture()
def _xfail_version_map_support_cases(request):
    tag = request.getfixturevalue("tag")
    version = request.getfixturevalue("version")
    if (version, tag) in [
        ("1.6.0", "tag:stsci.edu:asdf/core/column-1.1.0"),
        ("1.6.0", "tag:stsci.edu:asdf/core/table-1.1.0"),
        ("1.6.0", "tag:stsci.edu:asdf/fits/fits-1.1.0"),
        ("1.6.0", "tag:stsci.edu:asdf/time/time-1.2.0"),
        ("1.6.0", "tag:stsci.edu:asdf/unit/defunit-1.1.0"),
        ("1.6.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.6.0", "tag:stsci.edu:asdf/unit/quantity-1.2.0"),
        ("1.6.0", "tag:stsci.edu:asdf/unit/unit-1.1.0"),
        ("1.5.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.4.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.4.0", "tag:stsci.edu:asdf/wcs/celestial_frame-1.1.0"),
        ("1.4.0", "tag:stsci.edu:asdf/wcs/composite_frame-1.1.0"),
        ("1.4.0", "tag:stsci.edu:asdf/wcs/icrs_coord-1.1.0"),
        ("1.4.0", "tag:stsci.edu:asdf/wcs/spectral_frame-1.1.0"),
        ("1.4.0", "tag:stsci.edu:asdf/wcs/step-1.2.0"),
        ("1.4.0", "tag:stsci.edu:asdf/wcs/wcs-1.2.0"),
        ("1.3.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.3.0", "tag:stsci.edu:asdf/wcs/celestial_frame-1.1.0"),
        ("1.3.0", "tag:stsci.edu:asdf/wcs/composite_frame-1.1.0"),
        ("1.3.0", "tag:stsci.edu:asdf/wcs/icrs_coord-1.1.0"),
        ("1.3.0", "tag:stsci.edu:asdf/wcs/spectral_frame-1.1.0"),
        ("1.3.0", "tag:stsci.edu:asdf/wcs/step-1.1.0"),
        ("1.3.0", "tag:stsci.edu:asdf/wcs/wcs-1.1.0"),
        ("1.2.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.2.0", "tag:stsci.edu:asdf/wcs/celestial_frame-1.1.0"),
        ("1.2.0", "tag:stsci.edu:asdf/wcs/composite_frame-1.1.0"),
        ("1.2.0", "tag:stsci.edu:asdf/wcs/icrs_coord-1.1.0"),
        ("1.2.0", "tag:stsci.edu:asdf/wcs/spectral_frame-1.1.0"),
        ("1.2.0", "tag:stsci.edu:asdf/wcs/step-1.1.0"),
        ("1.2.0", "tag:stsci.edu:asdf/wcs/wcs-1.1.0"),
        ("1.1.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.1.0", "tag:stsci.edu:asdf/wcs/celestial_frame-1.1.0"),
        ("1.1.0", "tag:stsci.edu:asdf/wcs/composite_frame-1.1.0"),
        ("1.1.0", "tag:stsci.edu:asdf/wcs/icrs_coord-1.1.0"),
        ("1.1.0", "tag:stsci.edu:asdf/wcs/spectral_frame-1.1.0"),
        ("1.1.0", "tag:stsci.edu:asdf/wcs/step-1.1.0"),
        ("1.1.0", "tag:stsci.edu:asdf/wcs/wcs-1.0.0"),
        ("1.0.0", "tag:stsci.edu:asdf/unit/defunit-1.0.0"),
        ("1.0.0", "tag:stsci.edu:asdf/wcs/celestial_frame-1.0.0"),
        ("1.0.0", "tag:stsci.edu:asdf/wcs/composite_frame-1.0.0"),
        ("1.0.0", "tag:stsci.edu:asdf/wcs/spectral_frame-1.0.0"),
        ("1.0.0", "tag:stsci.edu:asdf/wcs/step-1.0.0"),
        ("1.0.0", "tag:stsci.edu:asdf/wcs/wcs-1.0.0"),
    ]:
        request.node.add_marker(
            pytest.mark.xfail(reason="astropy does not yet explicitly support older schema versions", strict=True),
        )


@pytest.mark.parametrize(("version", "schema_type", "tag"), list(_standard_versioned_tags()))
@pytest.mark.usefixtures("_xfail_version_map_support_cases")
def test_version_map_support(version, schema_type, tag):
    type_index = default_extensions.extension_list.type_index

    class MockContext:
        def __init__(self):
            self._fname = None

        def _warn_tag_mismatch(self, *args, **kwargs):
            pass

    ctx = MockContext()

    try:
        load_schema(tag)
    except Exception as err:  # noqa: BLE001
        msg = (
            f"ASDF Standard version {version} requires support for "
            f"{tag}, but the corresponding schema cannot be loaded."
        )
        raise AssertionError(msg) from err

    extension_type = type_index.from_yaml_tag(ctx, tag)
    assert (
        extension_type is not None
    ), f"ASDF Standard version {version} requires support for {tag}, but no ExtensionType exists to support that tag."

    assert extension_type.yaml_tag == tag, (
        f"ASDF Standard version {version} requires support for "
        f"{tag}, but no ExtensionType exists that explicitly "
        "supports that version."
    )
