# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from ...asdftypes import AsdfType
from ... import yamlutil


_REQUIRES = ['gwcs', 'astropy']


class WCSType(AsdfType):
    name = "wcs/wcs"
    requires = _REQUIRES
    types = ['gwcs.WCS']
    version = '1.1.0'

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        steps = [(x['frame'], x.get('transform')) for x in node['steps']]
        name = node['name']

        return gwcs.WCS(steps, name=name)

    @classmethod
    def to_tree(cls, gwcs, ctx):
        def get_frame(frame_name):
            frame = getattr(gwcs, frame_name)
            if frame is None:
                return frame_name
            return frame

        frames = gwcs.available_frames
        steps = []
        for i in range(len(frames) - 1):
            frame_name = frames[i]
            frame = get_frame(frame_name)
            transform = gwcs.get_transform(frames[i], frames[i + 1])
            steps.append(StepType({'frame': frame, 'transform': transform}))
        frame_name = frames[-1]
        frame = get_frame(frame_name)
        steps.append(StepType({'frame': frame}))

        return {'name': gwcs.name,
                'steps': yamlutil.custom_tree_to_tagged_tree(steps, ctx)}

    @classmethod
    def assert_equal(cls, old, new):
        from ...tests import helpers

        assert old.name == new.name
        assert len(old.available_frames) == len(new.available_frames)
        for (old_frame, old_transform), (new_frame, new_transform) in zip(
                old.pipeline, new.pipeline):
            helpers.assert_tree_match(old_frame, new_frame)
            helpers.assert_tree_match(old_transform, new_transform)


class StepType(dict, AsdfType):
    name = "wcs/step"
    requires = _REQUIRES
    version = '1.1.0'


class FrameType(AsdfType):
    name = "wcs/frame"
    requires = ['gwcs']
    types = ['gwcs.Frame2D']
    version = '1.1.0'

    @classmethod
    def _get_reference_frame_mapping(cls):
        if hasattr(cls, '_reference_frame_mapping'):
            return cls._reference_frame_mapping

        from astropy.coordinates import builtin_frames

        cls._reference_frame_mapping = {
            'ICRS': builtin_frames.ICRS,
            'FK5': builtin_frames.FK5,
            'FK4': builtin_frames.FK4,
            'FK4_noeterms': builtin_frames.FK4NoETerms,
            'galactic': builtin_frames.Galactic,
            'galactocentric': builtin_frames.Galactocentric,
            'GCRS': builtin_frames.GCRS,
            'CIRS': builtin_frames.CIRS,
            'ITRS': builtin_frames.ITRS,
            'precessed_geocentric': builtin_frames.PrecessedGeocentric
        }

        return cls._reference_frame_mapping

    @classmethod
    def _get_inverse_reference_frame_mapping(cls):
        if hasattr(cls, '_inverse_reference_frame_mapping'):
            return cls._inverse_reference_frame_mapping

        reference_frame_mapping = cls._get_reference_frame_mapping()

        cls._inverse_reference_frame_mapping = {}
        for key, val in reference_frame_mapping.items():
            cls._inverse_reference_frame_mapping[val] = key

        return cls._inverse_reference_frame_mapping

    @classmethod
    def _reference_frame_from_tree(cls, node, ctx):
        from astropy.units import Quantity
        from astropy.io.misc.asdf.tags.unit.quantity import QuantityType
        from astropy.coordinates import ICRS, CartesianRepresentation

        version = cls.version
        reference_frame = node['reference_frame']
        reference_frame_name = reference_frame['type']

        frame_cls = cls._get_reference_frame_mapping()[reference_frame_name]

        frame_kwargs = {}
        for name in frame_cls.get_frame_attr_names().keys():
            val = reference_frame.get(name)
            if val is not None:
                # These are deprecated fields that must be handled as a special
                # case for older versions of the schema
                if name in ['galcen_ra', 'galcen_dec']:
                    continue
                # There was no schema for quantities in v1.0.0
                if name in ['galcen_distance', 'roll', 'z_sun'] and version == '1.0.0':
                    val = Quantity(val[0], unit=val[1])
                # These fields are known to be CartesianRepresentations
                if name in ['obsgeoloc', 'obsgeovel']:
                    if version == '1.0.0':
                        unit = val[1]
                        x = Quantity(val[0][0], unit=unit)
                        y = Quantity(val[0][1], unit=unit)
                        z = Quantity(val[0][2], unit=unit)
                    else:
                        x = QuantityType.from_tree(val[0], ctx)
                        y = QuantityType.from_tree(val[1], ctx)
                        z = QuantityType.from_tree(val[2], ctx)
                    val = CartesianRepresentation(x, y, z)
                elif name == 'galcen_v_sun':
                    from astropy.coordinates import CartesianDifferential
                    # This field only exists since v1.1.0, and it only uses
                    # CartesianDifferential after v1.3.3
                    d_x = QuantityType.from_tree(val[0], ctx)
                    d_y = QuantityType.from_tree(val[1], ctx)
                    d_z = QuantityType.from_tree(val[2], ctx)
                    val = CartesianDifferential(d_x, d_y, d_z)
                else:
                    val = yamlutil.tagged_tree_to_custom_tree(val, ctx)
                frame_kwargs[name] = val
        has_ra_and_dec = reference_frame.get('galcen_dec') and \
            reference_frame.get('galcen_ra')
        if version == '1.0.0' and has_ra_and_dec:
            # Convert deprecated ra and dec fields into galcen_coord
            galcen_dec = reference_frame['galcen_dec']
            galcen_ra = reference_frame['galcen_ra']
            dec = Quantity(galcen_dec[0], unit=galcen_dec[1])
            ra = Quantity(galcen_ra[0], unit=galcen_ra[1])
            frame_kwargs['galcen_coord'] = ICRS(dec=dec, ra=ra)
        return frame_cls(**frame_kwargs)

    @classmethod
    def _from_tree(cls, node, ctx):
        kwargs = {'name': node['name']}

        if 'axes_names' in node:
            kwargs['axes_names'] = node['axes_names']

        if 'reference_frame' in node:
            kwargs['reference_frame'] = \
                cls._reference_frame_from_tree(node, ctx)

        if 'axes_order' in node:
            kwargs['axes_order'] = tuple(node['axes_order'])

        if 'unit' in node:
            kwargs['unit'] = tuple(
                yamlutil.tagged_tree_to_custom_tree(node['unit'], ctx))

        return kwargs

    @classmethod
    def _to_tree(cls, frame, ctx):
        import numpy as np
        from astropy.coordinates import CartesianRepresentation
        from astropy.io.misc.asdf.tags.unit.quantity import QuantityType
        from astropy.coordinates import CartesianDifferential

        node = {}

        node['name'] = frame.name

        if frame.axes_order != (0, 1):
            node['axes_order'] = list(frame.axes_order)

        if frame.axes_names is not None:
            node['axes_names'] = list(frame.axes_names)

        if frame.reference_frame is not None:
            reference_frame = {}
            reference_frame['type'] = cls._get_inverse_reference_frame_mapping()[
                type(frame.reference_frame)]

            for name in frame.reference_frame.get_frame_attr_names().keys():
                frameval = getattr(frame.reference_frame, name)
                # CartesianRepresentation becomes a flat list of x,y,z
                # coordinates with associated units
                if isinstance(frameval, CartesianRepresentation):
                    value = [frameval.x, frameval.y, frameval.z]
                    frameval = value
                elif isinstance(frameval, CartesianDifferential):
                    value = [frameval.d_x, frameval.d_y, frameval.d_z]
                    frameval = value
                yamlval = yamlutil.custom_tree_to_tagged_tree(frameval, ctx)
                reference_frame[name] = yamlval

            node['reference_frame'] = reference_frame

        if frame.unit is not None:
            node['unit'] = yamlutil.custom_tree_to_tagged_tree(
                list(frame.unit), ctx)

        return node

    @classmethod
    def _assert_equal(cls, old, new):
        from ...tests import helpers

        assert old.name == new.name
        assert old.axes_order == new.axes_order
        assert old.axes_names == new.axes_names
        assert type(old.reference_frame) == type(new.reference_frame)
        assert old.unit == new.unit

        if old.reference_frame is not None:
            for name in old.reference_frame.get_frame_attr_names().keys():
                helpers.assert_tree_match(
                    getattr(old.reference_frame, name),
                    getattr(new.reference_frame, name))

    @classmethod
    def assert_equal(cls, old, new):
        cls._assert_equal(old, new)

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        node = cls._from_tree(node, ctx)

        return gwcs.Frame2D(**node)

    @classmethod
    def to_tree(cls, frame, ctx):
        return cls._to_tree(frame, ctx)

class CelestialFrameType(FrameType):
    name = "wcs/celestial_frame"
    types = ['gwcs.CelestialFrame']
    supported_versions = [(1,0,0), (1,1,0)]

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        node = cls._from_tree(node, ctx)

        return gwcs.CelestialFrame(**node)

    @classmethod
    def to_tree(cls, frame, ctx):
        return cls._to_tree(frame, ctx)

    @classmethod
    def assert_equal(cls, old, new):
        cls._assert_equal(old, new)

        assert old.reference_position == new.reference_position


class SpectralFrame(FrameType):
    name = "wcs/spectral_frame"
    types = ['gwcs.SpectralFrame']

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        node = cls._from_tree(node, ctx)

        if 'reference_position' in node:
            node['reference_position'] = node['reference_position'].upper()

        return gwcs.SpectralFrame(**node)

    @classmethod
    def to_tree(cls, frame, ctx):
        node = cls._to_tree(frame, ctx)

        if frame.reference_position is not None:
            node['reference_position'] = frame.reference_position.lower()

        return node


class CompositeFrame(FrameType):
    name = "wcs/composite_frame"
    types = ['gwcs.CompositeFrame']
    version = '1.1.0'

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        if len(node) != 2:
            raise ValueError("CompositeFrame has extra properties")

        name = node['name']
        frames = node['frames']

        return gwcs.CompositeFrame(frames, name)

    @classmethod
    def to_tree(cls, frame, ctx):
        return {
            'name': frame.name,
            'frames': yamlutil.custom_tree_to_tagged_tree(frame.frames, ctx)
        }

    @classmethod
    def assert_equal(cls, old, new):
        from ...tests import helpers

        assert old.name == new.name
        for old_frame, new_frame in zip(old.frames, new.frames):
            helpers.assert_tree_match(old_frame, new_frame)

class ICRSCoord(AsdfType):
    """The newest version of this tag and the associated schema have  moved to
    Astropy. This implementation is retained here for the purposes of backwards
    compatibility with older files.
    """
    name = "wcs/icrs_coord"
    types = ['astropy.coordinates.ICRS']
    requires = ['astropy']
    version = "1.1.0"

    @classmethod
    def from_tree(cls, node, ctx):
        from astropy.io.misc.asdf.tags.unit.quantity import QuantityType
        from astropy.coordinates import ICRS, Longitude, Latitude, Angle

        angle = QuantityType.from_tree(node['ra']['wrap_angle'], ctx)
        wrap_angle = Angle(angle.value, unit=angle.unit)
        ra = Longitude(
            node['ra']['value'],
            unit=node['ra']['unit'],
            wrap_angle=wrap_angle)
        dec = Latitude(node['dec']['value'], unit=node['dec']['unit'])

        return ICRS(ra=ra, dec=dec)

    @classmethod
    def to_tree(cls, frame, ctx): # pragma: no cover
        # We do not run coverage analysis since new ICRS objects will be
        # serialized by the tag implementation in Astropy. Eventually if we
        # have a better way to write older versions of tags, we can re-add
        # tests for this code.
        from astropy.units import Quantity
        from astropy.coordinates import ICRS
        from astropy.io.misc.asdf.tags.unit.quantity import QuantityType

        node = {}

        wrap_angle = Quantity(
            frame.ra.wrap_angle.value,
            unit=frame.ra.wrap_angle.unit)
        node['ra'] = {
            'value': frame.ra.value,
            'unit': frame.ra.unit.to_string(),
            'wrap_angle': yamlutil.custom_tree_to_tagged_tree(wrap_angle, ctx)
        }
        node['dec'] = {
            'value': frame.dec.value,
            'unit': frame.dec.unit.to_string()
        }

        return node
