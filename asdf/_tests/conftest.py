import pytest

from asdf import config, schema

from . import create_large_tree, create_small_tree
from .httpserver import HTTPServer, RangeHTTPServer


@pytest.fixture()
def small_tree():
    return create_small_tree()


@pytest.fixture()
def large_tree():
    return create_large_tree()


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
    schema.load_custom_schema.cache_clear()


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
def rhttpserver(request):
    """
    The returned ``httpserver`` provides a threaded HTTP server
    instance.  It serves content from a temporary directory (available
    as the attribute tmpdir) at randomly assigned URL (available as
    the attribute url).  The server supports HTTP Range headers.

    * ``tmpdir`` - path to the tmpdir that it's serving from (str)
    * ``url`` - the base url for the server
    """
    server = RangeHTTPServer()
    yield server
    server.finalize()
