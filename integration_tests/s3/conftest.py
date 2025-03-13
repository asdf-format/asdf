import pytest


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
