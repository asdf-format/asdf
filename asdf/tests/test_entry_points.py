from pkg_resources import EntryPoint
import pkg_resources

import pytest

from asdf import entry_points
from asdf.exceptions import AsdfWarning


def resource_mappings_entry_point_one():
    return [
        {"http://somewhere.org/schemas/foo-1.0.0": b"foo"},
        {"http://somewhere.org/schemas/bar-1.0.0": b"bar"},
    ]


def resource_mappings_entry_point_two():
    return [
        {"http://somewhere.org/schemas/baz-1.0.0": b"baz"},
        {"http://somewhere.org/schemas/foz-1.0.0": b"foz"},
        object(),
    ]


def test_get_resource_mappings(monkeypatch):
    def iter_entry_points(*, group):
        if group == "asdf.resource_mappings":
            yield EntryPoint(
                "one", "asdf.tests.test_entry_points",
                attrs=("resource_mappings_entry_point_one",),
                dist=pkg_resources.get_distribution("asdf")
            )
            yield EntryPoint(
                "two", "asdf.tests.test_entry_points",
                attrs=("resource_mappings_entry_point_two",),
                dist=pkg_resources.get_distribution("asdf")
            )

    monkeypatch.setattr(entry_points, "iter_entry_points", iter_entry_points)

    with pytest.warns(AsdfWarning, match="is not an instance of Mapping"):
        mappings = entry_points.get_resource_mappings()

    assert len(mappings) == 4
