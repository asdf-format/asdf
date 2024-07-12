import numpy as np

import asdf


def test_memmap_view_access_after_close(tmp_path):
    """
    Accessing a view of a memmap after the asdf file
    is closed results in a segfault

    https://github.com/asdf-format/asdf/issues/1334
    """

    a = np.ones(10, dtype="uint8")
    fn = tmp_path / "test.asdf"
    asdf.AsdfFile({"a": a}).write_to(fn)

    with asdf.open(fn, memmap=True) as af:
        v = af["a"][:5]

    assert np.all(v == 1)
