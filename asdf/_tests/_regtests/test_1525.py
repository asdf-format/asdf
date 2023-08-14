import numpy as np
import pytest

import asdf


@pytest.mark.parametrize("copy_arrays", [True, False])
def test_external_blocks_always_lazy_loaded_and_memmapped(tmp_path, copy_arrays):
    """
    External blocks are always lazy loaded and memmapped

    https://github.com/asdf-format/asdf/issues/1525
    """

    fn = tmp_path / "test.asdf"
    arr = np.arange(10)
    af = asdf.AsdfFile({"arr": arr})
    af.set_array_storage(arr, "external")
    af.write_to(fn)

    with asdf.open(fn, copy_arrays=copy_arrays) as af:
        # check that block is external
        source = af["arr"]._source
        assert isinstance(source, str)

        # check if block is memmapped
        if copy_arrays:
            assert not isinstance(af["arr"].base, np.memmap)
        else:
            assert isinstance(af["arr"].base, np.memmap)
