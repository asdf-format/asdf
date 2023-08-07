import numpy as np

import asdf


def test_asdf_info_should_not_load_arrays(tmp_path):
    """
    AsdfFile.info should not load array data

    https://github.com/asdf-format/asdf/issues/1553
    """
    fn = tmp_path / "test.asdf"
    tree = dict([(k, np.arange(ord(k))) for k in "abc"])
    asdf.AsdfFile(tree).write_to(fn)

    with asdf.open(fn) as af:
        assert "unloaded" in str(af["b"])
        af.info()
        assert "unloaded" in str(af["b"])
