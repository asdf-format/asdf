import io
import os

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import asdf
from asdf import reference
from asdf.tags.core import ndarray

from ._helpers import assert_tree_match


def test_external_reference(tmp_path):
    exttree = {
        "cool_stuff": {"a": np.array([0, 1, 2], float), "b": np.array([3, 4, 5], float)},
        "list_of_stuff": ["foobar", 42, np.array([7, 8, 9], float)],
    }
    external_path = os.path.join(str(tmp_path), "external.asdf")
    ext = asdf.AsdfFile(exttree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ext.write_to(external_path, all_array_storage="internal")

    external_path = os.path.join(str(tmp_path), "external2.asdf")
    ff = asdf.AsdfFile(exttree)
    ff.write_to(external_path, all_array_storage="internal")

    tree = {
        # The special name "data" here must be an array.  This is
        # included so that such validation can be ignored when we just
        # have a "$ref".
        "data": {"$ref": "external.asdf#/cool_stuff/a"},
        "science_data": {"$ref": "external.asdf#/cool_stuff/a"},
        "science_data2": {"$ref": "external2.asdf#/cool_stuff/a"},
        "foobar": {
            "$ref": "external.asdf#/list_of_stuff/0",
        },
        "answer": {"$ref": "external.asdf#/list_of_stuff/1"},
        "array": {
            "$ref": "external.asdf#/list_of_stuff/2",
        },
        "whole_thing": {"$ref": "external.asdf#"},
        "myself": {
            "$ref": "#",
        },
        "internal": {"$ref": "#science_data"},
    }

    def do_asserts(ff):
        assert "unloaded" in repr(ff.tree["science_data"])
        assert "unloaded" in str(ff.tree["science_data"])
        assert len(ff._external_asdf_by_uri) == 0

        assert_array_equal(ff.tree["science_data"], exttree["cool_stuff"]["a"])
        assert len(ff._external_asdf_by_uri) == 1

        assert_array_equal(ff.tree["science_data2"], exttree["cool_stuff"]["a"])
        assert len(ff._external_asdf_by_uri) == 2

        assert ff.tree["foobar"]() == "foobar"
        assert ff.tree["answer"]() == 42
        assert_array_equal(ff.tree["array"], exttree["list_of_stuff"][2])

        assert_tree_match(ff.tree["whole_thing"](), exttree)

        assert_array_equal(ff.tree["whole_thing"]["cool_stuff"]["a"], exttree["cool_stuff"]["a"])

        assert_array_equal(ff.tree["myself"]["science_data"], exttree["cool_stuff"]["a"])
        # Make sure that referencing oneself doesn't make another call
        # to disk.
        assert len(ff._external_asdf_by_uri) == 2

        assert_array_equal(ff.tree["internal"], exttree["cool_stuff"]["a"])

    with asdf.AsdfFile({}, uri=(tmp_path / "main.asdf").as_uri()) as ff:
        ff.tree = tree
        ff.find_references()
        do_asserts(ff)

        internal_path = os.path.join(str(tmp_path), "main.asdf")
        ff.write_to(internal_path)

    with asdf.open(internal_path) as ff:
        ff.find_references()
        do_asserts(ff)

    with asdf.open(internal_path) as ff:
        ff.find_references()
        assert len(ff._external_asdf_by_uri) == 0
        ff.resolve_references()
        assert len(ff._external_asdf_by_uri) == 2

        assert isinstance(ff.tree["data"], ndarray.NDArrayType)
        assert isinstance(ff.tree["science_data"], ndarray.NDArrayType)

        assert_array_equal(ff.tree["science_data"], exttree["cool_stuff"]["a"])
        assert_array_equal(ff.tree["science_data2"], exttree["cool_stuff"]["a"])

        assert ff.tree["foobar"] == "foobar"
        assert ff.tree["answer"] == 42
        assert_array_equal(ff.tree["array"], exttree["list_of_stuff"][2])

        assert_tree_match(ff.tree["whole_thing"], exttree)

        assert_array_equal(ff.tree["whole_thing"]["cool_stuff"]["a"], exttree["cool_stuff"]["a"])

        assert_array_equal(ff.tree["myself"]["science_data"], exttree["cool_stuff"]["a"])

        assert_array_equal(ff.tree["internal"], exttree["cool_stuff"]["a"])


@pytest.mark.remote_data()
def test_external_reference_invalid(tmp_path):
    tree = {"foo": {"$ref": "fail.asdf"}}

    ff = asdf.AsdfFile()
    ff.tree = tree
    ff.find_references()
    with pytest.raises(ValueError, match=r"Resolved to relative URL"):
        ff.resolve_references()

    ff = asdf.AsdfFile({}, uri="http://httpstat.us/404")
    ff.tree = tree
    ff.find_references()
    msg = r"[HTTP Error 404: Not Found, HTTP Error 502: Bad Gateway]"  # if httpstat.us is down 502 is returned.
    with pytest.raises(IOError, match=msg):
        ff.resolve_references()

    ff = asdf.AsdfFile({}, uri=(tmp_path / "main.asdf").as_uri())
    ff.tree = tree
    ff.find_references()
    with pytest.raises(IOError, match=r"No such file or directory: .*"):
        ff.resolve_references()


def test_external_reference_invalid_fragment(tmp_path):
    exttree = {"list_of_stuff": ["foobar", 42, np.array([7, 8, 9], float)]}
    external_path = os.path.join(str(tmp_path), "external.asdf")
    ff = asdf.AsdfFile(exttree)
    ff.write_to(external_path)

    tree = {"foo": {"$ref": "external.asdf#/list_of_stuff/a"}}

    with asdf.AsdfFile({}, uri=(tmp_path / "main.asdf").as_uri()) as ff:
        ff.tree = tree
        ff.find_references()
        with pytest.raises(ValueError, match=r"Unresolvable reference: .*"):
            ff.resolve_references()

    tree = {"foo": {"$ref": "external.asdf#/list_of_stuff/3"}}

    with asdf.AsdfFile({}, uri=(tmp_path / "main.asdf").as_uri()) as ff:
        ff.tree = tree
        ff.find_references()
        with pytest.raises(ValueError, match=r"Unresolvable reference: .*"):
            ff.resolve_references()


def test_make_reference(tmp_path):
    exttree = {
        # Include some ~ and / in the name to make sure that escaping
        # is working correctly
        "f~o~o/": {"a": np.array([0, 1, 2], float), "b": np.array([3, 4, 5], float)},
    }
    external_path = os.path.join(str(tmp_path), "external.asdf")
    ext = asdf.AsdfFile(exttree)
    ext.write_to(external_path)

    with asdf.open(external_path) as ext:
        ff = asdf.AsdfFile()
        ff.tree["ref"] = ext.make_reference(["f~o~o/", "a"])
        assert_array_equal(ff.tree["ref"], ext.tree["f~o~o/"]["a"])

        ff.write_to(os.path.join(str(tmp_path), "source.asdf"))

    with (asdf.open(os.path.join(str(tmp_path), "source.asdf")) as ff,):
        ff.find_references()
        assert ff.tree["ref"]._uri == "external.asdf#f~0o~0o~1/a"


def test_internal_reference(tmp_path):
    testfile = tmp_path / "test.asdf"

    tree = {"foo": 2, "bar": {"$ref": "#"}}

    ff = asdf.AsdfFile(tree)
    ff.find_references()
    assert isinstance(ff.tree["bar"], reference.Reference)
    ff.resolve_references()
    assert ff.tree["bar"]["foo"] == 2

    tree = {"foo": 2}
    ff = asdf.AsdfFile(tree, uri=testfile.as_uri())
    ff.tree["bar"] = ff.make_reference([])
    buff = io.BytesIO()
    ff.write_to(buff)
    buff.seek(0)
    ff = asdf.AsdfFile()
    assert b"{$ref: ''}" in buff.getvalue()


def test_implicit_internal_reference(tmp_path, with_lazy_tree):
    target = {"foo": "bar"}
    nested_in_dict = {"target": target}
    nested_in_list = [target]
    tree = {"target": target, "nested_in_dict": nested_in_dict, "nested_in_list": nested_in_list}

    assert tree["target"] is tree["nested_in_dict"]["target"]
    assert tree["target"] is tree["nested_in_list"][0]

    af = asdf.AsdfFile(tree)

    assert af["target"] is af["nested_in_dict"]["target"]
    assert af["target"] is af["nested_in_list"][0]

    output_path = os.path.join(str(tmp_path), "test.asdf")
    af.write_to(output_path)
    with asdf.open(output_path) as af:
        assert af["target"] is af["nested_in_dict"]["target"]
        assert af["target"] is af["nested_in_list"][0]
