import numpy as np

import asdf


def test_1520(tmp_path):
    """
    A failed update can corrupt the file

    https://github.com/asdf-format/asdf/issues/1520
    """
    fn = tmp_path / "test.asdf"
    n_arrays = 10
    array_size = 10000

    # make a tree with many arrays that will compress well
    af = asdf.AsdfFile()
    for i in range(n_arrays):
        af[i] = np.zeros(array_size, dtype="uint8") + i
        af.set_array_compression(af[i], "zlib")
    af.write_to(fn)

    with asdf.open(fn, mode="rw") as af:
        # now make the data difficult to compress
        for i in range(n_arrays):
            assert np.all(af[i] == i)
            af[i][:] = np.random.randint(255, size=array_size)
            af[i][0] = i + 1
        # this no longer causes update to fail
        af.update()

    with asdf.open(fn, mode="r") as af:
        for i in range(n_arrays):
            assert af[i][0] == i + 1
