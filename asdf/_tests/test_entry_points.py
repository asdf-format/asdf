import sys

import pytest

from asdf import _entry_points
from asdf._version import version as asdf_package_version
from asdf.exceptions import AsdfWarning
from asdf.extension import ExtensionProxy
from asdf.resource import ResourceMappingProxy

# The standard library importlib.metadata returns duplicate entrypoints
# for all python versions up to and including 3.11
# https://github.com/python/importlib_metadata/issues/410#issuecomment-1304258228
# see PR https://github.com/asdf-format/asdf/pull/1260
# see issue https://github.com/asdf-format/asdf/issues/1254
if sys.version_info >= (3, 12):
    import importlib.metadata as metadata
else:
    import importlib_metadata as metadata


@pytest.fixture()
def mock_entry_points():
    return []


@pytest.fixture(autouse=True)
def _monkeypatch_entry_points(monkeypatch, mock_entry_points):
    def patched_entry_points(*, group):
        for candidate_group, name, func_name in mock_entry_points:
            if candidate_group == group:
                point = metadata.EntryPoint(name=name, group=group, value=func_name)
                vars(point).update(dist=metadata.distribution("asdf"))

                yield point

    monkeypatch.setattr(_entry_points, "entry_points", patched_entry_points)


def resource_mappings_entry_point_successful():
    return [
        {"http://somewhere.org/schemas/foo-1.0.0": b"foo"},
        {"http://somewhere.org/schemas/bar-1.0.0": b"bar"},
    ]


def resource_mappings_entry_point_failing():
    msg = "NOPE"
    raise Exception(msg)


def resource_mappings_entry_point_bad_element():
    return [
        {"http://somewhere.org/schemas/baz-1.0.0": b"baz"},
        object(),
        {"http://somewhere.org/schemas/foz-1.0.0": b"foz"},
    ]


def test_get_resource_mappings(mock_entry_points):
    mock_entry_points.append(
        (
            "asdf.resource_mappings",
            "successful",
            "asdf._tests.test_entry_points:resource_mappings_entry_point_successful",
        ),
    )
    mappings = _entry_points.get_resource_mappings()
    assert len(mappings) == 2
    for m in mappings:
        assert isinstance(m, ResourceMappingProxy)
        assert m.package_name == "asdf"
        assert m.package_version == asdf_package_version

    mock_entry_points.clear()
    mock_entry_points.append(
        ("asdf.resource_mappings", "failing", "asdf._tests.test_entry_points:resource_mappings_entry_point_failing"),
    )
    with pytest.warns(AsdfWarning, match=r"Exception: NOPE"):
        mappings = _entry_points.get_resource_mappings()
    assert len(mappings) == 0

    mock_entry_points.clear()
    mock_entry_points.append(
        (
            "asdf.resource_mappings",
            "bad_element",
            "asdf._tests.test_entry_points:resource_mappings_entry_point_bad_element",
        ),
    )
    with pytest.warns(AsdfWarning, match=r"TypeError: Resource mapping must implement the Mapping interface"):
        mappings = _entry_points.get_resource_mappings()
    assert len(mappings) == 2


class MinimumExtension:
    def __init__(self, extension_uri):
        self._extension_uri = extension_uri

    @property
    def extension_uri(self):
        return self._extension_uri


def extensions_entry_point_successful():
    return [
        MinimumExtension("http://somewhere.org/extensions/foo-1.0"),
        MinimumExtension("http://somewhere.org/extensions/bar-1.0"),
    ]


def extensions_entry_point_failing():
    msg = "NOPE"
    raise Exception(msg)


def extensions_entry_point_bad_element():
    return [
        MinimumExtension("http://somewhere.org/extensions/baz-1.0"),
        object(),
        MinimumExtension("http://somewhere.org/extensions/foz-1.0"),
    ]


class LegacyExtension:
    types = []
    tag_mapping = []
    url_mapping = []


class FauxLegacyExtension:
    pass


def test_get_extensions(mock_entry_points):
    mock_entry_points.append(
        ("asdf.extensions", "successful", "asdf._tests.test_entry_points:extensions_entry_point_successful"),
    )
    extensions = _entry_points.get_extensions()
    assert len(extensions) == 2
    for e in extensions:
        assert isinstance(e, ExtensionProxy)
        assert e.package_name == "asdf"
        assert e.package_version == asdf_package_version

    mock_entry_points.clear()
    mock_entry_points.append(
        ("asdf.extensions", "failing", "asdf._tests.test_entry_points:extensions_entry_point_failing"),
    )
    with pytest.warns(AsdfWarning, match=r"Exception: NOPE"):
        extensions = _entry_points.get_extensions()
    assert len(extensions) == 0

    mock_entry_points.clear()
    mock_entry_points.append(
        ("asdf.extensions", "bad_element", "asdf._tests.test_entry_points:extensions_entry_point_bad_element"),
    )
    with pytest.warns(
        AsdfWarning,
        match=r"TypeError: Extension must implement the Extension interface",
    ):
        extensions = _entry_points.get_extensions()
    assert len(extensions) == 2

    mock_entry_points.clear()
    mock_entry_points.append(("asdf_extensions", "legacy", "asdf._tests.test_entry_points:LegacyExtension"))
    extensions = _entry_points.get_extensions()
    assert len(extensions) == 0  # asdf_extensions is no longer supported

    mock_entry_points.clear()
    mock_entry_points.append(("asdf.extensions", "failing", "asdf._tests.test_entry_points:FauxLegacyExtension"))
    with pytest.warns(AsdfWarning, match=r"TypeError"):
        extensions = _entry_points.get_extensions()
    assert len(extensions) == 0
