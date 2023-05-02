import io
import os

import numpy as np
import pytest
from numpy.testing import assert_array_equal

import asdf
from asdf import Stream, generic_io


def test_stream():
    buff = io.BytesIO()

    tree = {"stream": Stream([6, 2], np.float64)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    for i in range(100):
        buff.write(np.array([i] * 12, np.float64).tobytes())

    buff.seek(0)

    with asdf.open(buff) as ff:
        assert len(ff._blocks.blocks) == 1
        assert ff.tree["stream"].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree["stream"]):
            assert np.all(row == i)


def test_stream_write_nothing():
    """
    Test that if you write nothing, you get a zero-length array
    """

    buff = io.BytesIO()

    tree = {"stream": Stream([6, 2], np.float64)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)

    buff.seek(0)

    with asdf.open(buff) as ff:
        assert len(ff._blocks.blocks) == 1
        assert ff.tree["stream"].shape == (0, 6, 2)


def test_stream_twice():
    """
    Test that if you write nothing, you get a zero-length array
    """

    buff = io.BytesIO()

    tree = {"stream": Stream([6, 2], np.uint8), "stream2": Stream([12, 2], np.uint8)}

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff)
    for i in range(100):
        buff.write(np.array([i] * 12, np.uint8).tobytes())

    buff.seek(0)

    ff = asdf.open(buff)
    assert len(ff._blocks.blocks) == 1
    assert ff.tree["stream"].shape == (100, 6, 2)
    assert ff.tree["stream2"].shape == (50, 12, 2)


def test_stream_with_nonstream():
    buff = io.BytesIO()

    tree = {"nonstream": np.array([1, 2, 3, 4], np.int64), "stream": Stream([6, 2], np.float64)}

    ff = asdf.AsdfFile(tree)
    # Since we're testing with small arrays, force this array to be stored in
    # an internal block rather than letting it be automatically put inline.
    ff.set_array_storage(ff["nonstream"], "internal")
    ff.write_to(buff)
    for i in range(100):
        buff.write(np.array([i] * 12, np.float64).tobytes())

    buff.seek(0)

    with asdf.open(buff) as ff:
        assert len(ff._blocks.blocks) == 2
        assert_array_equal(ff.tree["nonstream"], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree["stream"].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree["stream"]):
            assert np.all(row == i)


def test_stream_real_file(tmp_path):
    path = os.path.join(str(tmp_path), "test.asdf")

    tree = {"nonstream": np.array([1, 2, 3, 4], np.int64), "stream": Stream([6, 2], np.float64)}

    with open(path, "wb") as fd:
        ff = asdf.AsdfFile(tree)
        # Since we're testing with small arrays, force this array to be stored
        # in an internal block rather than letting it be automatically put
        # inline.
        ff.set_array_storage(ff["nonstream"], "internal")
        ff.write_to(fd)
        for i in range(100):
            fd.write(np.array([i] * 12, np.float64).tobytes())

    with asdf.open(path) as ff:
        assert len(ff._blocks.blocks) == 2
        assert_array_equal(ff.tree["nonstream"], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree["stream"].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree["stream"]):
            assert np.all(row == i)


def test_stream_to_stream():
    tree = {"nonstream": np.array([1, 2, 3, 4], np.int64), "stream": Stream([6, 2], np.float64)}

    buff = io.BytesIO()
    fd = generic_io.OutputStream(buff)

    ff = asdf.AsdfFile(tree)
    ff.write_to(fd)
    for i in range(100):
        fd.write(np.array([i] * 12, np.float64).tobytes())

    buff.seek(0)

    with asdf.open(generic_io.InputStream(buff, "r")) as ff:
        assert len(ff._blocks.blocks) == 2
        assert_array_equal(ff.tree["nonstream"], np.array([1, 2, 3, 4], np.int64))
        assert ff.tree["stream"].shape == (100, 6, 2)
        for i, row in enumerate(ff.tree["stream"]):
            assert np.all(row == i)


def test_array_to_stream(tmp_path):
    tree = {
        "stream": np.array([1, 2, 3, 4], np.int64),
    }

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree["stream"], "streamed")
    ff.write_to(buff)
    buff.write(np.array([5, 6, 7, 8], np.int64).tobytes())

    buff.seek(0)
    ff = asdf.open(generic_io.InputStream(buff))
    assert_array_equal(ff.tree["stream"], [1, 2, 3, 4, 5, 6, 7, 8])
    buff.seek(0)
    ff2 = asdf.AsdfFile(ff)
    ff2.set_array_storage(ff2["stream"], "streamed")
    ff2.write_to(buff)
    assert b"shape: ['*']" in buff.getvalue()

    with open(os.path.join(str(tmp_path), "test.asdf"), "wb") as fd:
        ff = asdf.AsdfFile(tree)
        ff.set_array_storage(tree["stream"], "streamed")
        ff.write_to(fd)
        fd.write(np.array([5, 6, 7, 8], np.int64).tobytes())

    with asdf.open(os.path.join(str(tmp_path), "test.asdf")) as ff:
        assert_array_equal(ff.tree["stream"], [1, 2, 3, 4, 5, 6, 7, 8])
        ff2 = asdf.AsdfFile(ff)
        ff2.write_to(buff)
        assert b"shape: ['*']" in buff.getvalue()


def test_too_many_streams():
    tree = {"stream1": np.array([1, 2, 3, 4], np.int64), "stream2": np.array([1, 2, 3, 4], np.int64)}

    ff = asdf.AsdfFile(tree)
    ff.set_array_storage(tree["stream1"], "streamed")
    with pytest.raises(ValueError, match=r"Can not add second streaming block"):
        ff.set_array_storage(tree["stream2"], "streamed")


def test_stream_repr_and_str():
    tree = {"stream": Stream([16], np.int64)}

    ff = asdf.AsdfFile(tree)
    repr(ff.tree["stream"])
    str(ff.tree["stream"])
