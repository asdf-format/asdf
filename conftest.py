# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
import os
from collections import OrderedDict

import pytest
from _pytest.doctest import DoctestItem

from astropy.tests.helper import enable_deprecations_as_exceptions
from astropy.tests.plugins import display


display.PYTEST_HEADER_MODULES = OrderedDict([
                                    ('asdf', 'asdf'),
                                    ('numpy', 'numpy'),
                                    ('jsonschema', 'jsonschema'),
                                    ('pyyaml', 'yaml'),
                                    ('astropy', 'astropy')])

try:
    import gwcs
    display.PYTEST_HEADER_MODULES['gwcs'] = 'gwcs'
except ImportError:
    pass


pytest_plugins = [
    'astropy.tests.plugins.display'
]

enable_deprecations_as_exceptions()


@pytest.fixture(autouse=True)
def _docdir(request):
    """
    Make sure that doctests run in a temporary directory so that any files that
    are created as part of the test get removed automatically.
    """

    # Trigger ONLY for the doctests.
    if isinstance(request.node, DoctestItem):

        # Get the fixture dynamically by its name.
        tmpdir = request.getfixturevalue('tmpdir')

        # Chdir only for the duration of the test.
        olddir = os.getcwd()
        tmpdir.chdir()
        yield
        os.chdir(olddir)

    else:
        # For normal tests, we have to yield, since this is a yield-fixture.
        yield
