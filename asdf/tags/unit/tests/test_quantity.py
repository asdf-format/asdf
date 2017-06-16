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
    from astropy import units

import pytest

from .... import asdf


@pytest.mark.skipif('not HAS_ASTROPY')
def test_quantity_roundtrip(tmpdir):
    from ....tests import helpers
    yaml = """
quantity: !unit/quantity-1.1.0
    value: [3.14159]
    unit: kg
"""
    quantity = units.Quantity(3.14159, unit=units.kg)
    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(buff) as ff:
        assert ff.tree['quantity'] == quantity
        buff2 = io.BytesIO()
        ff.write_to(buff2)

    buff2.seek(0)
    with asdf.AsdfFile.open(buff2) as ff:
        assert ff.tree['quantity'] == quantity
