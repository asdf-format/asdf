import numpy as np

import asdf


def test_update_with_memmapped_data_can_make_view_data_invalid(tmp_path):
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

    with asdf.open(fn, mode="rw", memmap=True) as af:
        va = af["a"][:3]
        np.testing.assert_array_equal(a, af["a"])
        np.testing.assert_array_equal(b, af["b"])
        np.testing.assert_array_equal(va, ov)
        af["c"] = "a" * 10000
        af.update()
        np.testing.assert_array_equal(a, af["a"])
        np.testing.assert_array_equal(b, af["b"])
        # the view of 'a' taken above ('va') keeps the original memmap open
        # and is not a valid view of af['a'] (as this now differs from the
        # af['a'] used to generate the view).
        assert not np.all(va == ov)
