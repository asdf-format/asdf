from dataclasses import dataclass, field
from pathlib import Path

import nox

# Use uv if available, otherwise fall back to default
nox.options.default_venv_backend = "uv|virtualenv"


@dataclass(frozen=True)
class Package:
    name: str
    repo: str
    tags: list[str] = field(default_factory=list)
    extras: list[str] | None = None
    env: dict[str, str] | None = None
    pytest_paths: list[str] | None = None
    pytest_args: list[str] | None = None

    def as_param(self):
        """Build a nox `param` from the package configuration."""
        return nox.param(self, tags=self.tags, id=self.name)

    def installer_spec(self, dir: Path) -> str:
        """Get the full dependency spec for installing the package which can be passed to pip.

        `dir` is the full path to the package repo.
        """
        extras = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{dir}{extras}"

    def generate_pytest_command(self):
        """Get the full pytest command for testing this package.

        Returns a generator that yields the pytest command followed by all arguments.
        """
        yield "pytest"

        if self.pytest_paths is not None:
            yield from self.pytest_paths

        if self.pytest_args is not None:
            yield from self.pytest_args


CRDS_ENV = {
    "CRDS_SERVER_URL": "https://jwst-crds.stsci.edu",
    "CRDS_PATH": "/tmp/crds_cache",  # noqa: S108
    "CRDS_CLIENT_RETRY_COUNT": "3",
    "CRDS_CLIENT_RETRY_DELAY_SECONDS": "20",
}

DOWNSTREAM = [
    ### asdf-schemas ###
    Package(
        "asdf-standard",
        "https://github.com/asdf-format/asdf-standard.git",
        tags=["asdf-schemas"],
        extras=["test"],
    ),
    Package(
        "asdf-transform-schemas",
        "https://github.com/asdf-format/asdf-transform-schemas.git",
        tags=["asdf-schemas"],
        extras=["test"],
    ),
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
    Package("asdf-astropy", "https://github.com/astropy/asdf-astropy.git", tags=["astropy"], extras=["test"]),
    Package("specutils", "https://github.com/astropy/specutils.git", tags=["astropy"], extras=["test"]),
    ### stsci ###
    Package("astrocut", "https://github.com/spacetelescope/astrocut.git", tags=["stsci"], extras=["test"]),
    Package("gwcs", "https://github.com/spacetelescope/gwcs.git", tags=["stsci"], extras=["test"]),
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
    ),
    Package(
        "abacusutils",
        "https://github.com/abacusorg/abacusutils.git",
        tags=["third-party"],
        pytest_paths=["tests/test_data.py"],
    ),
]


def install_repo(session, pkg: Package) -> Path:
    dir = Path(session.cache_dir) / pkg.name
    if dir.exists():
        with session.cd(dir):
            session.run_install("git", "pull", "--prune", external=True, silent=True)
    else:
        session.run_install("git", "clone", pkg.repo, dir, external=True, silent=True)

    session.install("-e", pkg.installer_spec(dir))
    return dir


def log_env(session):
    session.install("pip")
    # Silent so it only shows up when verbose output is enabled
    session.run_install("pip", "freeze", silent=True)


def pytest_args(*, parallel: bool, show_slowest: int | None = 10):
    yield "pytest"
    if show_slowest is not None:
        yield f"--durations={show_slowest}"
    if parallel:
        yield from ("--numprocesses", "auto")


@nox.session(tags=["test", "downstream"], python="3.12")
@nox.parametrize("pkg", [pkg.as_param() for pkg in DOWNSTREAM])
def downstream(session, pkg):
    dir = install_repo(session, pkg)
    session.install("-e", ".[all,tests]")
    log_env(session)

    with session.cd(dir):
        session.run(*pkg.generate_pytest_command())


@nox.session(tags=["test", "core"], python=["3.10", "3.11", "3.12", "3.13"])
def core(session):
    session.install("-e", ".[all,tests]")
    session.install("pytest-xdist")

    session.run(*pytest_args(parallel=True))


@nox.session(tags=["test", "coverage"], python="3.14")
def coverage(session):
    session.install("-e", ".[all,tests]")
    session.install("pytest-cov")
    session.run(
        *pytest_args(parallel=False),
        "--cov",
        "--cov-config",
        "pyproject.toml",
        "--cov-report",
        "term-missing",
        "--cov-report",
        "xml",
    )


@nox.session(tags=["test", "devdeps"], python=["3.10", "3.11", "3.12", "3.13", "3.14"])
def devdeps(session):
    session.install("-e", ".[all,tests]")
    session.install("pytest-xdist")
    session.install("-r", "requirements-dev.txt")
    session.run(*pytest_args(parallel=True), "-W", "ignore::asdf_standard.exceptions.UnstableCoreSchemasWarning")


@nox.session(tags=["test", "pytestdev"], python=["3.14", "3.15"])
def pytestdev(session):
    session.install("-e", ".[all,tests]")
    session.install("pytest-xdist")
    session.install("git+https://github.com/pytest-dev/pytest")
    session.run(*pytest_args(parallel=True))
