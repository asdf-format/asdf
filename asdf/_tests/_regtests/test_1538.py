import numpy as np

import asdf


def test_unable_to_read_empty_inline_array(tmp_path):
    """
    ASDF unable to read empty inline array

    https://github.com/asdf-format/asdf/issues/1538
    """
    fn = tmp_path / "test.asdf"
    a = np.array([])
    af = asdf.AsdfFile({"a": a})
    af.set_array_storage(a, "inline")
    af.write_to(fn)
    with asdf.open(fn) as af:
        np.testing.assert_array_equal(af["a"], a)
