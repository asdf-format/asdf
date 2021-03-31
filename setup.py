#!/usr/bin/env python
import os
from setuptools import setup, find_packages


packages = find_packages()
packages.append('asdf.schemas')
packages.append('asdf.reference_files')
packages.append('asdf.resources')

package_dir = {
    'asdf.schemas': 'asdf-standard/schemas',
    'asdf.reference_files': 'asdf-standard/reference_files',
    'asdf.resources': 'asdf-standard/resources',
}

package_data = {
    'asdf.commands.tests.data': ['*'],
    'asdf.tags.core.tests.data': ['*'],
    'asdf.tests.data': ['*'],
    'asdf.reference_files': ['*', '**/*'],
    'asdf.schemas':  ['*.yaml', '**/*.yaml', '**/**/*.yaml', '**/**/**/*.yaml'],
    'asdf.resources': ['*.yaml', '**/*.yaml', '**/**/*.yaml', '**/**/**/*.yaml'],
}

setup(
    use_scm_version={"write_to": os.path.join("asdf", "version.py"), "write_to_template": 'version = "{version}"\n'},
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
)
