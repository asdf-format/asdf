import numpy as np

import asdf
from asdf.versioning import supported_versions


def generate_file(path, version):
    if version not in supported_versions:
        msg = f"ASDF Standard version {version} is not supported by version {asdf.__version__} of the asdf library"
        raise ValueError(msg)

    af = asdf.AsdfFile({"array": np.ones((8, 16))}, version=version)
    af.write_to(path)


def assert_file_correct(path):
    __tracebackhide__ = True

    with asdf.open(str(path)) as af:
        assert af["array"].shape == (8, 16)
        assert np.all(af["array"] == 1)
