from pathlib import Path

import numpy as np
import pytest

import asdf

_ = pytest.importorskip("scipy")


def test_scipy_array_api(tmp_path, scipy_array_api):
    """Test that `NDArrayType` works with scipy's array API backend.

    https://github.com/asdf-format/asdf/issues/2161
    """
    from scipy.interpolate import CubicSpline

    path = Path(tmp_path) / "file.asdf"
    x = np.array([1, 2, 3, 4, 5, 6])
    y = np.array([1, 4, 8, 16, 25, 36])
    asdf.dump({"y": y}, path)
    with asdf.open(path, lazy_load=True) as af:
        spl = CubicSpline(x, af["y"])
        _ = spl(2.5)
