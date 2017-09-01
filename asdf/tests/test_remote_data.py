# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import pytest

astropy = pytest.importorskip('astropy')
from astropy.tests.helper import remote_data
from astropy.tests.disable_internet import INTERNET_OFF

_REMOTE_DATA = False

@remote_data('any')
def test_internet_on():
    global _REMOTE_DATA
    _REMOTE_DATA = True
    assert INTERNET_OFF == False

def test_internet_off():
    if not _REMOTE_DATA:
        assert INTERNET_OFF == True
