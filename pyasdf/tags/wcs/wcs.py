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


class FrameType(AsdfType):
    name = "wcs/frame"
    requires = _REQUIRES
    types = ['gwcs.Frame2D']

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
        for key, val in six.iteritems(reference_frame_mapping):
            cls._inverse_reference_frame_mapping[val] = key

        return cls._inverse_reference_frame_mapping

    @classmethod
    def _from_tree(cls, node, ctx):
        from astropy import units as u

        kwargs = {}

        kwargs['name'] = node['name']

        if 'axes_names' in node:
            kwargs['axes_names'] = node['axes_names']

        if 'reference_frame' in node:
            reference_frame = node['reference_frame']
            reference_frame_name = reference_frame['type']

            frame_cls = cls._get_reference_frame_mapping()[reference_frame_name]

            frame_kwargs = {}
            for name in frame_cls.get_frame_attr_names().keys():
                val = reference_frame.get(name)
                if val is not None:
                    if isinstance(val, list):
                        val = u.Quantity(val[0], unit=val[1])
                    else:
                        val = yamlutil.tagged_tree_to_custom_tree(val, ctx)
                    frame_kwargs[name] = val

            kwargs['reference_frame'] = frame_cls(**frame_kwargs)

        if 'axes_order' in node:
            kwargs['axes_order'] = tuple(node['axes_order'])

        if 'unit' in node:
            kwargs['unit'] = tuple(
                yamlutil.tagged_tree_to_custom_tree(node['unit'], ctx))

        return kwargs

    @classmethod
    def _to_tree(cls, frame, ctx):
        from astropy import units as u
        import numpy as np

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
                val = getattr(frame.reference_frame, name)
                if isinstance(val, u.Quantity):
                    value = val.value
                    if not np.isscalar(value):
                        value = list(val.value)
                    val = [value, val.unit]
                val = yamlutil.custom_tree_to_tagged_tree(val, ctx)
                reference_frame[name] = val

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
