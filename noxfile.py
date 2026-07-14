from dataclasses import KW_ONLY, dataclass, field
from pathlib import Path

import nox

# Use uv if available, otherwise fall back to default
nox.options.default_venv_backend = "uv|virtualenv"
# Fail if using an external program without external=True
nox.options.error_on_external_run = True


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

    def test(self, session) -> None:
        """Run the package's test suite."""
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
        "asdf-standard",
        "https://github.com/asdf-format/asdf-standard.git",
        tags=["asdf"],
        extras=["test"],
    ),
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
    Package(
        "asdf-transform-schemas",
        "https://github.com/asdf-format/asdf-transform-schemas.git",
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


def install_asdf(session) -> None:
    session.install("-e", ".[all,tests]")

    # Log installed packages
    if session.venv_backend == "uv":
        session.run_install("uv", "pip", "freeze", silent=True)
    else:
        session.run_install("pip", "freeze", silent=True)


@nox.session(tags=["test", "downstream"], python="3.12")
@nox.parametrize("pkg", [pkg.as_param() for pkg in DOWNSTREAM])
def downstream(session, pkg: Package):
    """Run the test suite for a downstream package against the local asdf version."""
    dir = pkg.download_and_install(session)
    install_asdf(session)

    with session.cd(dir):
        pkg.test(session)
