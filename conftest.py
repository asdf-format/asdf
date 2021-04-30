import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def temp_cwd(tmpdir_factory):
    """
    This fixture creates a temporary current working directory
    for the test session, so that docstring tests that write files
    don't clutter up the real cwd.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(tmpdir_factory.mktemp("cwd"))
        yield
    finally:
        os.chdir(original_cwd)
