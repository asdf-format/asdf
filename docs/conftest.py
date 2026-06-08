import os

import pytest

collect_ignore = ["conf.py"]

@pytest.fixture(autouse=True)
def tmp_cwd(tmp_path):
    """Run doctests in a temporary directory."""
    curdir = os.getcwd()
    try:
        os.chdir(tmp_path)
        yield
    finally:
        os.chdir(curdir)
