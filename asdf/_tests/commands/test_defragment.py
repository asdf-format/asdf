import numpy as np
import pytest

import asdf
from asdf import AsdfFile
from asdf._tests._helpers import assert_tree_match
from asdf.commands import main


def _test_defragment(tmp_path, codec):
    x = np.arange(0, 1000, dtype=float)

    tree = {
        "science_data": x,
        "subset": x[3:-3],
        "skipping": x[::2],
        "not_shared": np.arange(100, 0, -1, dtype=np.uint8),
    }

    path = tmp_path / "original.asdf"
    out_path = tmp_path / "original.defragment.asdf"
    ff = AsdfFile(tree)
    ff.write_to(path)
    with asdf.open(path) as af:
        assert len(af._blocks.blocks) == 2

    result = main.main_from_args(["defragment", str(path), "-o", str(out_path), "-c", codec])

    assert result == 0

    files = [p.name for p in tmp_path.iterdir()]

    assert "original.asdf" in files
    assert "original.defragment.asdf" in files

    original_size = (tmp_path / "original.asdf").stat().st_size
    defragment_size = (tmp_path / "original.defragment.asdf").stat().st_size
    assert original_size > defragment_size

    with asdf.open(tmp_path / "original.defragment.asdf") as ff:
        assert_tree_match(ff.tree, tree)
        assert len(ff._blocks.blocks) == 2


def test_defragment_zlib(tmp_path):
    _test_defragment(tmp_path, "zlib")


def test_defragment_bzp2(tmp_path):
    _test_defragment(tmp_path, "bzp2")


def test_defragment_lz4(tmp_path):
    pytest.importorskip("lz4")
    _test_defragment(tmp_path, "lz4")
