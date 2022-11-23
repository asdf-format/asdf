import io
import os
import re
import sys

import jsonschema
import numpy as np
import pytest
import yaml
from numpy import ma
from numpy.testing import assert_array_equal

import asdf
from asdf import util
from asdf.tags.core import ndarray
from asdf.tests import CustomTestType, helpers

from . import data as test_data

TEST_DATA_PATH = helpers.get_test_data_path("", module=test_data)


# These custom types and the custom extension are here purely for the purpose
# of testing NDArray objects and making sure that they can be validated as part
# of a nested hierarchy, and not just top-level objects.
class CustomNdim(CustomTestType):
    name = "ndim"
    organization = "nowhere.org"
    standard = "custom"
    version = "1.0.0"


class CustomDatatype(CustomTestType):
    name = "datatype"
    organization = "nowhere.org"
    standard = "custom"
    version = "1.0.0"


class CustomExtension:
    @property
    def types(self):
        return [CustomNdim, CustomDatatype]

    @property
    def tag_mapping(self):
        return [("tag:nowhere.org:custom", "http://nowhere.org/schemas/custom{tag_suffix}")]

    @property
    def url_mapping(self):
        return [("http://nowhere.org/schemas/custom/", util.filepath_to_url(TEST_DATA_PATH) + "/{url_suffix}.yaml")]


def test_sharing(tmpdir):
    x = np.arange(0, 10, dtype=float)
    tree = {"science_data": x, "subset": x[3:-3], "skipping": x[::2]}

    def check_asdf(asdf):
        tree = asdf.tree

        assert_array_equal(tree["science_data"], x)
        assert_array_equal(tree["subset"], x[3:-3])
        assert_array_equal(tree["skipping"], x[::2])

        assert tree["science_data"].ctypes.data == tree["skipping"].ctypes.data

        assert len(list(asdf.blocks.internal_blocks)) == 1
        assert next(asdf.blocks.internal_blocks)._size == 80

        if "w" in asdf._mode:
            tree["science_data"][0] = 42
            assert tree["skipping"][0] == 42

    def check_raw_yaml(content):
        assert b"!core/ndarray" in content

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf, raw_yaml_check_func=check_raw_yaml)


def test_byteorder(tmpdir):
    tree = {
        "bigendian": np.arange(0, 10, dtype=">f8"),
        "little": np.arange(0, 10, dtype="<f8"),
    }

    def check_asdf(asdf):
        my_tree = asdf.tree
        for endian in ("bigendian", "little"):
            assert my_tree[endian].dtype == tree[endian].dtype

        if sys.byteorder == "little":
            assert my_tree["bigendian"].dtype.byteorder == ">"
            assert my_tree["little"].dtype.byteorder == "="
        else:
            assert my_tree["bigendian"].dtype.byteorder == "="
            assert my_tree["little"].dtype.byteorder == "<"

    def check_raw_yaml(content):
        assert b"byteorder: little" in content
        assert b"byteorder: big" in content

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf, raw_yaml_check_func=check_raw_yaml)


def test_all_dtypes(tmpdir):
    tree = {}
    for byteorder in (">", "<"):
        for dtype in ndarray._datatype_names.values():
            # Python 3 can't expose these dtypes in non-native byte
            # order, because it's using the new Python buffer
            # interface.
            if dtype in ("c32", "f16"):
                continue

            if dtype == "b1":
                arr = np.array([True, False])
            else:
                arr = np.arange(0, 10, dtype=str(byteorder + dtype))

            tree[byteorder + dtype] = arr

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_dont_load_data():
    x = np.arange(0, 10, dtype=float)
    tree = {"science_data": x, "subset": x[3:-3], "skipping": x[::2]}
    ff = asdf.AsdfFile(tree)

    buff = io.BytesIO()
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff) as ff:
        ff.run_hook("reserve_blocks")

        # repr and str shouldn't load data
        str(ff.tree["science_data"])
        repr(ff.tree)

        for block in ff.blocks.internal_blocks:
            assert block._data is None


def test_table_inline(tmpdir):
    table = np.array(
        [(0, 1, (2, 3)), (4, 5, (6, 7))],
        dtype=[("MINE", np.int8), ("", np.float64), ("arr", ">i4", (2,))],
    )

    tree = {"table_data": table}

    def check_raw_yaml(content):
        tree = yaml.safe_load(re.sub(rb"!core/\S+", b"", content))

        assert tree["table_data"] == {
            "datatype": [
                {"datatype": "int8", "name": "MINE"},
                {"datatype": "float64", "name": "f1"},
                {"datatype": "int32", "name": "arr", "shape": [2]},
            ],
            "data": [[0, 1.0, [2, 3]], [4, 5.0, [6, 7]]],
            "shape": [2],
        }

    with asdf.config_context() as config:
        config.array_inline_threshold = 100
        helpers.assert_roundtrip_tree(tree, tmpdir, raw_yaml_check_func=check_raw_yaml)


def test_array_inline_threshold_recursive(tmpdir):
    models = pytest.importorskip("astropy.modeling.models")

    aff = models.AffineTransformation2D(matrix=[[1, 2], [3, 4]])
    tree = {"test": aff}

    def check_asdf(asdf):
        assert len(list(asdf.blocks.internal_blocks)) == 0

    with asdf.config_context() as config:
        config.array_inline_threshold = 100
        helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf)


def test_copy_inline():
    yaml = """
x0: !core/ndarray-1.0.0
  data: [-1.0, 1.0]
    """

    buff = helpers.yaml_to_asdf(yaml)

    with asdf.open(buff) as infile:
        with asdf.AsdfFile() as f:
            f.tree["a"] = infile.tree["x0"]
            f.tree["b"] = f.tree["a"]
            f.write_to(io.BytesIO())


def test_table(tmpdir):
    table = np.array([(0, 1, (2, 3)), (4, 5, (6, 7))], dtype=[("MINE", np.int8), ("", "<f8"), ("arr", ">i4", (2,))])

    tree = {"table_data": table}

    def check_raw_yaml(content):
        tree = yaml.safe_load(re.sub(rb"!core/\S+", b"", content))

        assert tree["table_data"] == {
            "datatype": [
                {"byteorder": "big", "datatype": "int8", "name": "MINE"},
                {"byteorder": "little", "datatype": "float64", "name": "f1"},
                {"byteorder": "big", "datatype": "int32", "name": "arr", "shape": [2]},
            ],
            "shape": [2],
            "source": 0,
            "byteorder": "big",
        }

    helpers.assert_roundtrip_tree(tree, tmpdir, raw_yaml_check_func=check_raw_yaml)


def test_table_nested_fields(tmpdir):
    table = np.array(
        [(0, (1, 2)), (4, (5, 6)), (7, (8, 9))],
        dtype=[("A", "<i8"), ("B", [("C", "<i8"), ("D", "<i8")])],
    )

    tree = {"table_data": table}

    def check_raw_yaml(content):
        tree = yaml.safe_load(re.sub(rb"!core/\S+", b"", content))

        assert tree["table_data"] == {
            "datatype": [
                {"datatype": "int64", "name": "A", "byteorder": "little"},
                {
                    "datatype": [
                        {"datatype": "int64", "name": "C", "byteorder": "little"},
                        {"datatype": "int64", "name": "D", "byteorder": "little"},
                    ],
                    "name": "B",
                    "byteorder": "big",
                },
            ],
            "shape": [3],
            "source": 0,
            "byteorder": "big",
        }

    helpers.assert_roundtrip_tree(tree, tmpdir, raw_yaml_check_func=check_raw_yaml)


def test_inline():
    x = np.arange(0, 10, dtype=float)
    tree = {"science_data": x, "subset": x[3:-3], "skipping": x[::2]}

    buff = io.BytesIO()

    ff = asdf.AsdfFile(tree)
    ff.blocks.set_array_storage(ff.blocks[tree["science_data"]], "inline")
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff, mode="rw") as ff:
        helpers.assert_tree_match(tree, ff.tree)
        assert len(list(ff.blocks.internal_blocks)) == 0
        buff = io.BytesIO()
        ff.write_to(buff)

    assert b"[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]" in buff.getvalue()


def test_inline_bare():
    content = "arr: !core/ndarray-1.0.0 [[1, 2, 3, 4], [5, 6, 7, 8]]"
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"], [[1, 2, 3, 4], [5, 6, 7, 8]])


def test_mask_roundtrip(tmpdir):
    x = np.arange(0, 10, dtype=float)
    m = ma.array(x, mask=x > 5)
    tree = {"masked_array": m, "unmasked_array": x}

    def check_asdf(asdf):
        tree = asdf.tree

        m = tree["masked_array"]

        print(m)
        print(m.mask)
        assert np.all(m.mask[6:])
        assert len(asdf.blocks) == 2

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_asdf)


def test_len_roundtrip(tmpdir):
    sequence = np.arange(0, 10, dtype=int)
    tree = {"sequence": sequence}

    def check_len(asdf):
        s = asdf.tree["sequence"]
        assert len(s) == 10

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_len)


def test_mask_arbitrary():
    content = """
    arr: !core/ndarray-1.0.0
      data: [[1, 2, 3, 1234], [5, 6, 7, 8]]
      mask: 1234
    """

    buff = helpers.yaml_to_asdf(content)
    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"].mask, [[False, False, False, True], [False, False, False, False]])


def test_mask_nan():
    content = """
    arr: !core/ndarray-1.0.0
      data: [[1, 2, 3, .NaN], [5, 6, 7, 8]]
      mask: .NaN
    """

    buff = helpers.yaml_to_asdf(content)
    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"].mask, [[False, False, False, True], [False, False, False, False]])


def test_string(tmpdir):
    tree = {"ascii": np.array([b"foo", b"bar", b"baz"]), "unicode": np.array(["სამეცნიერო", "данные", "வடிவம்"])}

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_string_table(tmpdir):
    tree = {"table": np.array([(b"foo", "სამეცნიერო", "42", "53.0")])}

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_inline_string():
    content = "arr: !core/ndarray-1.0.0 ['a', 'b', 'c']"
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"]._make_array(), ["a", "b", "c"])


def test_inline_structured():
    content = """
    arr: !core/ndarray-1.0.0
        datatype: [['ascii', 4], uint16, uint16, ['ascii', 4]]
        data: [[M110, 110, 205, And],
               [ M31,  31, 224, And],
               [ M32,  32, 221, And],
               [M103, 103, 581, Cas]]"""

    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff) as ff:
        assert ff.tree["arr"]["f1"].dtype.char == "H"


def test_simple_table():
    table = np.array(
        [
            (10.683262825012207, 41.2674560546875, 0.13, 0.12, 213.916),
            (10.682777404785156, 41.270111083984375, 0.1, 0.09, 306.825),
            (10.684737205505371, 41.26903533935547, 0.08, 0.07, 96.656),
            (10.682382583618164, 41.26792526245117, 0.1, 0.09, 237.145),
            (10.686025619506836, 41.26922607421875, 0.13, 0.12, 79.581),
            (10.685656547546387, 41.26955032348633, 0.13, 0.12, 55.219),
            (10.684028625488281, 41.27090072631836, 0.13, 0.12, 345.269),
            (10.687610626220703, 41.270301818847656, 0.18, 0.14, 60.192),
        ],
        dtype=[
            ("ra", "<f4"),
            ("dec", "<f4"),
            ("err_maj", "<f8"),
            ("err_min", "<f8"),
            ("angle", "<f8"),
        ],
    )

    tree = {"table": table}
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(table, "inline")
    ff.write_to(io.BytesIO())


def test_unicode_to_list(tmpdir):
    arr = np.array(["", "𐀠"], dtype="<U")
    tree = {"unicode": arr}

    fd = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(arr, "inline")
    ff.write_to(fd)
    fd.seek(0)

    with asdf.open(fd) as ff:
        ff.resolve_and_inline()
        ff.write_to(io.BytesIO())


def test_inline_masked_array(tmpdir):
    testfile = os.path.join(str(tmpdir), "masked.asdf")

    tree = {"test": ma.array([1, 2, 3], mask=[0, 1, 0])}

    f = asdf.AsdfFile(tree)
    f.set_array_storage(tree["test"], "inline")
    f.write_to(testfile)

    with asdf.open(testfile) as f2:
        assert len(list(f2.blocks.internal_blocks)) == 0
        assert_array_equal(f.tree["test"], f2.tree["test"])

    with open(testfile, "rb") as fd:
        assert b"null" in fd.read()


def test_masked_array_stay_open_bug(tmpdir):
    psutil = pytest.importorskip("psutil")

    tmppath = os.path.join(str(tmpdir), "masked.asdf")

    tree = {"test": np.ma.array([1, 2, 3], mask=[False, True, False])}

    f = asdf.AsdfFile(tree)
    f.write_to(tmppath)

    p = psutil.Process()
    orig_open = p.open_files()

    for i in range(3):
        with asdf.open(tmppath) as f2:
            np.sum(f2.tree["test"])

    assert len(p.open_files()) <= len(orig_open)


def test_memmap_stay_open_bug(tmpdir):
    """
    Regression test for issue #1239
    memmapped arrays only closed at garbage collection when asdf.open given an open file

    When asdf.open is called with an already opened file
    it did not close any memmaps that it created (as the file
    pointer was still valid). These lingered until garbage collection
    and caused CI failures in astropy:
    https://github.com/astropy/astropy/pull/14035#issuecomment-1325236928
    """
    psutil = pytest.importorskip("psutil")

    tmppath = os.path.join(str(tmpdir), "arr.asdf")

    tree = {"test": np.array([1, 2, 3])}

    f = asdf.AsdfFile(tree)
    f.write_to(tmppath)

    p = psutil.Process()
    orig_open = p.open_files()

    for i in range(3):
        with open(tmppath, mode="rb") as fp:
            with asdf.open(fp) as f2:
                np.sum(f2.tree["test"])

    assert len(p.open_files()) <= len(orig_open)


def test_masked_array_repr(tmpdir):
    tmppath = os.path.join(str(tmpdir), "masked.asdf")

    tree = {"array": np.arange(10), "masked": np.ma.array([1, 2, 3], mask=[False, True, False])}

    asdf.AsdfFile(tree).write_to(tmppath)

    with asdf.open(tmppath) as ff:
        assert "masked array" in repr(ff.tree["masked"])


def test_operations_on_ndarray_proxies(tmpdir):
    tmppath = os.path.join(str(tmpdir), "test.asdf")

    tree = {"array": np.arange(10)}

    asdf.AsdfFile(tree).write_to(tmppath)

    with asdf.open(tmppath) as ff:
        x = ff.tree["array"] * 2
        assert_array_equal(x, np.arange(10) * 2)

    with asdf.open(tmppath) as ff:
        x = -ff.tree["array"]
        assert_array_equal(x, -np.arange(10))

    with asdf.open(tmppath, mode="rw") as ff:
        ff.tree["array"][2] = 4
        x = np.arange(10)
        x[2] = 4
        assert_array_equal(ff.tree["array"], x)


def test_mask_datatype(tmpdir):
    content = """
        arr: !core/ndarray-1.0.0
            data: [1, 2, 3]
            dtype: int32
            mask: !core/ndarray-1.0.0
                data: [true, true, false]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass


def test_invalid_mask_datatype(tmpdir):
    content = """
        arr: !core/ndarray-1.0.0
            data: [1, 2, 3]
            dtype: int32
            mask: !core/ndarray-1.0.0
                data: ['a', 'b', 'c']
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff):
            pass


def test_ndim_validation(tmpdir):
    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        a: !core/ndarray-1.0.0
           data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        a: !core/ndarray-1.0.0
           shape: [1, 3]
           data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        b: !core/ndarray-1.0.0
           data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        b: !core/ndarray-1.0.0
           data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/ndim-1.0.0>
        b: !core/ndarray-1.0.0
           data: [[[1, 2, 3]]]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass


def test_datatype_validation(tmpdir):
    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: float32
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: float64
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: int16
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        b: !core/ndarray-1.0.0
           data: [1, 2, 3]
           datatype: int16
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        a: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass


def test_structured_datatype_validation(tmpdir):
    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int64
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [[1, 'a', 0], [2, 'b', 1], [3, 'c', 2]]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
             - name: c
               datatype: float64
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        c: !core/ndarray-1.0.0
           data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        d: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int8
             - name: b
               datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with pytest.raises(jsonschema.ValidationError):
        with asdf.open(buff, extensions=CustomExtension()):
            pass

    content = """
    obj: !<tag:nowhere.org:custom/datatype-1.0.0>
        d: !core/ndarray-1.0.0
           data: [[1, 'a'], [2, 'b'], [3, 'c']]
           datatype:
             - name: a
               datatype: int16
             - name: b
               datatype: ['ascii', 16]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff, extensions=CustomExtension()):
        pass


def test_string_inline():
    x = np.array([b"a", b"b", b"c"])
    line = ndarray.numpy_array_to_list(x)

    for entry in line:
        assert isinstance(entry, str)


def test_inline_shape_mismatch():
    content = """
    arr: !core/ndarray-1.0.0
      data: [1, 2, 3]
      shape: [2]
    """

    buff = helpers.yaml_to_asdf(content)
    with pytest.raises(ValueError):
        with asdf.open(buff):
            pass


@pytest.mark.xfail(reason="NDArrays with dtype=object are not currently supported")
def test_simple_object_array(tmpdir):
    # See https://github.com/asdf-format/asdf/issues/383 for feature
    # request
    dictdata = np.empty((3, 3), dtype=object)
    for i, _ in enumerate(dictdata.flat):
        dictdata.flat[i] = {"foo": i * 42, "bar": i**2}

    helpers.assert_roundtrip_tree({"bizbaz": dictdata}, tmpdir)


@pytest.mark.xfail(reason="NDArrays with dtype=object are not currently supported")
def test_tagged_object_array(tmpdir):
    # See https://github.com/asdf-format/asdf/issues/383 for feature
    # request
    quantity = pytest.importorskip("astropy.units.quantity")

    objdata = np.empty((3, 3), dtype=object)
    for i, _ in enumerate(objdata.flat):
        objdata.flat[i] = quantity.Quantity(i, "angstrom")

    helpers.assert_roundtrip_tree({"bizbaz": objdata}, tmpdir)


def test_broadcasted_array(tmpdir):
    attrs = np.broadcast_arrays(np.array([10, 20]), np.array(10), np.array(10))
    tree = {"one": attrs[1]}  # , 'two': attrs[1], 'three': attrs[2]}
    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_broadcasted_offset_array(tmpdir):
    base = np.arange(10)
    offset = base[5:]
    broadcasted = np.broadcast_to(offset, (4, 5))
    tree = {"broadcasted": broadcasted}
    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_non_contiguous_base_array(tmpdir):
    base = np.arange(60).reshape(5, 4, 3).transpose(2, 0, 1) * 1
    contiguous = base.transpose(1, 2, 0)
    tree = {"contiguous": contiguous}
    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_fortran_order(tmpdir):
    array = np.array([[11, 12, 13], [21, 22, 23]], order="F", dtype=np.int64)
    tree = dict(data=array)

    def check_f_order(t):
        assert t["data"].flags.fortran
        assert np.all(np.isclose(array, t["data"]))

    def check_raw_yaml(content):
        tree = yaml.safe_load(re.sub(rb"!core/\S+", b"", content))
        assert tree["data"]["strides"] == [8, 16]

    helpers.assert_roundtrip_tree(tree, tmpdir, asdf_check_func=check_f_order, raw_yaml_check_func=check_raw_yaml)


def test_memmap_write(tmpdir):
    tmpfile = str(tmpdir.join("data.asdf"))
    tree = dict(data=np.zeros(100))

    with asdf.AsdfFile(tree) as af:
        # Make sure we're actually writing to an internal array for this test
        af.write_to(tmpfile, all_array_storage="internal")

    with asdf.open(tmpfile, mode="rw", copy_arrays=False) as af:
        data = af["data"]
        assert data.flags.writeable is True
        data[0] = 42
        assert data[0] == 42

    with asdf.open(tmpfile, mode="rw", copy_arrays=False) as af:
        assert af["data"][0] == 42

    with asdf.open(tmpfile, mode="r", copy_arrays=False) as af:
        assert af["data"][0] == 42


def test_readonly(tmpdir):

    tmpfile = str(tmpdir.join("data.asdf"))
    tree = dict(data=np.ndarray(100))

    with asdf.AsdfFile(tree) as af:
        # Make sure we're actually writing to an internal array for this test
        af.write_to(tmpfile, all_array_storage="internal")

    # Opening in read mode (the default) should mean array is readonly
    with asdf.open(tmpfile) as af:
        assert af["data"].flags.writeable is False
        with pytest.raises(ValueError) as err:
            af["data"][0] = 41
            assert str(err) == "assignment destination is read-only"

    # This should be perfectly fine
    with asdf.open(tmpfile, mode="rw") as af:
        assert af["data"].flags.writeable is True
        af["data"][0] = 40

    # Copying the arrays makes it safe to write to the underlying array
    with asdf.open(tmpfile, mode="r", copy_arrays=True) as af:
        assert af["data"].flags.writeable is True
        af["data"][0] = 42


def test_readonly_inline(tmpdir):
    tmpfile = str(tmpdir.join("data.asdf"))
    tree = dict(data=np.ndarray(100))

    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, all_array_storage="inline")

    # This should be safe since it's an inline array
    with asdf.open(tmpfile, mode="r") as af:
        assert af["data"].flags.writeable is True
        af["data"][0] = 42


# Confirm that NDArrayType's internal array is regenerated
# following an update.
def test_block_data_change(tmpdir):
    tmpfile = str(tmpdir.join("data.asdf"))
    tree = {"data": np.ndarray(10)}
    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile)

    with asdf.open(tmpfile, mode="rw") as af:
        array_before = af.tree["data"].__array__()
        af.update()
        array_after = af.tree["data"].__array__()
        assert array_before is not array_after


def test_problematic_class_attributes(tmp_path):
    """
    The presence of the "name" and "version" attributes
    in NDArrayType cause problems when our arrays are used
    with other libraries.

    See https://github.com/asdf-format/asdf/issues/1015
    """
    file_path = tmp_path / "test.asdf"
    with asdf.AsdfFile() as af:
        af["arr"] = np.arange(100)
        af.write_to(file_path)

    with asdf.open(file_path) as af:
        assert isinstance(af["arr"], ndarray.NDArrayType)

        with pytest.raises(AttributeError):
            af["arr"].name

        with pytest.raises(AttributeError):
            af["arr"].version
