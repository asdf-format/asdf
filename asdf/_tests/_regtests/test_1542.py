import os
import sys

import numpy as np
import pytest

import asdf


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="os.pipe.seek noop on windows: https://bugs.python.org/issue42602"
)
def test_failure_to_write_blocks_to_non_seekable_file():
    """
    ASDF fails to write blocks to non-seekable file

    https://github.com/asdf-format/asdf/issues/1542
    """
    r, w = os.pipe()
    with os.fdopen(r, "rb") as rf:
        with os.fdopen(w, "wb") as wf:
            arrs = [np.zeros(1, dtype="uint8") + i for i in range(10)]
            af = asdf.AsdfFile({"arrs": arrs})
            af.write_to(wf)
        with asdf.open(rf) as raf:
            for a, ra in zip(arrs, raf["arrs"]):
                np.testing.assert_array_equal(a, ra)
