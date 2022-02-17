#!/usr/bin/env python
import os
from setuptools import setup


package_data = {
    "asdf.commands.tests.data": ["*"],
    "asdf.tags.core.tests.data": ["*"],
    "asdf.tests.data": ["*"],
}

setup(
    use_scm_version={"write_to": os.path.join("asdf", "version.py"), "write_to_template": 'version = "{version}"\n'},
    package_data=package_data,
)
