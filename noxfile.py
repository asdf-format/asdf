from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field
from pathlib import Path

import nox

# Use uv if available, otherwise fall back to default
nox.options.default_venv_backend = "uv|virtualenv"
# Fail if using an external program without external=True
nox.options.error_on_external_run = True

PYPROJECT = nox.project.load_toml("pyproject.toml")


def log_dependencies(session) -> None:
    """Log all dependencies in the current environment.

    Only shown if nox is run with `nox -v`.
    """
    if session.venv_backend == "uv":
        session.run_install("uv", "pip", "freeze", silent=True)
    else:
        session.run_install("pip", "freeze", silent=True)


@dataclass(frozen=True)
class Package:
    """Helper class for defining an external package to test."""

    name: str
    repo: str
    _: KW_ONLY
    tags: list[str] = field(default_factory=list)
    extras: list[str] | None = None
    env: dict[str, str] | None = None
    parallel: bool = False
    pytest_paths: list[str] | None = None
    pytest_args: list[str] | None = None

    def as_param(self):
        """Build a nox `param` from the package configuration."""
        return nox.param(self, tags=self.tags, id=self.name)

    def download_and_install(self, session) -> Path:
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

    def install_asdf(self, session) -> None:
        """Install local version of ASDF and all required dependencies."""
        session.install("-e", ".[all,tests]")

    def test(self, session) -> None:
        """Run the package's test suite."""
        log_dependencies(session)
        session.run(*self._generate_pytest_command(), env=self.env)

    def _installer_spec(self, dir: Path) -> str:
        """Get the full dependency spec for installing the package which can be passed to pip.

        `dir` is the full path to the package repo.
        """
        extras = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{dir}{extras}"

    def _generate_pytest_command(self):
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

    def install(self, session, *extra_deps):
        """Install local version of ASDF and its dependencies.

        Arguments passed to `extra_deps` are installed after ASDF.
        """
        if self.parallel:
            session.install("pytest-xdist")

        session.install("-e", ".[all,tests]")

        if extra_deps:
            session.install(*extra_deps)

        return self

    def test(self, session, *extra_args) -> Asdf:
        """Run the ASDF test suite.

        Arguments passed to `extra_args` are forwarded to pytest.
        """
        log_dependencies(session)
        session.run(*self._pytest_args(), *extra_args)
        return self

    def install_oldest_deps(self, session) -> Asdf:
        """Install the oldest supported versions of all ASDF dependencies."""
        session.install("minimum_dependencies")
        tmp_path = Path(session.create_tmp()) / "requirements-min.txt"
        session.run_install("minimum_dependencies", "asdf", "--filename", str(tmp_path), silent=True)

        session.install("-r", tmp_path)
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


CRDS_ENV = {
    "CRDS_SERVER_URL": "https://jwst-crds.stsci.edu",
    "CRDS_PATH": "/tmp/crds_cache",  # noqa: S108
    "CRDS_CLIENT_RETRY_COUNT": "3",
    "CRDS_CLIENT_RETRY_DELAY_SECONDS": "20",
}

# Downstream packages with test suites to run against the local asdf version
DOWNSTREAM = [
    ### asdf ###
    Package(
        "asdf-compression",
        "https://github.com/asdf-format/asdf-compression.git",
        tags=["asdf"],
        extras=["tests", "all"],
    ),
    Package("asdf-zarr", "https://github.com/asdf-format/asdf-zarr.git", tags=["asdf"], extras=["tests"]),
    Package("asdf-wcs-schemas", "https://github.com/asdf-format/asdf-wcs-schemas.git", tags=["asdf"], extras=["test"]),
    Package(
        "asdf-coordinates-schemas",
        "https://github.com/asdf-format/asdf-coordinates-schemas.git",
        tags=["asdf"],
        extras=["test"],
    ),
    ### astropy ###
    Package(
        "asdf-astropy",
        "https://github.com/astropy/asdf-astropy.git",
        tags=["astropy"],
        extras=["test"],
    ),
    Package(
        "specutils",
        "https://github.com/astropy/specutils.git",
        tags=["astropy"],
        extras=["test"],
    ),
    ### stsci ###
    Package(
        "astrocut",
        "https://github.com/spacetelescope/astrocut.git",
        tags=["stsci"],
        extras=["test"],
        pytest_args=["--pyargs", "astrocut"],
    ),
    Package(
        "gwcs",
        "https://github.com/spacetelescope/gwcs.git",
        tags=["stsci"],
        extras=["test"],
    ),
    Package(
        "jwst",
        "https://github.com/spacetelescope/jwst.git",
        tags=["stsci"],
        extras=["test"],
        env=CRDS_ENV,
    ),
    Package(
        "stdatamodels",
        "https://github.com/spacetelescope/stdatamodels.git",
        tags=["stsci"],
        extras=["test"],
        env=CRDS_ENV,
    ),
    Package("stpipe", "https://github.com/spacetelescope/stpipe.git", tags=["stsci"], extras=["test"]),
    Package(
        "roman_datamodels", "https://github.com/spacetelescope/roman_datamodels.git", tags=["stsci"], extras=["test"]
    ),
    ### third-party ###
    Package(
        "weldx",
        "https://github.com/BAMWelDX/weldx.git",
        tags=["third-party"],
        extras=["test", "media"],
        pytest_paths=["weldx/tests/asdf_tests", "weldx/schemas"],
        pytest_args=["--asdf-tests"],
    ),
    Package(
        "sunpy",
        "https://github.com/sunpy/sunpy.git",
        tags=["third-party"],
        extras=["tests", "all"],
        pytest_paths=["sunpy/io"],
    ),
    Package(
        "dkist",
        "https://github.com/DKISTDC/dkist.git",
        tags=["third-party"],
        extras=["tests"],
        pytest_args=["--benchmark-skip"],
    ),
    Package(
        "dkist-inventory",
        "https://bitbucket.org/dkistdc/dkist-inventory.git",
        tags=["third-party"],
        extras=["test"],
        parallel=True,
    ),
    # This package's tests only work on linux
    Package(
        "abacusutils",
        "https://github.com/abacusorg/abacusutils.git",
        tags=["third-party"],
        pytest_paths=["tests/test_data.py"],
    ),
]


################
### SESSIONS ###
################


@nox.session(tags=["test", "downstream"], python="3.12")
@nox.parametrize("pkg", [pkg.as_param() for pkg in DOWNSTREAM])
def downstream(session, pkg: Package):
    """Run the test suite for a downstream package against the local asdf version."""
    dir = pkg.download_and_install(session)
    pkg.install_asdf(session)

    with session.cd(dir):
        pkg.test(session)


@nox.session(tags=["test", "core"], python=["3.10", "3.11", "3.12", "3.13"])
def core(session):
    """Run asdf test suite"""
    Asdf(parallel=True).install(session).test(session)


@nox.session(tags=["test", "coverage"], python="3.14")
def coverage(session):
    """Run asdf test suite with coverage"""
    (
        Asdf(parallel=False)
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
def devdeps(session):
    """Run asdf tests against latest unstable versions of asdf dependencies"""
    (
        Asdf(parallel=True)
        .install(session, "-r", "requirements-dev.txt")
        .test(session, "-W", "ignore::asdf_standard.exceptions.UnstableCoreSchemasWarning")
    )


@nox.session(tags=["test", "core"], python="3.12")
def mocks3(session):
    """Set up AWS mocks and run S3 integration tests"""
    (
        Asdf(parallel=False)
        .install(session, *nox.project.dependency_groups(PYPROJECT, "mocks3"))
        .test(session, "integration_tests/mocks3/")
    )


@nox.session(tags=["test", "core"], python="3.11")
def compatibility(session):
    """Run asdf compatibility integration tests"""
    Asdf(parallel=False).install(session, "virtualenv").test(session, "integration_tests/compatibility/")


@nox.session(tags=["test"], python="3.12")
def jsonschema(session):
    """Run asdf jsonschema tests"""
    Asdf(parallel=False).install(session).test(session, "--jsonschema")


@nox.session(
    tags=["test", "core"],
    python="3.10",
    # This test doesn't work with the uv backend
    # Probably due to differences in build isolation
    venv_backend="virtualenv",
)
def oldestdeps(session):
    """Run asdf tests against oldest supported dependency versions"""
    (Asdf(parallel=True).install(session).install_oldest_deps(session).test(session))


@nox.session(tags=["test", "core"], python=["3.14", "3.15"])
def pytestdev(session):
    """Run asdf tests using latest unstable pytest version"""
    Asdf(parallel=True).install(session, "git+https://github.com/pytest-dev/pytest").test(session)
