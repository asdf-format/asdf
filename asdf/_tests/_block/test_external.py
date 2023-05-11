import numpy as np

import asdf
from asdf._block import external


def test_cache(tmp_path):
    efn = tmp_path / "test.asdf"
    arr = np.arange(3, dtype="uint8")
    asdf.AsdfFile({"data": arr}).write_to(efn)

    cache = external.ExternalBlockCache()
    base_uri = f"file://{tmp_path}/"
    data = cache.load(base_uri, "test.asdf")
    np.testing.assert_array_equal(data, arr)
    assert cache.load(base_uri, "test.asdf") is data
    assert cache.load(base_uri, "#") is external.UseInternal
    assert cache.load(base_uri, "") is external.UseInternal
