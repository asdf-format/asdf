# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import pytest

astropy = pytest.importorskip('astropy')
from astropy import units as u

from .... import asdf
from ....tests import helpers


# TODO: Implement defunit

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
