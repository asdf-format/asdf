# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True
    from astropy import units as u

import pytest

from .... import asdf
from ....tests import helpers


# TODO: Implement defunit


@pytest.mark.skipif('not HAS_ASTROPY')
def test_unit():
    yaml = """
unit: !unit/unit-1.0.0 "2.1798721  10-18kg m2 s-2"
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff) as ff:
        assert ff.tree['unit'].is_equivalent(u.Ry)

        buff2 = io.BytesIO()
        ff.write_to(buff2)

    buff2.seek(0)
    with asdf.AsdfFile.open(buff2) as ff:
        assert ff.tree['unit'].is_equivalent(u.Ry)
