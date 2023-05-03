import numpy as np
import pytest

import asdf


@pytest.mark.xfail(reason="fixing this may require subclassing ndarray")
def test_1530(tmp_path):
    """
    Calling update with memmapped data can create invalid data in memmap views

    https://github.com/asdf-format/asdf/issues/1530

    A view of a memmapped array can return invalid data or segfault
    after an update
    """
    fn = tmp_path / "test.asdf"
    a = np.zeros(10, dtype="uint8")
    b = np.ones(10, dtype="uint8")
    ov = a[:3]

    af = asdf.AsdfFile({"a": a, "b": b})
    af.write_to(fn)

    with asdf.open(fn, mode="rw", copy_arrays=False) as af:
        va = af["a"][:3]
        np.testing.assert_array_equal(a, af["a"])
        np.testing.assert_array_equal(b, af["b"])
        np.testing.assert_array_equal(va, ov)
        af["c"] = "a" * 10000
        af.update()
        np.testing.assert_array_equal(a, af["a"])
        np.testing.assert_array_equal(b, af["b"])
        assert False
        # np.testing.assert_array_equal(va, ov)  # segfault
