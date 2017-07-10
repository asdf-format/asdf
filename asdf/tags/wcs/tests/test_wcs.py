# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import pytest
import warnings

gwcs = pytest.importorskip('gwcs')
astropy = pytest.importorskip('astropy', minversion='1.3.3')

from astropy.modeling import models
from astropy import coordinates as coord
from astropy import units as u
from astropy import time

from gwcs import coordinate_frames as cf
from gwcs import wcs

from ....tests import helpers


def test_create_wcs(tmpdir):
    m1 = models.Shift(12.4) & models.Shift(-2)
    m2 = models.Scale(2) & models.Scale(-2)
    icrs = cf.CelestialFrame(name='icrs', reference_frame=coord.ICRS())
    det = cf.Frame2D(name='detector', axes_order=(0,1))
    gw1 = wcs.WCS(output_frame='icrs', input_frame='detector', forward_transform=m1)
    gw2 = wcs.WCS(output_frame='icrs', forward_transform=m1)
    gw3 = wcs.WCS(output_frame=icrs, input_frame=det, forward_transform=m1)

    tree = {
        'gw1': gw1,
        'gw2': gw2,
        'gw3': gw3
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)


def test_composite_frame(tmpdir):
    icrs = coord.ICRS()
    fk5 = coord.FK5()
    cel1 = cf.CelestialFrame(reference_frame=icrs)
    cel2 = cf.CelestialFrame(reference_frame=fk5)

    spec1 = cf.SpectralFrame(name='freq', unit=[u.Hz,], axes_order=(2,))
    spec2 = cf.SpectralFrame(name='wave', unit=[u.m,], axes_order=(2,))

    comp1 = cf.CompositeFrame([cel1, spec1])
    comp2 = cf.CompositeFrame([cel2, spec2])
    comp = cf.CompositeFrame([comp1, cf.SpectralFrame(axes_order=(3,), unit=(u.m,))])

    tree = {
        'comp1': comp1,
        'comp2': comp2,
        'comp': comp
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)

def create_test_frames():
    """Creates an array of frames to be used for testing."""

    # Suppress warnings from astropy that are caused by having 'dubious' dates
    # that are too far in the future. It's not a concern for the purposes of
    # unit tests. See issue #5809 on the astropy GitHub for discussion.
    from astropy._erfa import ErfaWarning
    warnings.simplefilter("ignore", ErfaWarning)

    frames = [
        cf.CelestialFrame(reference_frame=coord.ICRS()),

        cf.CelestialFrame(
            reference_frame=coord.FK5(equinox=time.Time('2010-01-01'))),

        cf.CelestialFrame(
            reference_frame=coord.FK4(
                equinox=time.Time('2010-01-01'),
                obstime=time.Time('2015-01-01'))
            ),

        cf.CelestialFrame(
            reference_frame=coord.FK4NoETerms(
                equinox=time.Time('2010-01-01'),
                obstime=time.Time('2015-01-01'))
            ),

        cf.CelestialFrame(
            reference_frame=coord.Galactic()),

        cf.CelestialFrame(
            reference_frame=coord.Galactocentric(
                # A default galcen_coord is used since none is provided here
                galcen_distance=5.0*u.m,
                z_sun=3*u.pc,
                roll=3*u.deg)
            ),

        cf.CelestialFrame(
            reference_frame=coord.GCRS(
                obstime=time.Time('2010-01-01'),
                obsgeoloc=[1, 3, 2000] * u.pc,
                obsgeovel=[2, 1, 8] * (u.m/u.s))),

        cf.CelestialFrame(
            reference_frame=coord.CIRS(
                obstime=time.Time('2010-01-01'))),

        cf.CelestialFrame(
            reference_frame=coord.ITRS(
                obstime=time.Time('2022-01-03'))),

        cf.CelestialFrame(
            reference_frame=coord.PrecessedGeocentric(
                obstime=time.Time('2010-01-01'),
                obsgeoloc=[1, 3, 2000] * u.pc,
                obsgeovel=[2, 1, 8] * (u.m/u.s)))
    ]

    return frames

def test_frames(tmpdir):

    tree = {
        'frames': create_test_frames()
    }

    helpers.assert_roundtrip_tree(tree, tmpdir)

@pytest.mark.xfail()
def test_backwards_compatibility(tmpdir):
    yaml = """
wcs/celestial_frame-1.1.0
  axes_names: [x, y, z]
  axes_order: [0, 1, 2]
  name: CelestialFrame
  reference_frame:
    galcen_dec: !unit/quantity-1.1.0
      unit: rad
      value: 1.0
    galcen_distance: !unit/quantity-1.1.0
      unit: m
      value: 5.0
    galcen_ra: !unit/quantity-1.1.0
      unit: deg
      value: 45.0
    roll: !unit/quantity-1.1.0
      unit: deg
      value: 3.0
    type: galactocentric
    z_sun: !unit/quantity-1.1.0
      unit: pc
      value: 3.0
  unit: [!unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg]"""
