import numpy as np

import asdf
from asdf import AsdfFile
from asdf._tests._helpers import assert_tree_match
from asdf.commands import main


def test_to_yaml(tmp_path):
    x = np.arange(0, 10, dtype=float)

    tree = {
        "science_data": x,
        "subset": x[3:-3],
        "skipping": x[::2],
        "not_shared": np.arange(10, 0, -1, dtype=np.uint8),
    }

    path = tmp_path / "original.asdf"
    ff = AsdfFile(tree)
    ff.write_to(path)
    with asdf.open(path) as ff2:
        assert len(ff2._blocks.blocks) == 2

    result = main.main_from_args(["to_yaml", str(path)])

    assert result == 0

    files = [p.name for p in tmp_path.iterdir()]

    assert "original.asdf" in files
    assert "original.yaml" in files

    with asdf.open(tmp_path / "original.yaml") as ff:
        assert_tree_match(ff.tree, tree)
        assert len(list(ff._blocks.blocks)) == 0
