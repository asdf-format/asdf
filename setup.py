#!/usr/bin/env python
from setuptools import setup

package_data = {
    "asdf.commands.tests.data": ["*"],
    "asdf.tags.core.tests.data": ["*"],
    "asdf.tests.data": ["*"],
}

setup(
    package_data=package_data,
)
