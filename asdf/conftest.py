import os
import urllib
from pathlib import Path

import pytest

# We ignore these files because these modules create deprecation warnings on
# import. When warnings are turned into errors this will completely prevent
# test collection
collect_ignore = ["asdf.py", "stream.py"]


try:
    from pyinstrument import Profiler

    TESTS_ROOT = Path.cwd()

    @pytest.fixture(autouse=True)
    def auto_profile(request):
        PROFILE_ROOT = TESTS_ROOT / ".profiles"
        # Turn profiling on
        profiler = Profiler()
        profiler.start()

        yield  # Run test

        profiler.stop()
        PROFILE_ROOT.mkdir(exist_ok=True)
        fn = urllib.parse.quote(request.node.name)
        results_file = PROFILE_ROOT / f"{fn}.html"
        profiler.write_html(results_file)

except ImportError:
    pass


def pytest_collection_modifyitems(items):
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
