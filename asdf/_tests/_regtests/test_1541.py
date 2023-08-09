import numpy
import pytest

import asdf


@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize("include_block_index", [True, False])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_block_checksums_only_checked_for_first_block_if_index_exists(tmp_path, index, include_block_index, lazy_load):
    """
    Block checksums are only checked for first block if a block index is present

    https://github.com/asdf-format/asdf/issues/1541
    """
    fn = tmp_path / "test.asdf"
    arrs = [numpy.zeros(1) + i for i in range(3)]
    asdf.AsdfFile({"arrs": arrs}).write_to(fn, include_block_index=include_block_index)

    # read file to get block offset
    with asdf.open(fn, lazy_load=False) as af:
        checksum_offset = af._blocks.blocks[index].offset + 2 + 4 + 4 + 8 + 8 + 8

    # now modify the block checksum
    with open(fn, "r+b") as f:
        f.seek(checksum_offset)
        v = f.read(1)[0]
        f.seek(checksum_offset)
        f.write(bytes([v + 1]))

    # and check that it raises an error
    with pytest.raises(ValueError, match=r".* does not match given checksum"):
        with asdf.open(fn, lazy_load=lazy_load, validate_checksums=True) as af:
            sum([a[0] for a in af["arrs"]])
