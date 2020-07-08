#!/usr/bin/env python
from setuptools import setup, find_packages


packages = find_packages()
packages.append('asdf.schemas')
packages.append('asdf.reference_files')

package_dir = {
    'asdf.schemas': 'asdf-standard/schemas',
    'asdf.reference_files': 'asdf-standard/reference_files',
}

package_data = {
    'asdf.commands.tests.data': ['*'],
    'asdf.tags.core.tests.data': ['*'],
    'asdf.tests.data': ['*'],
    'asdf.reference_files': ['*', '**/*'],
    'asdf.schemas':  ['*.yaml', '**/*.yaml', '**/**/*.yaml', '**/**/**/*.yaml'],
}

setup(
    use_scm_version=True,
    packages=packages,
    package_dir=package_dir,
    package_data=package_data,
)
