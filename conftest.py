import pytest


@pytest.fixture(scope="session", autouse=True)
def temp_cwd():
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.chdir(tmp)
            yield
        finally:
            os.chdir(original_cwd)
