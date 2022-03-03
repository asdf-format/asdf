#!/usr/bin/env python
from pathlib import Path

from setuptools import setup


def package_yaml_files(directory):
    paths = sorted(Path(directory).rglob("*.yaml"))
    return [str(p.relative_to(directory)) for p in paths]


package_data = {
    "asdf.commands.tests.data": ["*"],
    "asdf.tags.core.tests.data": ["*"],
    "asdf.tests.data": ["*"],
}

setup(
    package_data=package_data,
)
