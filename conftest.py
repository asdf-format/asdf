import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def temp_cwd():
    original_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            yield
    finally:
        os.chdir(original_cwd)
