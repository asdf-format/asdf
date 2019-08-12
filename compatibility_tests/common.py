import asdf
from asdf.versioning import supported_versions
import numpy as np


def generate_file(path, version):
    if version not in supported_versions:
        raise ValueError("ASDF Standard version {} is not supported by version {} of the asdf library".format(version, asdf.__version__))

    af = asdf.AsdfFile({"array": np.ones((8, 16))}, version=version)
    af.write_to(path)


def assert_file_correct(path):
    __tracebackhide__ = True

    with asdf.open(str(path)) as af:
        assert af["array"].shape == (8, 16)
        assert np.all(af["array"] == 1)
