#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
import re
import codecs


# We need to use custom logic here to parse the README due to the raw HTML blob
# the beginning which makes things render nicely on GitHub. Without this custom
# parsing logic, the README will not render properly as the long description on
# PyPi. If we ever revert to using pure RST for the README, this can be
# replaced by functionality built into setuptools.
def read_readme(readme_filename):
    with codecs.open(readme_filename, encoding='utf8') as ff:
        lines = ff.read().splitlines()

    # Skip lines that contain raw HTML markup
    lines = lines[:4] + lines[26:]

    # Turn the header comment into a real header
    lines = lines[1:]
    lines[0:2] = [x.strip() for x in lines[0:2]]

    # Fix hyperlink targets so that the README displays properly on pypi
    label_re = re.compile(r'^\.\.\s+_(\w|-)+$')
    for i, line in enumerate(lines):
        if label_re.match(line):
            lines[i] = line + ':'

    return '\n'.join(lines)


from setuptools import setup
setup(use_scm_version=True, long_description=read_readme('README.rst'))
