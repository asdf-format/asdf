# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io

from astropy.extern import six
from astropy.tests.helper import pytest
from astropy import units as u

from jsonschema import ValidationError

from .. import finf

from . import helpers


def test_violate_toplevel_schema():
    tree = {'fits': 'This does not look like a FITS file'}

    buff = io.BytesIO()
    ff = finf.FinfFile(tree)

    with pytest.raises(ValidationError) as e:
        ff.write_to(buff)


def test_tagging_scalars():
    yaml = """
unit: !unit
  m
not_unit:
  m
    """

    buff = helpers.yaml_to_finf(yaml)
    ff = finf.FinfFile.read(buff)

    assert isinstance(ff.tree['unit'], u.UnitBase)
    assert not isinstance(ff.tree['not_unit'], u.UnitBase)
    assert isinstance(ff.tree['not_unit'], six.text_type)

    assert ff.tree == {
        'unit': u.m,
        'not_unit': 'm'
        }
