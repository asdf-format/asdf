# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.tests.helper import pytest

from ... import finf

from ...tests import helpers


def test_invalid_complex():
    yaml = """
a: !complex
  3 + 4i
    """

    buff = helpers.yaml_to_finf(yaml)
    with pytest.raises(ValueError):
        finf.FinfFile.read(buff)


def test_roundtrip(tmpdir):
    tree = {
        'a': 0+0j,
        'b': 1+1j,
        'c': -1+1j,
        'd': -1-1j
        }

    helpers.assert_roundtrip_tree(tree, tmpdir)
