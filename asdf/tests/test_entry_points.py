import unittest.mock as mk

import pytest

try:
    import importlib.metadata as metadata
except ImportError:
    import importlib_metadata as metadata

from asdf import entry_points
from asdf._version import version as asdf_package_version
from asdf.exceptions import AsdfWarning
from asdf.extension import ExtensionProxy
from asdf.resource import ResourceMappingProxy


@pytest.fixture
def mock_entry_points():
    return []


@pytest.fixture(autouse=True)
def monkeypatch_entry_points(monkeypatch, mock_entry_points):
    def _entry_points():
        points = mk.MagicMock()

        def _get(group, default):
            points = []
            for candidate_group, name, func_name in mock_entry_points:
                if candidate_group == group:
                    point = metadata.EntryPoint(name=name, group="asdf.tests.test_entry_points", value=func_name)
                    point.dist = metadata.distribution("asdf")
                    points.append(point)

            if len(points) > 0:
                return points
            else:
                return default

        points.get = _get

        return points

    monkeypatch.setattr(entry_points, "entry_points", _entry_points)


def resource_mappings_entry_point_successful():
    return [
        {"http://somewhere.org/schemas/foo-1.0.0": b"foo"},
        {"http://somewhere.org/schemas/bar-1.0.0": b"bar"},
    ]


def resource_mappings_entry_point_failing():
    raise Exception("NOPE")


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
            "asdf.tests.test_entry_points:resource_mappings_entry_point_successful",
        )
    )
    mappings = entry_points.get_resource_mappings()
    assert len(mappings) == 2
    for m in mappings:
        assert isinstance(m, ResourceMappingProxy)
        assert m.package_name == "asdf"
        assert m.package_version == asdf_package_version

    mock_entry_points.clear()
    mock_entry_points.append(
        ("asdf.resource_mappings", "failing", "asdf.tests.test_entry_points:resource_mappings_entry_point_failing")
    )
    with pytest.warns(AsdfWarning, match="Exception: NOPE"):
        mappings = entry_points.get_resource_mappings()
    assert len(mappings) == 0

    mock_entry_points.clear()
    mock_entry_points.append(
        (
            "asdf.resource_mappings",
            "bad_element",
            "asdf.tests.test_entry_points:resource_mappings_entry_point_bad_element",
        )
    )
    with pytest.warns(AsdfWarning, match="TypeError: Resource mapping must implement the Mapping interface"):
        mappings = entry_points.get_resource_mappings()
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
    raise Exception("NOPE")


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
        ("asdf.extensions", "successful", "asdf.tests.test_entry_points:extensions_entry_point_successful")
    )
    extensions = entry_points.get_extensions()
    assert len(extensions) == 2
    for e in extensions:
        assert isinstance(e, ExtensionProxy)
        assert e.package_name == "asdf"
        assert e.package_version == asdf_package_version

    mock_entry_points.clear()
    mock_entry_points.append(
        ("asdf.extensions", "failing", "asdf.tests.test_entry_points:extensions_entry_point_failing")
    )
    with pytest.warns(AsdfWarning, match="Exception: NOPE"):
        extensions = entry_points.get_extensions()
    assert len(extensions) == 0

    mock_entry_points.clear()
    mock_entry_points.append(
        ("asdf.extensions", "bad_element", "asdf.tests.test_entry_points:extensions_entry_point_bad_element")
    )
    with pytest.warns(
        AsdfWarning, match="TypeError: Extension must implement the Extension or AsdfExtension interface"
    ):
        extensions = entry_points.get_extensions()
    assert len(extensions) == 2

    mock_entry_points.clear()
    mock_entry_points.append(("asdf_extensions", "legacy", "asdf.tests.test_entry_points:LegacyExtension"))
    extensions = entry_points.get_extensions()
    assert len(extensions) == 1
    for e in extensions:
        assert isinstance(e, ExtensionProxy)
        assert e.package_name == "asdf"
        assert e.package_version == asdf_package_version
        assert e.legacy is True

    mock_entry_points.clear()
    mock_entry_points.append(("asdf_extensions", "failing", "asdf.tests.test_entry_points:FauxLegacyExtension"))
    with pytest.warns(AsdfWarning, match="TypeError"):
        extensions = entry_points.get_extensions()
    assert len(extensions) == 0
