# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from ...asdftypes import AsdfType
from ... import yamlutil


_REQUIRES = ['gwcs', 'astropy']


class WCSType(AsdfType):
    name = "wcs/wcs"
    requires = _REQUIRES
    types = ['gwcs.WCS']
    version = '1.2.0'

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
    version = '1.2.0'


class FrameType(AsdfType):
    name = "wcs/frame"
    requires = ['gwcs']
    types = ['gwcs.Frame2D']
    version = '1.2.0'

    @classmethod
    def _from_tree(cls, node, ctx):
        kwargs = {'name': node['name']}

        if 'axes_names' in node:
            kwargs['axes_names'] = node['axes_names']

        if 'reference_frame' in node:
            kwargs['reference_frame'] = yamlutil.tagged_tree_to_custom_tree(node['reference_frame'], ctx)

        if 'axes_order' in node:
            kwargs['axes_order'] = tuple(node['axes_order'])

        if 'unit' in node:
            kwargs['unit'] = tuple(
                yamlutil.tagged_tree_to_custom_tree(node['unit'], ctx))

        return kwargs

    @classmethod
    def _to_tree(cls, frame, ctx):

        node = {}

        node['name'] = frame.name

        if frame.axes_order != (0, 1):
            node['axes_order'] = list(frame.axes_order)

        if frame.axes_names is not None:
            node['axes_names'] = list(frame.axes_names)

        if frame.reference_frame is not None:
            node['reference_frame'] = yamlutil.custom_tree_to_tagged_tree(frame.reference_frame, ctx)

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
        assert type(old.reference_frame) is type(new.reference_frame)
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
    supported_versions = [(1,0,0), (1,1,0), (1,2,0)]

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


class TemporalFrame(AsdfType):
    name = "wcs/temporal_frame"
    requires = ['gwcs']
    types = ['gwcs.coordinate_frames.TemporalFrame']
    version = '1.2.0'

    @classmethod
    def to_tree(cls, frame, ctx):
        import astropy.time

        node = {}

        node['name'] = frame.name

        if frame.axes_order != (0, 1):
            node['axes_order'] = list(frame.axes_order)

        if frame.axes_names is not None:
            node['axes_names'] = list(frame.axes_names)

        if frame.reference_frame is not None:
            if frame.reference_frame is not astropy.time.Time:
                raise ValueError("Can not save reference_frame unless it's Time")

        if frame.reference_position is not None:
            node['reference_time'] = yamlutil.custom_tree_to_tagged_tree(
                frame.reference_position, ctx)

        if frame.unit is not None:
            node['unit'] = yamlutil.custom_tree_to_tagged_tree(
                list(frame.unit), ctx)

        return node

    @classmethod
    def from_tree(cls, node, ctx):
        from gwcs.coordinate_frames import TemporalFrame as gTemporalFrame
        import astropy.time

        name = node['name']
        axes_order = node.get('axes_order', None)
        axes_names = node.get('axes_names', None)
        reference_frame = node.get('reference_frame', astropy.time.Time)
        reference_time = node.get('reference_time', None)
        unit = node.get('unit', None)

        return gTemporalFrame(axes_order, reference_time,
                              reference_frame, unit, axes_names, name)


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

# class ICRSCoord(AsdfType):
#     """The newest version of this tag and the associated schema have  moved to
#     Astropy. This implementation is retained here for the purposes of backwards
#     compatibility with older files.
#     """
#     name = "wcs/icrs_coord"
#     types = ['astropy.coordinates.ICRS']
#     requires = ['astropy']
#     version = "1.1.0"

#     @classmethod
#     def from_tree(cls, node, ctx):
#         from astropy.io.misc.asdf.tags.unit.quantity import QuantityType
#         from astropy.coordinates import ICRS, Longitude, Latitude, Angle

#         angle = QuantityType.from_tree(node['ra']['wrap_angle'], ctx)
#         wrap_angle = Angle(angle.value, unit=angle.unit)
#         ra = Longitude(
#             node['ra']['value'],
#             unit=node['ra']['unit'],
#             wrap_angle=wrap_angle)
#         dec = Latitude(node['dec']['value'], unit=node['dec']['unit'])

#         return ICRS(ra=ra, dec=dec)

#     @classmethod
#     def to_tree(cls, frame, ctx): # pragma: no cover
#         # We do not run coverage analysis since new ICRS objects will be
#         # serialized by the tag implementation in Astropy. Eventually if we
#         # have a better way to write older versions of tags, we can re-add
#         # tests for this code.
#         from astropy.units import Quantity
#         from astropy.coordinates import ICRS
#         from astropy.io.misc.asdf.tags.unit.quantity import QuantityType

#         node = {}

#         wrap_angle = Quantity(
#             frame.ra.wrap_angle.value,
#             unit=frame.ra.wrap_angle.unit)
#         node['ra'] = {
#             'value': frame.ra.value,
#             'unit': frame.ra.unit.to_string(),
#             'wrap_angle': yamlutil.custom_tree_to_tagged_tree(wrap_angle, ctx)
#         }
#         node['dec'] = {
#             'value': frame.dec.value,
#             'unit': frame.dec.unit.to_string()
#         }

#         return node
