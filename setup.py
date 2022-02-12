#!/usr/bin/env python
import os
from pathlib import Path
from setuptools import setup, find_packages

if not any((Path(__file__).parent / "asdf-standard").iterdir()):
    from setuptools.errors import SetupError

    raise SetupError("asdf-standard is empty. Need to run `git submodule update --init` and try again!")


packages = find_packages()
packages.append('asdf.schemas')
packages.append('asdf.reference_files')
packages.append('asdf.resources')

package_dir = {
    'asdf.schemas': 'asdf-standard/schemas',
    'asdf.reference_files': 'asdf-standard/reference_files',
    'asdf.resources': 'asdf-standard/resources',
}

def package_yaml_files(directory):
    paths = sorted(Path(directory).rglob("*.yaml"))
    return [str(p.relative_to(directory)) for p in paths]

package_data = {
    'asdf.commands.tests.data': ['*'],
    'asdf.tags.core.tests.data': ['*'],
    'asdf.tests.data': ['*'],
    'asdf.reference_files': ['*', '**/*'],
    'asdf.schemas':  package_yaml_files("asdf-standard/schemas"),
    'asdf.resources': package_yaml_files("asdf-standard/resources"),
}

setup(
    use_scm_version={"write_to": os.path.join("asdf", "version.py"), "write_to_template": 'version = "{version}"\n'},
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
)
