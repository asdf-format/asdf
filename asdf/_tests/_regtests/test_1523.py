import numpy as np

import asdf


def test_update_corrupts_stream_data(tmp_path):
    """
    update corrupts stream data
    https://github.com/asdf-format/asdf/issues/1523
    """
    fn = tmp_path / "stream.asdf"

    s = asdf.Stream([3], np.uint8)
    asdf.AsdfFile({"s": s}).write_to(fn)

    with open(fn, "rb+") as f:
        f.seek(0, 2)
        f.write(b"\x01\x02\x03")

    with asdf.open(fn) as af:
        np.testing.assert_array_equal(af["s"], [[1, 2, 3]])

    with asdf.open(fn, mode="rw") as af:
        af["a"] = np.arange(1000)
        af.update()
        np.testing.assert_array_equal(af["s"], [[1, 2, 3]])

    with asdf.open(fn) as af:
        np.testing.assert_array_equal(af["s"], [[1, 2, 3]])
