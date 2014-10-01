# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy import units as u

from .... import asdf
from ....tests import helpers


# TODO: Implement defunit


def test_unit():
    yaml = """
unit: !unit/unit "2.1798721  10-18kg m2 s-2"
    """

    buff = helpers.yaml_to_asdf(yaml)
    ff = asdf.AsdfFile.read(buff)

    assert ff.tree['unit'].is_equivalent(u.Ry)
