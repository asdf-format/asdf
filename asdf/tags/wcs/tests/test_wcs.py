# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import os
import pytest
import warnings
from functools import partial

gwcs = pytest.importorskip('gwcs')
astropy = pytest.importorskip('astropy', minversion='3.0.0')

from astropy.modeling import models
from astropy import coordinates as coord
from astropy import units as u
from astropy import time

from gwcs import coordinate_frames as cf
from gwcs import wcs

import asdf
from asdf import AsdfFile
from asdf.tests import helpers

from . import data as test_data
get_test_data_path = partial(helpers.get_test_data_path, module=test_data)


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0'])
def test_read_wcs(version):
    """Simple test to make sure that we can read older versions of files
    containing WCS objects. We do not test against versions of the ASDF format
    more recent than 1.1.0 since the schemas and tags have moved to Astropy and
    GWCS."""

    filename = get_test_data_path("test_wcs-{}.asdf".format(version))
    with asdf.open(filename) as tree:
        assert isinstance(tree['gw1'], wcs.WCS)
        assert isinstance(tree['gw2'], wcs.WCS)
        assert isinstance(tree['gw3'], wcs.WCS)


@pytest.mark.parametrize('version', ['1.0.0', '1.1.0', '1.2.0'])
def test_composite_frame(tmpdir, version):
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

    write_options = dict(version=version)
    helpers.assert_roundtrip_tree(tree, tmpdir, write_options=write_options)


def test_frames(tmpdir):
    """Simple check to make sure we can still read older files with frames.
    Serialization of these frames was only introduced in v1.1.0, and we do not
    test any subsequent ASDF versions since the schemas and tags for those
    frames have moved to Astropy and gwcs."""

    filename = get_test_data_path("test_frames-1.1.0.asdf")
    with asdf.open(filename) as tree:
        for frame in tree['frames']:
            assert isinstance(frame, cf.CoordinateFrame)


def test_backwards_compat_galcen():
    # Hold these fields constant so that we can compare them
    declination = 1.0208        # in degrees
    right_ascension = 45.729    # in degrees
    galcen_distance = 3.14
    roll = 4.0
    z_sun = 0.2084
    old_frame_yaml =  """
frames:
  - !wcs/celestial_frame-1.0.0
    axes_names: [x, y, z]
    axes_order: [0, 1, 2]
    name: CelestialFrame
    reference_frame:
      type: galactocentric
      galcen_dec:
        - %f
        - deg
      galcen_ra:
        - %f
        - deg
      galcen_distance:
        - %f
        - m
      roll:
        - %f
        - deg
      z_sun:
        - %f
        - pc
    unit: [!unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg]
""" % (declination, right_ascension, galcen_distance, roll, z_sun)

    new_frame_yaml = """
frames:
  - !wcs/celestial_frame-1.1.0
    axes_names: [x, y, z]
    axes_order: [0, 1, 2]
    name: CelestialFrame
    reference_frame:
      type: galactocentric
      galcen_coord: !wcs/icrs_coord-1.1.0
        dec: {value: %f}
        ra:
          value: %f
          wrap_angle:
            !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 deg, value: 360.0}
      galcen_distance:
        !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m, value: %f}
      galcen_v_sun:
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 km s-1, value: 11.1}
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 km s-1, value: 232.24}
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 km s-1, value: 7.25}
      roll: !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 deg, value: %f}
      z_sun: !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 pc, value: %f}
    unit: [!unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg]
""" % (declination, right_ascension, galcen_distance, roll, z_sun)

    old_buff = helpers.yaml_to_asdf(old_frame_yaml)
    old_asdf = AsdfFile.open(old_buff)
    old_frame = old_asdf.tree['frames'][0]
    new_buff = helpers.yaml_to_asdf(new_frame_yaml)
    new_asdf = AsdfFile.open(new_buff)
    new_frame = new_asdf.tree['frames'][0]

    # Poor man's frame comparison since it's not implemented by astropy
    assert old_frame.axes_names == new_frame.axes_names
    assert old_frame.axes_order == new_frame.axes_order
    assert old_frame.unit == new_frame.unit

    old_refframe = old_frame.reference_frame
    new_refframe = new_frame.reference_frame

    # v1.0.0 frames have no representation of galcen_v_center, so do not compare
    assert old_refframe.galcen_distance == new_refframe.galcen_distance
    assert old_refframe.galcen_coord.dec == new_refframe.galcen_coord.dec
    assert old_refframe.galcen_coord.ra == new_refframe.galcen_coord.ra


def test_backwards_compat_gcrs():
    obsgeoloc = (
        3.0856775814671916e+16,
        9.257032744401574e+16,
        6.1713551629343834e+19
    )
    obsgeovel = (2.0, 1.0, 8.0)

    old_frame_yaml =  """
frames:
  - !wcs/celestial_frame-1.0.0
    axes_names: [lon, lat]
    name: CelestialFrame
    reference_frame:
      type: GCRS
      obsgeoloc:
        - [%f, %f, %f]
        - !unit/unit-1.0.0 m
      obsgeovel:
        - [%f, %f, %f]
        - !unit/unit-1.0.0 m s-1
      obstime: !time/time-1.0.0 2010-01-01 00:00:00.000
    unit: [!unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg]
""" % (obsgeovel + obsgeoloc)

    new_frame_yaml = """
frames:
  - !wcs/celestial_frame-1.1.0
    axes_names: [lon, lat]
    name: CelestialFrame
    reference_frame:
      type: GCRS
      obsgeoloc:
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m, value: %f}
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m, value: %f}
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m, value: %f}
      obsgeovel:
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m s-1, value: %f}
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m s-1, value: %f}
      - !unit/quantity-1.1.0 {unit: !unit/unit-1.0.0 m s-1, value: %f}
      obstime: !time/time-1.1.0 2010-01-01 00:00:00.000
    unit: [!unit/unit-1.0.0 deg, !unit/unit-1.0.0 deg]
""" % (obsgeovel + obsgeoloc)

    old_buff = helpers.yaml_to_asdf(old_frame_yaml)
    old_asdf = AsdfFile.open(old_buff)
    old_frame = old_asdf.tree['frames'][0]
    old_loc = old_frame.reference_frame.obsgeoloc
    old_vel = old_frame.reference_frame.obsgeovel

    new_buff = helpers.yaml_to_asdf(new_frame_yaml)
    new_asdf = AsdfFile.open(new_buff)
    new_frame = new_asdf.tree['frames'][0]
    new_loc = new_frame.reference_frame.obsgeoloc
    new_vel = new_frame.reference_frame.obsgeovel

    assert (old_loc.x == new_loc.x and old_loc.y == new_loc.y and
        old_loc.z == new_loc.z)
    assert (old_vel.x == new_vel.x and old_vel.y == new_vel.y and
        old_vel.z == new_vel.z)
