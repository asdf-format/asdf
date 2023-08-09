import numpy as np

import asdf


def test_writes_but_fails_to_read_inline_structured_array(tmp_path):
    """
    ASDF writes but fails to read inline structured array

    https://github.com/asdf-format/asdf/issues/1540
    """
    x = np.array((0, 1.0, [2, 3]), dtype=[("MINE", "i1"), ("f1", "<f8"), ("arr", "<i4", (2,))])
    af = asdf.AsdfFile()
    af["x"] = x
    af.write_to("test.asdf", all_array_storage="inline")

    with asdf.open("test.asdf") as af2:
        np.testing.assert_array_equal(af2["x"], x)
