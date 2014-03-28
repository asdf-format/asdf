# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy import units as u

from ... import finf

from ...tests import helpers


def test_invalid_unit():
    yaml = """
unit: !unit
  foo
    """

    buff = helpers.yaml_to_finf(yaml)
    ff = finf.FinfFile.read(buff)

    assert isinstance(ff.tree['unit'], u.UnrecognizedUnit)


def test_unit():
    yaml = """
unit: !unit "2.1798721  10-18kg m2 s-2"
    """

    buff = helpers.yaml_to_finf(yaml)
    ff = finf.FinfFile.read(buff)

    assert ff.tree['unit'].is_equivalent(u.Ry)
