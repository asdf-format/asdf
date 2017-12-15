# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
import sys
import subprocess as sp

import ah_bootstrap
from astropy_helpers.setup_helpers import get_package_info as _get_package_info
from astropy_helpers.version_helpers import _get_version_py_str

from configparser import ConfigParser


__all__ = [ 'generate_version_file', 'get_package_info', 'read_metadata',
           'read_readme' ]

# Get root of asdf-standard documents
ASDF_STANDARD_ROOT = os.environ.get('ASDF_STANDARD_ROOT', 'asdf-standard')


# Freeze build information in version.py
# We no longer use generate_version_py from astropy_helpers because it imports
# the asdf module, and we no longer want to enable that kind of bad behavior
def generate_version_file(package_dir, package_name, version, release):
    version_py = os.path.join(package_dir, package_name, 'version.py')
    with open(version_py, 'w') as f:
        f.write(_get_version_py_str('asdf', version, None, release, False))


# Get configuration information from all of the various subpackages.
# See the docstring for setup_helpers.update_package_files for more details.
def get_package_info():
    package_info = _get_package_info()

    # Add the project-global data
    package_info['package_data'].setdefault('asdf', []).append('data/*')

    # The schemas come from a git submodule, so we deal with them here
    schema_root = os.path.join(ASDF_STANDARD_ROOT, "schemas")

    package_info['package_dir']['asdf.schemas'] = schema_root
    package_info['packages'].append('asdf.schemas')

    # The reference files come from a git submodule, so we deal with them here
    reference_file_root = os.path.join(ASDF_STANDARD_ROOT, "reference_files")
    if not os.path.exists(reference_file_root):
        ret = sp.call(['git', 'submodule', 'update', '--init', ASDF_STANDARD_ROOT])
        if ret != 0 or not os.path.exists(reference_file_root):
            sys.stderr.write("Failed to initialize 'asdf-standard' submodule\n")
            sys.exit(ret or 1)

    package_info['package_dir']['asdf.reference_files'] = reference_file_root
    for dirname in os.listdir(reference_file_root):
        package_info['package_dir']['asdf.reference_files.' + dirname] = os.path.join(
            reference_file_root, dirname)
    package_info['packages'].append('asdf.reference_files')

    return package_info


# Get some values from the setup.cfg
def read_metadata(config_filename):
    conf = ConfigParser()
    conf.read([config_filename])
    return dict(conf.items('metadata'))


def read_readme(readme_filename):
    with open(readme_filename) as ff:
        return ff.read()
