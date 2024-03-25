import numpy as np

import asdf
from asdf import AsdfFile
from asdf._tests._helpers import assert_tree_match
from asdf.commands import main


def test_explode_then_implode(tmp_path):
    x = np.arange(0, 10, dtype=float)

    tree = {
        "science_data": x,
        "subset": x[3:-3],
        "skipping": x[::2],
        "not_shared": np.arange(10, 0, -1, dtype=np.uint8),
    }

    path = tmp_path / "original.asdf"
    ff = AsdfFile(tree)
    # Since we're testing with small arrays, force all arrays to be stored
    # in internal blocks rather than letting some of them be automatically put
    # inline.
    ff.write_to(path, all_array_storage="internal")
    with asdf.open(path) as af:
        assert len(af._blocks.blocks) == 2

    result = main.main_from_args(["explode", str(path)])

    assert result == 0

    files = [p.name for p in tmp_path.iterdir()]

    assert "original.asdf" in files
    assert "original_exploded.asdf" in files
    assert "original_exploded0000.asdf" in files
    assert "original_exploded0001.asdf" in files
    assert "original_exploded0002.asdf" not in files

    # compare file sizes of original and exploded files
    original_size = (tmp_path / "original.asdf").stat().st_size
    exploded_size = (tmp_path / "original_exploded.asdf").stat().st_size
    assert original_size > exploded_size

    path = tmp_path / "original_exploded.asdf"
    result = main.main_from_args(["implode", str(path)])

    assert result == 0

    with asdf.open(tmp_path / "original_exploded_all.asdf") as af:
        assert_tree_match(af.tree, tree)
        assert len(af._blocks.blocks) == 2


def test_file_not_found(tmp_path):
    path = tmp_path / "original.asdf"
    assert main.main_from_args(["explode", str(path)]) == 2
