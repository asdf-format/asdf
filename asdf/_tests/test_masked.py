import numpy.ma
import pytest

import asdf
from asdf._tests._helpers import assert_tree_match


@pytest.mark.parametrize(
    "mask",
    [
        [[False, False, True], [False, True, False], [False, False, False]],
        True,
        False,
    ],
)
def test_masked(mask, tmp_path):
    tree = {
        "a": 1,
        "b": numpy.ma.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]], mask=mask),
    }
    af = asdf.AsdfFile(tree)
    fn = tmp_path / "masked.asdf"
    af.write_to(fn)

    with asdf.open(fn) as af:
        assert_tree_match(tree, af.tree)
