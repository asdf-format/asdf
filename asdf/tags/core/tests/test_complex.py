# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import pytest

import asdf
from asdf.tests import helpers


def test_invalid_complex():
    yaml = """
a: !core/complex-1.0.0
  3 + 4i
    """

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.raises(ValueError):
        with asdf.AsdfFile.open(buff):
            pass


def test_roundtrip(tmpdir):
    tree = {
        'a': 0+0j,
        'b': 1+1j,
        'c': -1+1j,
        'd': -1-1j
        }

    helpers.assert_roundtrip_tree(tree, tmpdir)
