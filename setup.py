#!/usr/bin/env python
import os
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
    use_scm_version={
        "write_to": os.path.join("asdf", "version.py"),
        "write_to_template": 'version = "{version}"\n',
    },
    package_data=package_data,
)
