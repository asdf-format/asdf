from pkg_resources import EntryPoint
import pkg_resources

import pytest

from asdf import entry_points
from asdf.exceptions import AsdfWarning
from asdf.extension import ExtensionProxy
from asdf.resource import ResourceMappingProxy
from asdf.version import version as asdf_package_version


@pytest.fixture
def mock_entry_points():
    return []


@pytest.fixture(autouse=True)
def monkeypatch_entry_points(monkeypatch, mock_entry_points):
    def _iter_entry_points(*, group):
        for candidate_group, name, func_name in mock_entry_points:
            if candidate_group == group:
                yield EntryPoint(
                    name, "asdf.tests.test_entry_points",
                    attrs=(func_name,),
                    dist=pkg_resources.get_distribution("asdf"),
                )

    monkeypatch.setattr(entry_points, "iter_entry_points", _iter_entry_points)


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
    mock_entry_points.append(("asdf.resource_mappings", "successful", "resource_mappings_entry_point_successful"))
    mappings = entry_points.get_resource_mappings()
    assert len(mappings) == 2
    for m in mappings:
        assert isinstance(m, ResourceMappingProxy)
        assert m.package_name == "asdf"
        assert m.package_version == asdf_package_version

    mock_entry_points.clear()
    mock_entry_points.append(("asdf.resource_mappings", "failing", "resource_mappings_entry_point_failing"))
    with pytest.warns(AsdfWarning, match="Exception: NOPE"):
        mappings = entry_points.get_resource_mappings()
    assert len(mappings) == 0

    mock_entry_points.clear()
    mock_entry_points.append(("asdf.resource_mappings", "bad_element", "resource_mappings_entry_point_bad_element"))
    with pytest.warns(AsdfWarning, match="TypeError: Resource mapping must implement the Mapping interface"):
        mappings = entry_points.get_resource_mappings()
    assert len(mappings) == 2


def extensions_entry_point_successful():
    class TestExtension:
        pass

    return [
        TestExtension(),
        TestExtension(),
    ]


def extensions_entry_point_failing():
    raise Exception("NOPE")


def extensions_entry_point_bad_element():
    class TestExtension:
        pass

    class BadApple:
        @property
        def __class__(self):
            raise Exception("NUH UH")

    return [
        TestExtension(),
        BadApple(),
        TestExtension(),
    ]


class LegacyExtension:
    pass


def test_get_extensions(mock_entry_points):
    mock_entry_points.append(("asdf.extensions", "successful", "extensions_entry_point_successful"))
    extensions = entry_points.get_extensions()
    assert len(extensions) == 2
    for e in extensions:
        assert isinstance(e, ExtensionProxy)
        assert e.package_name == "asdf"
        assert e.package_version == asdf_package_version
        assert e.legacy is False

    mock_entry_points.clear()
    mock_entry_points.append(("asdf_extensions", "legacy", "LegacyExtension"))
    extensions = entry_points.get_extensions()
    assert len(extensions) == 1
    for e in extensions:
        assert isinstance(e, ExtensionProxy)
        assert e.package_name == "asdf"
        assert e.package_version == asdf_package_version
        assert e.legacy is True

    mock_entry_points.clear()
    mock_entry_points.append(("asdf.extensions", "failing", "extensions_entry_point_failing"))
    with pytest.warns(AsdfWarning, match="Exception: NOPE"):
        extensions = entry_points.get_extensions()
    assert len(extensions) == 0

    mock_entry_points.clear()
    mock_entry_points.append(("asdf.extensions", "bad_element", "extensions_entry_point_bad_element"))
    with pytest.warns(AsdfWarning, match="Exception: NUH UH"):
        extensions = entry_points.get_extensions()
    assert len(extensions) == 2
