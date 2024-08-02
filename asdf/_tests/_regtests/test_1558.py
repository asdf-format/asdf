import weakref

import numpy as np
import pytest

import asdf


def test_asdffile_tree_cleared_on_close(tmp_path):
    """
    closed AsdfFile instances hold private reference to tree

    https://github.com/asdf-format/asdf/issues/1558
    """

    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"a": np.arange(1000), "b": np.arange(42)}).write_to(fn)

    with asdf.open(fn, memmap=False, lazy_load=False) as af:
        array_weakref = weakref.ref(af["a"])
        array_ref = af["b"]

    # we shouldn't be able to access the now closed file
    with pytest.raises(OSError, match="Cannot access data"):
        af["a"]
    with pytest.raises(OSError, match="Cannot access data"):
        af["b"]

    # we also should not be able to resolve the weak reference
    # meaning the tree should have been cleaned up
    r = array_weakref()
    assert r is None

    assert array_ref is not None
