import numpy as np
import pytest

import asdf
from asdf._block import external


def test_cache(tmp_path):
    efn = tmp_path / "test.asdf"
    arr = np.arange(3, dtype="uint8")
    asdf.AsdfFile({"data": arr}).write_to(efn)

    cache = external.ExternalBlockCache()
    base_uri = f"{tmp_path.as_uri()}/"
    data = cache.load(base_uri, "test.asdf")
    np.testing.assert_array_equal(data, arr)
    assert cache.load(base_uri, "test.asdf") is data
    assert cache.load(base_uri, "#") is external.UseInternal
    assert cache.load(base_uri, "") is external.UseInternal


@pytest.mark.parametrize("uri", ["test.asdf", "foo/test.asdf"])
@pytest.mark.parametrize("index", [0, 1, 100])
def test_relative_uri_for_index(uri, index):
    match = f"test{index:04d}.asdf"
    assert external.relative_uri_for_index(uri, index) == match
