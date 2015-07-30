# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import six


from ...asdftypes import AsdfType
from ... import yamlutil


_REQUIRES = ['gwcs', 'astropy']


class WCSType(AsdfType):
    name = "wcs/wcs"
    requires = _REQUIRES
    types = ['gwcs.WCS']

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        steps = [(x['frame'], x.get('transform')) for x in node['steps']]
        name = node['name']

        return gwcs.WCS(steps, name=name)

    @classmethod
    def to_tree(cls, gwcs, ctx):
        frames = gwcs.available_frames
        steps = []
        for i in range(len(frames) - 1):
            transform = gwcs.get_transform(frames[i], frames[i + 1])
            steps.append(StepType({'frame': frames[i], 'transform': transform}))
        steps.append(StepType({'frame': frames[-1]}))

        return {'name': gwcs.name,
                'steps': yamlutil.custom_tree_to_tagged_tree(steps, ctx)}

    @classmethod
    def assert_equal(cls, old, new):
        from ...tests import helpers

        assert old.name == new.name
        assert len(old.available_frames) == len(new.available_frames)
        for (old_frame, old_transform), (new_frame, new_transform) in zip(
                old._pipeline, new._pipeline):
            helpers.assert_tree_match(old_frame, new_frame)
            helpers.assert_tree_match(old_transform, new_transform)


class StepType(dict, AsdfType):
    name = "wcs/step"
    requires = _REQUIRES


class FrameType(AsdfType):
    name = "wcs/frame"
    requires = _REQUIRES

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
            'altaz': builtin_frames.AltAz,
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
        for key, val in six.iteritems(reference_frame_mapping):
            cls._inverse_reference_frame_mapping[val] = key

        return cls._inverse_reference_frame_mapping

    @classmethod
    def get_reference_frame(cls, name):
        return cls._get_reference_frame_mapping()[name]()

    @classmethod
    def get_reference_frame_name(cls, frame):
        return cls._get_inverse_reference_frame_mapping()[type(frame)]

    @classmethod
    def _from_tree(cls, node, ctx):
        node = dict(node)

        if 'reference_frame' in node:
            node['reference_frame'] = cls.get_reference_frame(node['reference_frame'])
        if 'axes_order' in node:
            node['axes_order'] = tuple(node['axes_order'])
        if 'unit' in node:
            node['unit'] = tuple(
                yamlutil.tagged_tree_to_custom_tree(node['unit'], ctx))

        return node

    @classmethod
    def _to_tree(cls, frame, ctx):
        node = {}

        node['name'] = frame.name
        if frame.axes_order != (0, 1):
            node['axes_order'] = list(frame.axes_order)
        if frame.axes_names is not None:
            node['axes_names'] = list(frame.axes_names)
        if frame.reference_frame is not None:
            node['reference_frame'] = cls.get_reference_frame_name(
                frame.reference_frame)
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

    @classmethod
    def assert_equal(cls, old, new):
        cls._assert_equal(old, new)


class CelestialFrameType(FrameType):
    name = "wcs/celestial_frame"
    types = ['gwcs.CelestialFrame']

    @classmethod
    def from_tree(cls, node, ctx):
        import gwcs

        node = cls._from_tree(node, ctx)

        if 'reference_position' in node:
            node['reference_position'] = node['reference_position'].upper()

        return gwcs.CelestialFrame(**node)

    @classmethod
    def to_tree(cls, frame, ctx):
        node = cls._to_tree(frame, ctx)

        if frame.reference_position is not None:
            node['reference_position'] = frame.reference_position.lower()

        return node

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

        return gwcs.SpectralFrame(**node)

    @classmethod
    def to_tree(cls, frame, ctx):
        return cls._to_tree(frame, ctx)


class CompositeFrame(FrameType):
    name = "wcs/composite_frame"
    types = ['gwcs.CompositeFrame']

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
