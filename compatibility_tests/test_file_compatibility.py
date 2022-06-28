import json
import os
import subprocess
import urllib.request
from contextlib import contextmanager
from itertools import groupby
from pathlib import Path

import pytest
import pytest_remotedata
import virtualenv
from common import assert_file_correct, generate_file
from packaging.version import Version

import asdf

# Strange version present on pypi that doesn't parse as a Version
BAD_VERSIONS = {"0"}

# Minimum library version to read files produced by the current
# version of the code.  We're not maintaining < 2.7.x and bugs in older
# versions prevent valid files from being read.
MIN_VERSION_NEW_FILES = Version("2.7.0")

# Minimum library version to produce files read by the current
# version of the code.  Earlier versions aren't able to generate
# files for all the ASDF Standard versions that they claim to support.
MIN_VERSION_OLD_FILES = Version("2.3.0")

GENERATE_SCRIPT_PATH = Path(__file__).parent / "generate_file.py"
ASSERT_SCRIPT_PATH = Path(__file__).parent / "assert_file_correct.py"


@contextmanager
def internet_temporarily_enabled(verbose=False):
    """
    Context manager that temporarily enables pytest_remotedata
    internet.
    """
    initially_disabled = pytest_remotedata.disable_internet.INTERNET_OFF

    pytest_remotedata.disable_internet.turn_on_internet(verbose=verbose)
    try:
        yield
    finally:
        if initially_disabled:
            pytest_remotedata.disable_internet.turn_off_internet(verbose=verbose)


def fetch_package_versions(package_name):
    """
    Request a package's available versions from pypi.org metadata.
    """
    content = urllib.request.urlopen(f"https://pypi.org/pypi/{package_name}/json").read()
    version_strings = json.loads(content)["releases"].keys()
    return [
        Version(v)
        for v in version_strings
        if v not in BAD_VERSIONS and (Version(v) >= MIN_VERSION_NEW_FILES or Version(v) >= MIN_VERSION_OLD_FILES)
    ]


def fetch_latest_patch_versions(package_name):
    """
    Return the latest patch version within each of the package's
    minor versions.
    """
    key_fn = lambda v: v.release[0:2]

    versions = sorted(fetch_package_versions(package_name), key=key_fn)
    return [max(group) for _, group in groupby(versions, key=key_fn)]


# Enable internet here, otherwise pytest_remotedata will complain
# (and @pytest.mark.remote_data doesn't work on non-test methods).
with internet_temporarily_enabled():
    PATCH_VERSIONS = fetch_latest_patch_versions("asdf")


def env_run(env_path, command, *args, **kwargs):
    """
    Run a command on the context of the virtual environment at
    the specified path.
    """
    return subprocess.run([env_path / "bin" / command] + list(args), **kwargs).returncode == 0


def env_check_output(env_path, command, *args):
    """
    Run a command on the context of the virtual environment at
    the specified path, and return the output.
    """
    return subprocess.check_output([env_path / "bin" / command] + list(args)).decode("utf-8").strip()


def get_supported_versions(env_path):
    """
    Get ASDF Standard versions that are supported by the asdf library
    installed in the specified virtual environment.
    """
    script = r"""import asdf; print("\n".join(str(v) for v in asdf.versioning.supported_versions))"""
    output = env_check_output(env_path, "python3", "-c", script)
    return [asdf.versioning.AsdfVersion(v) for v in output.split("\n")]


def get_installed_version(env_path):
    """
    Get the version of the asdf library installed in the specified
    virtual environment.
    """
    script = r"""import asdf; print(asdf.__version__)"""
    return Version(env_check_output(env_path, "python3", "-c", script))


@pytest.fixture(scope="module", params=PATCH_VERSIONS)
def asdf_version(request):
    """
    The (old) version of the asdf library under test.
    """
    return request.param


@pytest.fixture(scope="module")
def env_path(asdf_version, tmp_path_factory):
    """
    Path to the virtualenv where the (old) asdf library is installed.
    """
    path = tmp_path_factory.mktemp(f"asdf-{asdf_version}-env", numbered=False)

    virtualenv.cli_run([str(path)])

    assert env_run(
        path, "pip", "install", f"asdf=={asdf_version}", capture_output=True
    ), f"Failed to install asdf version {asdf_version}"

    return path


@pytest.fixture(autouse=True)
def pushd_tmpdir(tmpdir):
    """
    Change the working directory, in case the user is running these
    tests from the repo root.  Python will import a module from the
    current working directory by preference, so this prevents us
    from accidentally comparing the current library code to itself.
    """
    original_cwd = os.getcwd()
    tmpdir.chdir()
    yield
    os.chdir(original_cwd)


@pytest.mark.remote_data
def test_file_compatibility(asdf_version, env_path, tmpdir):
    # Sanity check to ensure we're not accidentally comparing
    # the current code to itself.
    installed_version = get_installed_version(env_path)
    assert installed_version == asdf_version, (
        f"The version of asdf in the virtualenv ({installed_version}) does "
        + f"not match the version being tested ({asdf_version})"
    )

    # We can only test ASDF Standard versions that both library
    # versions support.
    current_supported_versions = set(asdf.versioning.supported_versions)
    old_supported_versions = set(get_supported_versions(env_path))
    standard_versions = [v for v in current_supported_versions.intersection(old_supported_versions)]

    # Confirm that this test isn't giving us a false sense of security.
    assert len(standard_versions) > 0

    for standard_version in standard_versions:
        # Confirm that a file generated by the current version of the code
        # can be read by the older version of the library.
        if asdf_version >= MIN_VERSION_NEW_FILES:
            current_file_path = Path(str(tmpdir)) / "test-current.asdf"
            generate_file(current_file_path, standard_version)
            assert env_run(env_path, "python3", ASSERT_SCRIPT_PATH, current_file_path, capture_output=True), (
                f"asdf library version {asdf_version} failed to read an ASDF Standard {standard_version} "
                + "file produced by this code"
            )

        # Confirm that a file generated by the older version of the library
        # can be read by the current version of the code.
        if asdf_version >= MIN_VERSION_OLD_FILES:
            old_file_path = Path(str(tmpdir)) / "test-old.asdf"
            assert env_run(
                env_path, "python3", GENERATE_SCRIPT_PATH, old_file_path, str(standard_version), capture_output=True
            ), "asdf library version {} failed to generate an ASDF Standard {} file".format(
                asdf_version, standard_version
            )
            assert_file_correct(old_file_path), (
                f"asdf library version {asdf_version} produced an ASDF Standard {standard_version} "
                + "that this code failed to read"
            )
