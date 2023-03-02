import os

import numpy as np

import asdf
from asdf import AsdfFile
from asdf._tests._helpers import assert_tree_match, get_file_sizes
from asdf.commands import main


def test_to_yaml(tmpdir):
    x = np.arange(0, 10, dtype=float)

    tree = {
        "science_data": x,
        "subset": x[3:-3],
        "skipping": x[::2],
        "not_shared": np.arange(10, 0, -1, dtype=np.uint8),
    }

    path = os.path.join(str(tmpdir), "original.asdf")
    ff = AsdfFile(tree)
    ff.write_to(path)
    assert len(ff._blocks) == 2

    result = main.main_from_args(["to_yaml", path])

    assert result == 0

    files = get_file_sizes(str(tmpdir))

    assert "original.asdf" in files
    assert "original.yaml" in files

    with asdf.open(os.path.join(str(tmpdir), "original.yaml")) as ff:
        assert_tree_match(ff.tree, tree)
        assert len(list(ff._blocks.internal_blocks)) == 0
