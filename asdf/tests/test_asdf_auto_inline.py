import numpy as np
import os
import pytest

import asdf
from .. import constants


def _write_test_file_multi(version, oname, short_arr, long_arr):
    tree = {
        "author": "Monty",
        "foo": 42,
        "bar": 13,
    }
    short_length = constants.DEFAULT_AUTO_INLINE - 1
    long_length = constants.DEFAULT_AUTO_INLINE
    
    tlen = max(short_arr, long_arr)
    for k in range(tlen):
        if k<short_arr:
            key = f"short_array_{k+1}"
            tree[key] = np.random.rand(short_length)
        if k<long_arr:
            key = f"long_array_{k+1}"
            tree[key] = np.random.rand(long_length)

    # Write it all out
    with asdf.AsdfFile(tree, version=version) as af:
        af.write_to(oname)


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_write_to_auto_inline(tmpdir, version):
    fname = "auto_inline_test.asdf"
    oname = os.path.join(tmpdir, fname)
    num_short = 10
    num_long = 13
    _write_test_file_multi(version, oname, num_short, num_long)

    with asdf.open(oname) as af:
        assert len(af._blocks._internal_blocks) == num_long
        assert len(af._blocks._inline_blocks) == num_short
