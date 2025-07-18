import pytest
import numpy as np

import asdf


@pytest.fixture
def software_asdf_file():
    return asdf.AsdfFile({"obj": asdf.tags.core.Software(name="foo", version="0.0.0")})


@pytest.fixture
def ndarray_asdf_file():
    return asdf.AsdfFile({"obj": np.ndarray([1])})


@pytest.fixture(params=["software_asdf_file", "ndarray_asdf_file"])
def asdf_file(request):
    return request.getfixturevalue(request.param)


def test_validate(asdf_file, benchmark):
    # first validate outside the benchmark to incur
    # extension loading, schema caching and other one-time costs
    asdf_file.validate()
    benchmark(asdf_file.validate)
