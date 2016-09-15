#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst

import glob
import os
import sys

import ah_bootstrap
from setuptools import setup

#A dirty hack to get around some early import/configurations ambiguities
if sys.version_info[0] >= 3:
    import builtins
else:
    import __builtin__ as builtins
builtins._ASDF_SETUP_ = True

from astropy_helpers.setup_helpers import (
    register_commands, get_debug_option, get_package_info)
from astropy_helpers.git_helpers import get_git_devstr
from astropy_helpers.version_helpers import generate_version_py

from astropy_helpers import test_helpers
def _null_validate(self):
    pass
test_helpers.AstropyTest._validate_required_deps = _null_validate

# Get some values from the setup.cfg
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
conf = ConfigParser()
conf.read(['setup.cfg'])
metadata = dict(conf.items('metadata'))

PACKAGENAME = metadata.get('package_name', 'packagename')
DESCRIPTION = metadata.get('description', 'package description')
AUTHOR = metadata.get('author', '')
AUTHOR_EMAIL = metadata.get('author_email', '')
LICENSE = metadata.get('license', 'unknown')
URL = metadata.get('url', '')

# Get the long description from the package's docstring
__import__('asdf')
package = sys.modules['asdf']
LONG_DESCRIPTION = package.__doc__

# Store the package name in a built-in variable so it's easy
# to get from other parts of the setup infrastructure
builtins._PACKAGE_NAME_ = 'asdf'

# VERSION should be PEP386 compatible (http://www.python.org/dev/peps/pep-0386)
VERSION = '1.0.6'

# Indicates if this version is a release version
RELEASE = 'dev' not in VERSION

if not RELEASE:
    VERSION += get_git_devstr(False)

# Get root of asdf-standard documents
ASDF_STANDARD_ROOT = os.environ.get('ASDF_STANDARD_ROOT', 'asdf-standard')

# Populate the dict of setup command overrides; this should be done before
# invoking any other functionality from distutils since it can potentially
# modify distutils' behavior.
cmdclassd = register_commands('asdf', VERSION, RELEASE)

# Freeze build information in version.py
generate_version_py('asdf', VERSION, RELEASE,
                    get_debug_option('asdf'))

# Treat everything in scripts except README.rst as a script to be installed
scripts = [fname for fname in glob.glob(os.path.join('scripts', '*'))
           if os.path.basename(fname) != 'README.rst']


# Get configuration information from all of the various subpackages.
# See the docstring for setup_helpers.update_package_files for more
# details.
package_info = get_package_info()

# Add the project-global data
package_info['package_data'].setdefault('asdf', []).append('data/*')

# The schemas come from a git submodule, so we deal with them here
schema_root = os.path.join(ASDF_STANDARD_ROOT, "schemas")

package_info['package_dir']['asdf.schemas'] = schema_root
package_info['packages'].append('asdf.schemas')

# The reference files come from a git submodule, so we deal with them here
reference_file_root = os.path.join(
    ASDF_STANDARD_ROOT, "reference_files")
package_info['package_dir']['asdf.reference_files'] = reference_file_root
for dirname in os.listdir(reference_file_root):
    package_info['package_dir']['asdf.reference_files.' + dirname] = os.path.join(
        reference_file_root, dirname)
package_info['packages'].append('asdf.reference_files')

#Define entry points for command-line scripts
entry_points = {}
entry_points['console_scripts'] = [
    'asdftool = asdf.commands.main:main',
]


# Note that requires and provides should not be included in the call to
# ``setup``, since these are now deprecated. See this link for more details:
# https://groups.google.com/forum/#!topic/astropy-dev/urYO8ckB2uM

setup(name=PACKAGENAME,
      version=VERSION,
      description=DESCRIPTION,
      scripts=scripts,
      install_requires=[
          'pyyaml>=3.10',
          'jsonschema>=2.3.0',
          'six>=1.9.0',
          'pytest>=2.7.2',
          'numpy>=1.8'
      ],
      author=AUTHOR,
      author_email=AUTHOR_EMAIL,
      license=LICENSE,
      url=URL,
      long_description=LONG_DESCRIPTION,
      cmdclass=cmdclassd,
      zip_safe=False,
      use_2to3=True,
      entry_points=entry_points,
      **package_info
)
