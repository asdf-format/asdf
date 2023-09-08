import numpy as np

import asdf


def test_update_fails_after_write_to(tmp_path):
    """
    Calling update after write_to fails

    https://github.com/asdf-format/asdf/issues/1505
    """
    fn1 = tmp_path / "test1.asdf"
    fn2 = tmp_path / "test2.asdf"

    tree = {"a": np.zeros(3), "b": np.ones(3)}
    af = asdf.AsdfFile(tree)

    af.write_to(fn1)

    with asdf.open(fn1, mode="rw") as af:
        af["a"] = None
        af.write_to(fn2)
        af.update()
