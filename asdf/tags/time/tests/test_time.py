# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import six
import pytest

astropy = pytest.importorskip('astropy')
from astropy import time

import numpy as np

from .... import asdf
from .... import yamlutil
from ....tests import helpers


def test_time(tmpdir):
    time_array = time.Time(
        np.arange(100), format="unix")

    tree = {
        'large_time_array': time_array
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_isot(tmpdir):
    tree = {
        'time': time.Time('2000-01-01T00:00:00.000')
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)

    ff = asdf.AsdfFile(tree)
    tree = yamlutil.custom_tree_to_tagged_tree(ff.tree, ff)
    assert isinstance(tree['time'], six.text_type)
