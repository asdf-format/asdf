import os

import pytest

# We ignore these files because these modules create deprecation warnings on
# import. When warnings are turned into errors this will completely prevent
# test collection
collect_ignore = ["asdf.py", "stream.py"]


@pytest.fixture(scope="session", autouse=True)
def _temp_cwd(tmp_path_factory):
    """
    This fixture creates a temporary current working directory
    for the test session, so that docstring tests that write files
    don't clutter up the real cwd.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path_factory.mktemp("cwd"))
        yield
    finally:
        os.chdir(original_cwd)


def pytest_addoption(parser):
    parser.addoption(
        "--jsonschema",
        action="store_true",
        default=False,
        help="Run jsonschema test suite tests",
    )
