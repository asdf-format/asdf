import numpy as np
import pytest

import asdf

# botocore uses the deprecated utcnow
pytestmark = pytest.mark.filterwarnings(r"ignore:datetime\.datetime\.utcnow\(\) is deprecated.*:DeprecationWarning")


@pytest.fixture()
def bucket_url(s3):
    s3fs = pytest.importorskip("s3fs")
    bucket_name = "test"
    s3.create_bucket(Bucket="test")
    base_url = f"s3://{bucket_name}"

    fs = s3fs.S3FileSystem()

    arr = np.arange(42)
    af = asdf.AsdfFile({"arr": arr})

    url = f"{base_url}/test.asdf"
    with fs.open(url, mode="wb") as f:
        af.write_to(f)
    yield url


def test_s3fs(bucket_url):
    fsspec = pytest.importorskip("fsspec")

    with fsspec.open(bucket_url, mode="rb") as f:
        with asdf.open(f, memmap=False) as af:
            assert af["arr"][-1] == 41


def test_native(bucket_url):
    with asdf.open(bucket_url, "r") as af:
        assert af["arr"][-1] == 41
