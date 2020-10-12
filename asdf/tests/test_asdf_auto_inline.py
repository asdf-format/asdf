import numpy as np
import os
import pytest

import asdf


def _write_test_file(version, oname):
    small_array = np.random.rand(99)
    large_array = np.random.rand(100)
    tree = {
        "author": "Monty",
        "foo": 42,
        "bar": 13,
        "small_array": small_array,
        "large_array": large_array,
    }
    asdf_name = os.path.join(oname)
    with asdf.AsdfFile(tree, version=version) as af:
        af.write_to(asdf_name)


@pytest.mark.parametrize("version", asdf.versioning.supported_versions)
def test_write_to_auto_inline(tmpdir, version):
    fname = "auto_inline_test.asdf"
    oname = os.path.join(tmpdir, fname)
    _write_test_file(version, oname)

    with asdf.open(oname) as af:
        assert len(af._blocks._internal_blocks) == 1
        assert len(af._blocks._inline_blocks) == 1
