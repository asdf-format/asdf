import warnings

import pytest


def test_warnings_are_errors():
    """
    Smoke test to make sure that warnings cause errors.
    This is here as previously asdf._tests._helpers had
    an ``assert_no_warnings`` function that was removed
    in favor of using a warning filter to turn warnings
    into errors.
    """
    with pytest.raises(UserWarning):
        warnings.warn("test")
