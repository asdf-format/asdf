import os
import warnings

import pytest

# We ignore these files because these modules create deprecation warnings on
# import. When warnings are turned into errors this will completely prevent
# test collection
collect_ignore = ["asdf.py", "stream.py"]


def pytest_collection_modifyitems(items):
    # first check if warnings are already turned into errors
    for wf in warnings.filters:
        if wf == ("error", None, Warning, None, 0):
            return
    # Turn warnings into errors for all tests, this is needed
    # as running tests through pyargs will not use settings
    # defined in pyproject.toml
    for item in items:
        item.add_marker(pytest.mark.filterwarnings("error"), False)


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
