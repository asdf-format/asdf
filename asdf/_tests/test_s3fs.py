import numpy as np
import pytest

import asdf

# botocore uses the deprecated utcnow
pytestmark = pytest.mark.filterwarnings(r"ignore:datetime\.datetime\.utcnow\(\) is deprecated.*:DeprecationWarning")


@pytest.fixture(scope="module")
def bucket_url(tmp_path_factory):

    IP = "127.0.0.1"
    PORT = 3000
    ENDPOINT_URL = f"http://{IP}:{PORT}"

    with pytest.MonkeyPatch.context() as mp:
        tmp_path = tmp_path_factory.mktemp("aws")
        mock_credentials_path = tmp_path / "mock_aws_credentials"
        with open(mock_credentials_path, "w") as f:
            f.write("[foo]\naws_access_key_id = mock\naws_secret_access_key = mock")

        mp.setenv("FSSPEC_S3_ENDPOINT_URL", ENDPOINT_URL)
        mp.setenv("AWS_SHARED_CREDENTIALS_FILE", str(mock_credentials_path))
        mp.setenv("AWS_ACCESS_KEY_ID", "testing")
        mp.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        mp.setenv("AWS_SECURITY_TOKEN", "testing")
        mp.setenv("AWS_SESSION_TOKEN", "testing")
        mp.setenv("AWS_DEFAULT_REGION", "us-east-1")

        s3fs = pytest.importorskip("s3fs")

        import boto3
        import moto.server

        server = moto.server.ThreadedMotoServer(ip_address=IP, port=PORT)
        server.start()

        s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL)
        bucket_name = "test"
        s3.create_bucket(Bucket=bucket_name)

        base_url = f"s3://{bucket_name}"

        fs = s3fs.S3FileSystem()

        arr = np.arange(42)
        af = asdf.AsdfFile({"arr": arr})

        url = f"{base_url}/test.asdf"
        with fs.open(url, mode="wb") as f:
            af.write_to(f)

        yield url

        server.stop()


def test_s3fs(bucket_url):
    fsspec = pytest.importorskip("fsspec")

    with fsspec.open(bucket_url, mode="rb") as f:
        with asdf.open(f, memmap=False) as af:
            assert af["arr"][-1] == 41


def test_native(bucket_url):
    with asdf.open(bucket_url, "r") as af:
        assert af["arr"][-1] == 41
