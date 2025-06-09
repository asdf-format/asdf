import importlib.resources

import numpy as np
import pytest

from asdf import config, schema

from .httpserver import HTTPServer


@pytest.fixture()
def small_tree():
    x = np.arange(0, 10, dtype=float)
    return {
        "science_data": x,
        "subset": x[3:-3],
        "skipping": x[::2],
        "not_shared": np.arange(10, 0, -1, dtype=np.uint8),
    }


@pytest.fixture()
def large_tree():
    # These are designed to be big enough so they don't fit in a
    # single block, but not so big that RAM/disk space for the tests
    # is enormous.
    x = np.zeros((256, 256))
    y = np.ones((16, 16, 16))
    return {
        "science_data": x,
        "more": y,
    }


@pytest.fixture
def recursive_tree(small_tree):
    a = small_tree.copy()
    a["a"] = a
    return a


@pytest.fixture(
    params=[
        "small_tree",
        "large_tree",
        "recursive_tree",
    ]
)
def tree(request):
    """
    Metafixture for all tree fixtures.
    """
    return request.getfixturevalue(request.param)


@pytest.fixture(autouse=True)
def _restore_default_config():
    yield
    config._global_config = config.AsdfConfig()
    config._local = config._ConfigLocal()


@pytest.fixture(autouse=True)
def _clear_schema_cache():
    """
    Fixture that clears schema caches to prevent issues
    when tests use same URI for different schema content.
    """
    yield
    schema._load_schema.cache_clear()
    schema._load_schema_cached.cache_clear()


@pytest.fixture()
def httpserver(request):
    """
    The returned ``httpserver`` provides a threaded HTTP server
    instance.  It serves content from a temporary directory (available
    as the attribute tmpdir) at randomly assigned URL (available as
    the attribute url).

    * ``tmpdir`` - path to the tmpdir that it's serving from (str)
    * ``url`` - the base url for the server
    """
    server = HTTPServer()
    yield server
    server.finalize()


@pytest.fixture()
def test_data_path():
    return importlib.resources.files("asdf") / "_tests" / "data"


@pytest.fixture(params=[True, False], ids=["lazy", "not-lazy"])
def with_lazy_tree(request):
    with config.config_context() as cfg:
        cfg.lazy_tree = request.param
        yield
