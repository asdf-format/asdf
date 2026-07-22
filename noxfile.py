from __future__ import annotations

import json
import os
from dataclasses import KW_ONLY, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import nox

if TYPE_CHECKING:
    from nox import Session

# Use uv if available, otherwise fall back to default
nox.options.default_venv_backend = "uv|virtualenv"
# Fail if using an external program without external=True
nox.options.error_on_external_run = True

PYPROJECT = nox.project.load_toml("pyproject.toml")


def log_dependencies(session: Session) -> None:
    """Log all dependencies in the current environment.

    Only shown if nox is run with `nox -v`.
    """
    if session.venv_backend == "uv":
        session.run_install("uv", "pip", "freeze", silent=True)
    else:
        session.run_install("pip", "freeze", silent=True)


def is_ci() -> bool:
    """Returns `True` if nox is currently running in a CI environment."""
    ci = os.environ.get("CI", "")
    try:
        # Parse as JSON so that `"true"`, `"1"`, etc register as `True`
        # `"false"`, `"0"`, or any invalid value registers as `False`
        return bool(json.loads(ci))
    except json.JSONDecodeError:
        return False


@dataclass(frozen=True)
class Package:
    """Helper class for defining an external package to test."""

    name: str
    repo: str
    _: KW_ONLY
    category: str | None = None
    extras: list[str] | None = None
    env: dict[str, str] | None = None
    parallel: bool = False
    pytest_paths: list[str] | None = None
    pytest_args: list[str] | None = None

    def as_param(self) -> nox.param:
        """Build a nox `param` from the package configuration."""
        tags = [self.category] if self.category is not None else []
        return nox.param(self, tags=tags, id=self.name)

    def download_and_install(self, session: Session) -> Path:
        """Clone and install the package repo and its dependencies.

        Returns the local path to the package root.
        """
        dir = Path(session.cache_dir) / self.name
        if dir.exists():
            with session.cd(dir):
                session.run_install("git", "pull", "--prune", external=True, silent=True)
        else:
            session.run_install("git", "clone", self.repo, dir, external=True, silent=True)

        session.install("-e", self._installer_spec(dir))
        return dir

    def install_asdf(self, session: Session) -> None:
        """Install local version of ASDF and all required dependencies."""
        session.install("-e", ".[all,tests]")

    def test(self, session: Session) -> None:
        """Run the package's test suite."""
        log_dependencies(session)
        session.run(*self._pytest_args(), *session.posargs, env=self.env)

    def _installer_spec(self, dir: Path) -> str:
        """Get the full dependency spec for installing the package which can be passed to pip.

        `dir` is the full path to the package repo.
        """
        extras = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{dir}{extras}"

    def _pytest_args(self):
        """Get the full pytest command for testing this package.

        Returns a generator that yields the pytest command followed by all arguments.
        """
        yield "pytest"

        if self.pytest_paths is not None:
            yield from self.pytest_paths

        if self.parallel:
            yield from ("-n", "auto")

        if self.pytest_args is not None:
            yield from self.pytest_args


@dataclass(frozen=True, kw_only=True)
class Asdf:
    """Helper class for managing ASDF installation and testing options."""

    parallel: bool
    show_slowest: int | None = 10
    extras: list[str] = field(default_factory=lambda: ["all", "tests"])

    def install(self, session: Session, *extra_deps: str) -> Asdf:
        """Install local version of ASDF and its dependencies.

        Arguments passed to `extra_deps` are installed after ASDF.
        """
        if self.parallel:
            session.install("pytest-xdist")

        if self.extras:
            extras = f"[{','.join(self.extras)}]"
        else:
            extras = ""

        session.install("-e", f".{extras}")

        if extra_deps:
            session.install(*extra_deps)

        return self

    def test(self, session: Session, *extra_args: str) -> Asdf:
        """Run the ASDF test suite.

        Arguments passed to `extra_args` are forwarded to pytest.
        """
        log_dependencies(session)
        session.run(*self._pytest_args(), *extra_args, *session.posargs)
        return self

    def install_oldest_deps(self, session: Session) -> Asdf:
        """Install the oldest supported versions of all ASDF dependencies."""
        session.install("minimum_dependencies")
        tmp_path = Path(session.create_tmp()) / "requirements-min.txt"
        session.run_install("minimum_dependencies", "asdf", "--filename", str(tmp_path), silent=True)

        session.install("-r", str(tmp_path))
        return self

    def _pytest_args(self):
        """Generate pytest command and arguments.

        Intended to be passed to `session.run`.
        """
        yield "pytest"
        if self.show_slowest is not None:
            yield f"--durations={self.show_slowest}"
        if self.parallel:
            yield from ("--numprocesses", "auto")


CRDS_ENV: dict[str, str] = {
    "CRDS_SERVER_URL": "https://jwst-crds.stsci.edu",
    "CRDS_PATH": "/tmp/crds_cache",  # noqa: S108
    "CRDS_CLIENT_RETRY_COUNT": "3",
    "CRDS_CLIENT_RETRY_DELAY_SECONDS": "20",
}

# Downstream packages with test suites to run against the local asdf version
DOWNSTREAM: list[Package] = [
    ### asdf ###
    Package(
        "asdf-standard",
        "https://github.com/asdf-format/asdf-standard.git",
        category="asdf",
        extras=["test"],
    ),
    Package(
        "asdf-compression",
        "https://github.com/asdf-format/asdf-compression.git",
        category="asdf",
        extras=["tests", "all"],
    ),
    Package(
        "asdf-zarr",
        "https://github.com/asdf-format/asdf-zarr.git",
        category="asdf",
        extras=["tests"],
    ),
    Package(
        "asdf-transform-schemas",
        "https://github.com/asdf-format/asdf-transform-schemas.git",
        category="asdf",
        extras=["test"],
    ),
    Package(
        "asdf-wcs-schemas", "https://github.com/asdf-format/asdf-wcs-schemas.git", category="asdf", extras=["test"]
    ),
    Package(
        "asdf-coordinates-schemas",
        "https://github.com/asdf-format/asdf-coordinates-schemas.git",
        category="asdf",
        extras=["test"],
    ),
    ### astropy ###
    Package(
        "asdf-astropy",
        "https://github.com/astropy/asdf-astropy.git",
        category="astropy",
        extras=["test"],
    ),
    Package(
        "specutils",
        "https://github.com/astropy/specutils.git",
        category="astropy",
        extras=["test"],
    ),
    ### stsci ###
    Package(
        "astrocut",
        "https://github.com/spacetelescope/astrocut.git",
        category="stsci",
        extras=["test"],
        pytest_args=["--pyargs", "astrocut"],
    ),
    Package(
        "gwcs",
        "https://github.com/spacetelescope/gwcs.git",
        category="stsci",
        extras=["test"],
    ),
    Package(
        "jwst",
        "https://github.com/spacetelescope/jwst.git",
        category="stsci",
        extras=["test"],
        env=CRDS_ENV,
    ),
    Package(
        "stdatamodels",
        "https://github.com/spacetelescope/stdatamodels.git",
        category="stsci",
        extras=["test"],
        env=CRDS_ENV,
    ),
    Package("stpipe", "https://github.com/spacetelescope/stpipe.git", category="stsci", extras=["test"]),
    Package(
        "roman_datamodels", "https://github.com/spacetelescope/roman_datamodels.git", category="stsci", extras=["test"]
    ),
    ### third-party ###
    Package(
        "weldx",
        "https://github.com/BAMWelDX/weldx.git",
        category="third-party",
        extras=["test", "media"],
        pytest_paths=["weldx/tests/asdf_tests", "weldx/schemas"],
        pytest_args=["--asdf-tests"],
    ),
    Package(
        "sunpy",
        "https://github.com/sunpy/sunpy.git",
        category="third-party",
        extras=["tests", "all"],
        pytest_paths=["sunpy/io"],
    ),
    Package(
        "dkist",
        "https://github.com/DKISTDC/dkist.git",
        category="third-party",
        extras=["tests"],
        pytest_args=["--benchmark-skip"],
    ),
    Package(
        "dkist-inventory",
        "https://bitbucket.org/dkistdc/dkist-inventory.git",
        category="third-party",
        extras=["test"],
        parallel=True,
    ),
    # This package's tests only work on linux
    Package(
        "abacusutils",
        "https://github.com/abacusorg/abacusutils.git",
        category="third-party",
        pytest_paths=["tests/test_data.py"],
    ),
]


################
### SESSIONS ###
################


@nox.session(tags=["test", "downstream"], python="3.12")
@nox.parametrize("pkg", [pkg.as_param() for pkg in DOWNSTREAM])
def downstream(session: Session, pkg: Package) -> None:
    """Run the test suite for a downstream package against the local asdf version."""
    dir = pkg.download_and_install(session)
    pkg.install_asdf(session)

    with session.cd(dir):
        pkg.test(session)


@nox.session(tags=["test", "core"], python=["3.10", "3.11", "3.12", "3.13"])
def core(session: Session) -> None:
    """Run asdf test suite"""
    Asdf(parallel=True).install(session).test(session)


@nox.session(tags=["test", "coverage", "core"], python="3.14")
def coverage(session: Session) -> None:
    """Run asdf test suite with coverage"""
    (
        Asdf(parallel=True)
        .install(session, "pytest-cov")
        .test(
            session,
            "--cov",
            "--cov-config",
            "pyproject.toml",
            "--cov-report",
            "term-missing",
            "--cov-report",
            "xml",
        )
    )


@nox.session(tags=["test", "core"], python=["3.10", "3.11", "3.12", "3.13", "3.14"])
def devdeps(session: Session) -> None:
    """Run asdf tests against latest unstable versions of asdf dependencies"""
    session.virtualenv.env.update(
        {
            "ASDF_UNSTABLE_CORE_SCHEMAS": "1",
            "PIP_EXTRA_INDEX_URL": "https://pypi.anaconda.org/scientific-python-nightly-wheels/simple",
            "UV_INDEX": "https://pypi.anaconda.org/scientific-python-nightly-wheels/simple",
            # Change uv index resolution to match pip
            "UV_INDEX_STRATEGY": "unsafe-best-match",
            # Change uv prerelease resolution to match pip
            "UV_PRERELEASE": "allow",
        }
    )
    (
        Asdf(parallel=True)
        .install(session, "-r", "requirements-dev.txt")
        .test(session, "-W", "ignore::asdf_standard.exceptions.UnstableCoreSchemasWarning")
    )


@nox.session(tags=["test", "core"], python="3.12")
def mocks3(session: Session) -> None:
    """Set up AWS mocks and run S3 integration tests"""
    (
        Asdf(parallel=False)
        .install(session, *nox.project.dependency_groups(PYPROJECT, "mocks3"))
        .test(session, "integration_tests/mocks3/")
    )


@nox.session(tags=["test", "core"], python="3.11")
def compatibility(session: Session) -> None:
    """Run asdf compatibility integration tests"""
    Asdf(parallel=False).install(session, "virtualenv").test(session, "integration_tests/compatibility/")


@nox.session(tags=["test", "core"], python="3.12")
def jsonschema(session: Session) -> None:
    """Run asdf jsonschema tests"""
    Asdf(parallel=False).install(session).test(session, "--jsonschema")


@nox.session(
    tags=["test", "core"],
    python="3.10",
    # This test doesn't work with the uv backend
    # Probably due to differences in build isolation
    venv_backend="virtualenv",
)
def oldestdeps(session: Session) -> None:
    """Run asdf tests against oldest supported dependency versions"""
    (Asdf(parallel=True).install(session).install_oldest_deps(session).test(session))


@nox.session(tags=["test", "core"], python=["3.14", "3.15"])
def pytestdev(session: Session) -> None:
    """Run asdf tests using latest unstable pytest version"""
    Asdf(parallel=True).install(session, "git+https://github.com/pytest-dev/pytest").test(session)


@nox.session(tags=["core", "type-checking"], python="3.10")
def type_checking(session: Session) -> None:
    # Install asdf with typing dependencies
    Asdf(parallel=False, extras=["all", "tests", "typing"]).install(session)
    # If running in CI, set Github output format unless output format is manually set
    if not any(arg.startswith("--output-format") for arg in session.posargs) and is_ci():
        session.posargs.append("--output-format=github")

    session.run("pyrefly", "check", *session.posargs)
