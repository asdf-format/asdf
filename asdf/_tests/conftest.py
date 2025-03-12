import importlib.resources

import pytest

from asdf import config, schema

from . import create_large_tree, create_small_tree
from .httpserver import HTTPServer


@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        yield


@pytest.fixture(scope="session")
def s3(aws_credentials):
    """
    Return a mocked S3 client
    """
    IP = "127.0.0.1"
    PORT = 3000
    ENDPOINT_URL = f"http://{IP}:{PORT}"
    boto3 = pytest.importorskip("boto3")
    moto_server = pytest.importorskip("moto.server")
    server = moto_server.ThreadedMotoServer(ip_address=IP, port=PORT)
    server.start()
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("FSSPEC_S3_ENDPOINT_URL", ENDPOINT_URL)
        yield boto3.client("s3", endpoint_url=ENDPOINT_URL)


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
