import contextlib
import io
import os
import re
import sys

import numpy as np
import pytest
import yaml
from numpy import ma
from numpy.testing import assert_array_equal

import asdf
from asdf.exceptions import ValidationError
from asdf.extension import Converter, Extension, TagDefinition
from asdf.tags.core import ndarray
from asdf.testing import helpers


# These custom types and the custom extension are here purely for the purpose
# of testing NDArray objects and making sure that they can be validated as part
# of a nested hierarchy, and not just top-level objects.
class CustomData:
    def __init__(self, value):
        self.value = value


class CustomNDim:
    def __init__(self, value):
        self.value = value


class CustomNDimConverter(Converter):
    tags = ["tag:nowhere.org:custom/ndim-1.0.0"]
    types = [CustomNDim]

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.value

    def from_yaml_tree(self, node, tag, ctx):
        return CustomNDim(node)


class CustomDataConverter(Converter):
    tags = ["tag:nowhere.org:custom/datatype-1.0.0"]
    types = [CustomData]

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.value

    def from_yaml_tree(self, node, tag, ctx):
        return CustomData(node)


class CustomExtension(Extension):
    tags = [
        TagDefinition(
            tag_uri="tag:nowhere.org:custom/datatype-1.0.0",
            schema_uris=["http://nowhere.org/schemas/custom/datatype-1.0.0"],
        ),
        TagDefinition(
            tag_uri="tag:nowhere.org:custom/ndim-1.0.0",
            schema_uris=["http://nowhere.org/schemas/custom/ndim-1.0.0"],
        ),
    ]
    extension_uri = "asdf://nowhere.org/extensions/custom-1.0.0"
    converters = [CustomDataConverter(), CustomNDimConverter()]


@contextlib.contextmanager
def with_custom_extension():
    with asdf.config_context() as cfg:
        cfg.add_extension(CustomExtension())
        cfg.add_resource_mapping(
            {
                "http://nowhere.org/schemas/custom/datatype-1.0.0": """%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.1.0"
id: "http://nowhere.org/schemas/custom/datatype-1.0.0"
type: object
properties:
  a:
    datatype: float32

  b:
    datatype: float32
    exact_datatype: true

  c:
    datatype:
      - name: a
        datatype: int16
      - name: b
        datatype: ['ascii', 16]

  d:
    datatype:
      - name: a
        datatype: int16
      - name: b
        datatype: ['ascii', 16]
    exact_datatype: true
  e:
    anyOf:
      - type: "null"
      - datatype: int16""",
                "http://nowhere.org/schemas/custom/ndim-1.0.0": """%YAML 1.1
---
$schema: "http://stsci.edu/schemas/asdf/asdf-schema-1.1.0"
id: "http://nowhere.org/schemas/custom/ndim-1.0.0"
type: object
properties:
  a:
    ndim: 2

  b:
    max_ndim: 2""",
            }
        )
        yield


@contextlib.contextmanager
def roundtrip(af, raw=False, standard_version=None):
    if not isinstance(af, asdf.AsdfFile):
        af = asdf.AsdfFile(af, version=standard_version)
    b = io.BytesIO()
    af.write_to(b)
    b.seek(0)
    if raw:
        bs = b.read()
        if asdf.constants.BLOCK_MAGIC in bs:
            bs, *_ = bs.split(asdf.constants.BLOCK_MAGIC)
        yield bs
    else:
        with asdf.open(b) as af:
            yield af


def test_sharing():
    x = np.arange(0, 10, dtype=float)
    tree = {"science_data": x, "subset": x[3:-3], "skipping": x[::2]}

    with roundtrip(tree) as af:
        tree = af.tree
        assert_array_equal(tree["science_data"], x)
        assert_array_equal(tree["subset"], x[3:-3])
        assert_array_equal(tree["skipping"], x[::2])

        assert tree["science_data"].ctypes.data == tree["skipping"].ctypes.data

        assert len(af._blocks.blocks) == 1
        assert af._blocks.blocks[0].header["data_size"] == 80

        tree["science_data"][0] = 42
        assert tree["skipping"][0] == 42


def test_byteorder(tmp_path):
    tree = {
        "bigendian": np.arange(0, 10, dtype=">f8"),
        "little": np.arange(0, 10, dtype="<f8"),
    }

    with roundtrip(tree) as af:
        my_tree = af.tree
        for endian in ("bigendian", "little"):
            assert my_tree[endian].dtype == tree[endian].dtype

        if sys.byteorder == "little":
            assert my_tree["bigendian"].dtype.byteorder == ">"
            assert my_tree["little"].dtype.byteorder == "="
        else:
            assert my_tree["bigendian"].dtype.byteorder == "="
            assert my_tree["little"].dtype.byteorder == "<"


@pytest.mark.parametrize("dtype", ndarray._datatype_names.values())
def test_all_dtypes(dtype):
    standard_version = "1.6.0" if dtype == "f2" else None
    tree = {}
    for byteorder in (">", "<"):
        arr = np.array([True, False]) if dtype == "b1" else np.arange(0, 10, dtype=str(byteorder + dtype))
        tree[byteorder + dtype] = arr
    with roundtrip(tree, standard_version=standard_version) as af:
        for k in tree:
            pre = tree[k]
            post = af[k]
            assert_array_equal(pre, post)


def test_dont_load_data():
    x = np.arange(0, 10, dtype=float)
    tree = {"science_data": x, "subset": x[3:-3], "skipping": x[::2]}
    ff = asdf.AsdfFile(tree)

    buff = io.BytesIO()
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff) as ff:
        # repr and str shouldn't load data
        str(ff.tree["science_data"])
        repr(ff.tree)

        for block in ff._blocks.blocks:
            assert callable(block._data)


def test_table_inline(tmp_path):
    table = np.array(
        [(0, 1, (2, 3)), (4, 5, (6, 7))],
        dtype=[("MINE", np.int8), ("", np.float64), ("arr", ">i4", (2,))],
    )

    tree = {"table_data": table}

    with asdf.config_context() as config:
        config.array_inline_threshold = 100

        with roundtrip(tree) as af:
            assert table.dtype.names == af["table_data"].dtype.names
            for n in table.dtype.names:
                assert_array_equal(table[n], af["table_data"][n])

        with roundtrip(tree, raw=True) as content:
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


def test_array_inline_threshold_recursive(tmp_path):
    """
    Test that setting the inline threshold works for objects
    that contain (and when serialized produce a ndarray)
    """

    class NDArrayContainer:
        def __init__(self, array):
            self._array = array

        @property
        def array(self):
            return np.array(self._array)

    class NDArrayContainerConverter:
        tags = ["http://somewhere.org/tags/foo-1.0.0"]
        types = [NDArrayContainer]

        def to_yaml_tree(self, obj, tag, ctx):
            return {"array": obj.array}

        def from_yaml_tree(self, node, tag, ctx):
            return NDArrayContainer(node["array"])

    class NDArrayContainerExtension:
        tags = NDArrayContainerConverter.tags
        converters = [NDArrayContainerConverter()]
        extension_uri = "http://somewhere.org/extensions/foo-1.0.0"

    container = NDArrayContainer([[1, 2], [3, 4]])
    tree = {"test": container}

    with asdf.config_context() as config:
        config.add_extension(NDArrayContainerExtension())
        config.array_inline_threshold = 100
        # we can no longer use _helpers.assert_roundtrip_tree here because
        # the model no longer has a CustomType which results in equality testing
        # using == which will fail
        # this test appears to be designed to test the inline threshold so we can
        # just look at the number of blocks
        fn = str(tmp_path / "test.asdf")
        af = asdf.AsdfFile(tree)
        af.write_to(fn)
        with asdf.open(fn) as af:
            assert len(list(af._blocks.blocks)) == 0


def test_copy_inline():
    yaml = """
x0: !core/ndarray-1.1.0
  data: [-1.0, 1.0]
    """

    buff = helpers.yaml_to_asdf(yaml)

    with asdf.open(buff) as infile, asdf.AsdfFile() as f:
        f.tree["a"] = infile.tree["x0"]
        f.tree["b"] = f.tree["a"]
        f.write_to(io.BytesIO())


def test_table(tmp_path):
    table = np.array([(0, 1, (2, 3)), (4, 5, (6, 7))], dtype=[("MINE", np.int8), ("", "<f8"), ("arr", ">i4", (2,))])

    tree = {"table_data": table}

    with roundtrip(tree) as af:
        assert_array_equal(af["table_data"], table)

    with roundtrip(tree, raw=True) as content:
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


def test_table_nested_fields(tmp_path):
    table = np.array(
        [(0, (1, 2)), (4, (5, 6)), (7, (8, 9))],
        dtype=[("A", "<i8"), ("B", [("C", "<i8"), ("D", "<i8")])],
    )

    tree = {"table_data": table}

    with roundtrip(tree) as af:
        assert_array_equal(af["table_data"], table)

    with roundtrip(tree, raw=True) as content:
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


def test_inline():
    x = np.arange(0, 10, dtype=float)
    tree = {"science_data": x, "subset": x[3:-3], "skipping": x[::2]}

    buff = io.BytesIO()

    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(x, "inline")
    ff.write_to(buff)

    buff.seek(0)
    with asdf.open(buff, mode="rw") as ff:
        for k in tree:
            assert_array_equal(tree[k], ff.tree[k])
        assert len(list(ff._blocks.blocks)) == 0
        buff = io.BytesIO()
        ff.write_to(buff)

    assert b"[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]" in buff.getvalue()


def test_inline_bare():
    content = "arr: !core/ndarray-1.1.0 [[1, 2, 3, 4], [5, 6, 7, 8]]"
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"], [[1, 2, 3, 4], [5, 6, 7, 8]])


@pytest.mark.parametrize(
    "mask",
    [
        [[False, False, True], [False, True, False], [False, False, False]],
        True,
        False,
    ],
)
def test_mask_roundtrip(mask, tmp_path):
    array = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]])
    tree = {
        "unmasked": array,
        "masked": np.ma.array(array, mask=mask),
    }

    with roundtrip(tree) as af:
        # assert_array_equal ignores the mask, so use equality here
        assert (tree["masked"].data == af["masked"].data).all()
        assert (tree["masked"].mask == af["masked"].mask).all()
        # ensure tree validity
        assert (af["unmasked"] == af["masked"].data).all()
        assert len(af._blocks.blocks) == 2


def test_len_roundtrip(tmp_path):
    sequence = np.arange(0, 10, dtype=int)
    tree = {"sequence": sequence}

    with roundtrip(tree) as af:
        s = af.tree["sequence"]
        assert len(s) == 10


def test_mask_arbitrary():
    content = """
arr: !core/ndarray-1.1.0
  data: [[1, 2, 3, 1234], [5, 6, 7, 8]]
  mask: 1234
    """

    buff = helpers.yaml_to_asdf(content)
    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"].mask, [[False, False, False, True], [False, False, False, False]])


def test_mask_nan():
    content = """
arr: !core/ndarray-1.1.0
  data: [[1, 2, 3, .NaN], [5, 6, 7, 8]]
  mask: .NaN
    """

    buff = helpers.yaml_to_asdf(content)
    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"].mask, [[False, False, False, True], [False, False, False, False]])


def test_string(tmp_path):
    tree = {
        "ascii": np.array([b"foo", b"bar", b"baz"]),
        "unicode": np.array(["სამეცნიერო", "данные", "வடிவம்"]),
    }

    with roundtrip(tree) as af:
        for k in tree:
            assert_array_equal(tree[k], af[k])


def test_string_table(tmp_path):
    tree = {"table": np.array([(b"foo", "სამეცნიერო", "42", "53.0")])}

    with roundtrip(tree) as af:
        for k in tree:
            assert_array_equal(tree[k], af[k])


def test_inline_string():
    content = "arr: !core/ndarray-1.1.0 ['a', 'b', 'c']"
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff) as ff:
        assert_array_equal(ff.tree["arr"]._make_array(), ["a", "b", "c"])


def test_inline_structured():
    content = """
arr: !core/ndarray-1.1.0
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


def test_unicode_to_list(tmp_path):
    arr = np.array(["", "𐀠"], dtype="<U")
    tree = {"unicode": arr}

    fd = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(arr, "inline")
    ff.write_to(fd)
    fd.seek(0)

    with asdf.open(fd) as ff:
        ff.resolve_references()
        ff.write_to(io.BytesIO(), all_array_storage="inline")


def test_inline_masked_array(tmp_path):
    testfile = os.path.join(str(tmp_path), "masked.asdf")

    tree = {"test": ma.array([1, 2, 3], mask=[0, 1, 0])}

    f = asdf.AsdfFile(tree)
    f.set_array_storage(tree["test"], "inline")
    f.write_to(testfile)

    with asdf.open(testfile) as f2:
        assert len(list(f2._blocks.blocks)) == 0
        # assert_array_equal ignores the mask, so use equality here
        assert (f.tree["test"] == f2.tree["test"]).all()

    with open(testfile, "rb") as fd:
        assert b"null" in fd.read()


def test_masked_array_stay_open_bug(tmp_path):
    psutil = pytest.importorskip("psutil")

    tmppath = os.path.join(str(tmp_path), "masked.asdf")

    tree = {"test": np.ma.array([1, 2, 3], mask=[False, True, False])}

    f = asdf.AsdfFile(tree)
    f.write_to(tmppath)

    p = psutil.Process()
    orig_open = p.open_files()

    for _ in range(3):
        with asdf.open(tmppath) as f2:
            np.sum(f2.tree["test"])

    assert len(p.open_files()) <= len(orig_open)


def test_memmap_stay_open_bug(tmp_path):
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

    tmppath = os.path.join(str(tmp_path), "arr.asdf")

    tree = {"test": np.array([1, 2, 3])}

    f = asdf.AsdfFile(tree)
    f.write_to(tmppath)

    p = psutil.Process()
    orig_open = p.open_files()

    for _ in range(3):
        with open(tmppath, mode="rb") as fp, asdf.open(fp) as f2:
            np.sum(f2.tree["test"])

    assert len(p.open_files()) <= len(orig_open)


def test_masked_array_repr(tmp_path):
    tmppath = os.path.join(str(tmp_path), "masked.asdf")

    tree = {"array": np.arange(10), "masked": np.ma.array([1, 2, 3], mask=[False, True, False])}

    asdf.AsdfFile(tree).write_to(tmppath)

    with asdf.open(tmppath) as ff:
        assert "masked array" in repr(ff.tree["masked"])


def test_operations_on_ndarray_proxies(tmp_path):
    tmppath = os.path.join(str(tmp_path), "test.asdf")

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


def test_mask_datatype(tmp_path):
    content = """
arr: !core/ndarray-1.1.0
    data: [1, 2, 3]
    dtype: int32
    mask: !core/ndarray-1.1.0
        data: [true, true, false]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass


def test_invalid_mask_datatype(tmp_path):
    content = """
arr: !core/ndarray-1.1.0
    data: [1, 2, 3]
    dtype: int32
    mask: !core/ndarray-1.1.0
        data: ['a', 'b', 'c']
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r".* is not valid under any of the given schemas"),
        asdf.open(
            buff,
        ),
    ):
        pass


@with_custom_extension()
def test_ndim_validation(tmp_path):
    content = """
obj: !<tag:nowhere.org:custom/ndim-1.0.0>
    a: !core/ndarray-1.1.0
       data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Wrong number of dimensions:.*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/ndim-1.0.0>
    a: !core/ndarray-1.1.0
       data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/ndim-1.0.0>
    a: !core/ndarray-1.1.0
       shape: [1, 3]
       data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/ndim-1.0.0>
    b: !core/ndarray-1.1.0
       data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/ndim-1.0.0>
    b: !core/ndarray-1.1.0
       data: [[1, 2, 3]]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/ndim-1.0.0>
    b: !core/ndarray-1.1.0
       data: [[[1, 2, 3]]]
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Wrong number of dimensions:.*"),
        asdf.open(
            buff,
        ),
    ):
        pass


@with_custom_extension()
def test_datatype_validation(tmp_path):
    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    a: !core/ndarray-1.1.0
       data: [1, 2, 3]
       datatype: float32
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    a: !core/ndarray-1.1.0
       data: [1, 2, 3]
       datatype: float64
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Can not safely cast from .* to .*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    a: !core/ndarray-1.1.0
       data: [1, 2, 3]
       datatype: int16
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    b: !core/ndarray-1.1.0
       data: [1, 2, 3]
       datatype: int16
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Expected datatype .*, got .*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    a: !core/ndarray-1.1.0
       data: [[1, 'a'], [2, 'b'], [3, 'c']]
       datatype:
         - name: a
           datatype: int8
         - name: b
           datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Expected scalar datatype .*, got .*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    e: null
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass


@with_custom_extension()
def test_structured_datatype_validation(tmp_path):
    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    c: !core/ndarray-1.1.0
       data: [[1, 'a'], [2, 'b'], [3, 'c']]
       datatype:
         - name: a
           description: a description
           datatype: int8
         - name: b
           datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    c: !core/ndarray-1.1.0
       data: [[1, 'a'], [2, 'b'], [3, 'c']]
       datatype:
         - name: a
           datatype: int64
         - name: b
           title: a title
           datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Can not safely cast to expected datatype.*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    c: !core/ndarray-1.1.0
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

    with (
        pytest.raises(ValidationError, match=r"Mismatch in number of columns:.*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    c: !core/ndarray-1.1.0
       data: [1, 2, 3]
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Expected structured datatype.*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    d: !core/ndarray-1.1.0
       data: [[1, 'a'], [2, 'b'], [3, 'c']]
       datatype:
         - name: a
           datatype: int8
         - name: b
           datatype: ['ascii', 8]
    """
    buff = helpers.yaml_to_asdf(content)

    with (
        pytest.raises(ValidationError, match=r"Expected datatype .*, got .*"),
        asdf.open(
            buff,
        ),
    ):
        pass

    content = """
obj: !<tag:nowhere.org:custom/datatype-1.0.0>
    d: !core/ndarray-1.1.0
       data: [[1, 'a'], [2, 'b'], [3, 'c']]
       datatype:
         - name: a
           datatype: int16
         - name: b
           datatype: ['ascii', 16]
    """
    buff = helpers.yaml_to_asdf(content)

    with asdf.open(buff):
        pass


def test_string_inline():
    x = np.array([b"a", b"b", b"c"])
    line = ndarray.numpy_array_to_list(x)

    for entry in line:
        assert isinstance(entry, str)


def test_inline_shape_mismatch():
    content = """
arr: !core/ndarray-1.1.0
  data: [1, 2, 3]
  shape: [2]
    """

    buff = helpers.yaml_to_asdf(content)
    with pytest.raises(ValueError, match=r"inline data doesn't match the given shape"):
        with asdf.open(buff) as af:
            af["arr"]


def test_broadcasted_array(tmp_path):
    attrs = np.broadcast_arrays(np.array([10, 20]), np.array(10), np.array(10))
    tree = {"one": attrs[1]}  # , 'two': attrs[1], 'three': attrs[2]}
    with roundtrip(tree) as af:
        assert_array_equal(tree["one"], af["one"])


def test_broadcasted_offset_array(tmp_path):
    base = np.arange(10)
    offset = base[5:]
    broadcasted = np.broadcast_to(offset, (4, 5))
    tree = {"broadcasted": broadcasted}
    with roundtrip(tree) as af:
        assert_array_equal(tree["broadcasted"], af["broadcasted"])


def test_non_contiguous_base_array(tmp_path):
    base = np.arange(60).reshape(5, 4, 3).transpose(2, 0, 1) * 1
    contiguous = base.transpose(1, 2, 0)
    tree = {"contiguous": contiguous}
    with roundtrip(tree) as af:
        assert_array_equal(tree["contiguous"], af["contiguous"])


def test_fortran_order(tmp_path):
    array = np.array([[11, 12, 13], [21, 22, 23]], order="F", dtype=np.int64)
    tree = {"data": array}

    with roundtrip(tree) as af:
        assert af["data"].flags.fortran
        assert np.all(np.isclose(array, af["data"]))

    with roundtrip(tree, raw=True) as content:
        tree = yaml.safe_load(re.sub(rb"!core/\S+", b"", content))
        assert tree["data"]["strides"] == [8, 16]


def test_memmap_write(tmp_path):
    tmpfile = str(tmp_path / "data.asdf")
    tree = {"data": np.zeros(100)}

    with asdf.AsdfFile(tree, memmap=False) as af:
        # Make sure we're actually writing to an internal array for this test
        af.write_to(tmpfile, all_array_storage="internal")

    with asdf.open(tmpfile, mode="rw", memmap=True) as af:
        data = af["data"]
        assert data.flags.writeable is True
        data[0] = 42
        assert data[0] == 42

    with asdf.open(tmpfile, mode="rw", memmap=True) as af:
        assert af["data"][0] == 42

    with asdf.open(tmpfile, mode="r", memmap=True) as af:
        assert af["data"][0] == 42


def test_readonly(tmp_path):
    tmpfile = str(tmp_path / "data.asdf")
    tree = {"data": np.ndarray(100)}

    with asdf.AsdfFile(tree) as af:
        # Make sure we're actually writing to an internal array for this test
        af.write_to(tmpfile, all_array_storage="internal")

    # Opening in read mode (the default) should mean array is readonly
    with asdf.open(tmpfile, memmap=True) as af:
        assert af["data"].flags.writeable is False
        with pytest.raises(ValueError, match=r"assignment destination is read-only"):
            af["data"][0] = 41

    # Forcing memmap, the array should still be readonly
    with asdf.open(tmpfile, memmap=True) as af:
        assert af["data"].flags.writeable is False
        with pytest.raises(ValueError, match=r"assignment destination is read-only"):
            af["data"][0] = 41

    # This should be perfectly fine
    with asdf.open(tmpfile, mode="rw") as af:
        assert af["data"].flags.writeable is True
        af["data"][0] = 40

    # Copying the arrays makes it safe to write to the underlying array
    with asdf.open(tmpfile, mode="r", memmap=False) as af:
        assert af["data"].flags.writeable is True
        af["data"][0] = 42


def test_readonly_inline(tmp_path):
    tmpfile = str(tmp_path / "data.asdf")
    tree = {"data": np.ndarray(100)}

    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, all_array_storage="inline")

    # This should be safe since it's an inline array
    with asdf.open(tmpfile, mode="r") as af:
        assert af["data"].flags.writeable is True
        af["data"][0] = 42


# Confirm that NDArrayType's internal array is regenerated
# following an update.
@pytest.mark.parametrize("pad_blocks", [True, False])
def test_block_data_change(pad_blocks, tmp_path):
    tmpfile = str(tmp_path / "data.asdf")
    tree = {"data": np.zeros(10, dtype="uint8")}
    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile, pad_blocks=pad_blocks)

    with asdf.open(tmpfile, mode="rw", memmap=True) as af:
        assert np.all(af.tree["data"] == 0)
        array_before = af.tree["data"].__array__()
        af.tree["data"][:5] = 1
        af.update()
        array_after = af.tree["data"].__array__()
        assert array_before is not array_after
        assert np.all(af.tree["data"][:5] == 1)
        assert np.all(af.tree["data"][5:] == 0)


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

        with pytest.raises(AttributeError, match=r".* object has no attribute 'name'"):
            af["arr"].name

        with pytest.raises(AttributeError, match=r".* object has no attribute 'version'"):
            af["arr"].version


def test_shape_does_not_load_array(tmp_path):
    file_path = tmp_path / "test.asdf"
    with asdf.AsdfFile() as af:
        af["arr"] = np.arange(100)
        af.write_to(file_path)

    with asdf.open(file_path, lazy_load=True) as af:
        assert af["arr"]._array is None
        assert af["arr"].shape == (100,)
        assert af["arr"]._array is None


@pytest.mark.parametrize(
    "lazy_load, array_class",
    (
        (True, ndarray.NDArrayType),
        (False, np.ndarray),
    ),
)
@pytest.mark.parametrize("lazy_tree", [True, False])
def test_lazy_load_array_class(tmp_path, lazy_load, lazy_tree, array_class):
    file_path = tmp_path / "test.asdf"
    asdf.AsdfFile({"arr": np.arange(100)}).write_to(file_path)

    with asdf.open(file_path, lazy_load=lazy_load, lazy_tree=lazy_tree) as af:
        assert type(af["arr"]) is array_class
