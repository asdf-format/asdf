"""
Generate the minimal dependency requirements for a given package
"""
import argparse
import warnings
from contextlib import suppress
from itertools import chain
from sys import stdout

import requests
from importlib_metadata import requires
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, parse


def get_minimum_version(requirement):
    """Return minimum version available on PyPi for a given version specification"""
    if not requirement.specifier:
        warnings.warn(
            f"No version specifier for {requirement.name} in "
            "install_requires.  Using lowest available version on PyPi.",
            stacklevel=2,
        )

    content = requests.get(
        f"https://pypi.python.org/pypi/{requirement.name}/json",
        timeout=30,
    ).json()
    versions = []
    for v in content["releases"]:
        with suppress(InvalidVersion):
            versions.append(parse(v))

    versions = sorted(versions)

    for version in versions:
        if version in requirement.specifier:
            # If the requirement does not list any version, the lowest will be
            return version

    # If the specified version does not exist on PyPi, issue a warning
    # and return the lowest available version
    warnings.warn(
        f"Exact version specified in {requirement} not found on PyPi.  Using lowest available version.",
        stacklevel=2,
    )
    return versions[0]


def create_requirements(package: str, extras: list = None) -> str:
    """Create a list of requirements for a given package"""
    extras = [] if extras is None else extras

    requirements = []
    for r in requires(package):
        requirement = Requirement(r)

        if requirement.marker is None or any(requirement.marker.evaluate({"extra": e}) for e in extras):
            if requirement.url is None:
                version = get_minimum_version(requirement)
                requirements.append(f"{requirement.name}=={version}\n")
            else:
                requirements.append(f"{requirement}\n")

    return "".join(requirements)


def write_requirements(package: str, filename: str, extras: list = None):
    """Write out a requirements file for a given package"""

    requirements = create_requirements(package, extras=extras)
    if filename is None:
        stdout.write(requirements)
    else:
        with open(filename, "w") as fd:
            fd.write(requirements)


def make_argparser():
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        "minimum_deps",
        description="Generate a requirements-min.txt file based on install_requires",
    )
    parser.add_argument(
        "package",
        type=str,
        nargs=1,
        help="Name of the package to generate requirements for",
    )
    parser.add_argument(
        "--filename",
        "-f",
        default=None,
        help="Name of the file to write out",
    )
    parser.add_argument(
        "--extras",
        "-e",
        nargs="*",
        default=None,
        action="append",
        help="List of optional dependency sets to include",
    )
    return parser


def main(args=None):
    """Run the script"""
    parser = make_argparser()
    args = parser.parse_args()
    extras = None if args.extras is None else list(chain.from_iterable(args.extras))

    write_requirements(args.package[0], args.filename, extras)
