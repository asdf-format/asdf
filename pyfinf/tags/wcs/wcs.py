# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy import modeling
from astropy import units as u

from ...finftypes import FinfType


__all__ = ['WcsType', 'StepsType']


class WcsType(dict, FinfType):
    name = "wcs/wcs"

    def __init__(self, forward=None, backward=None):
        if forward is not None:
            self['forward'] = forward
        if backward is not None:
            self['backward'] = backward

    @property
    def forward(self):
        if 'forward' in self:
            return self['forward']
        elif 'backward' in self:
            try:
                return self['backward'].inverse()
            except NotImplementedError:
                raise AttributeError(
                    "WCS does not have a forward transform, "
                    "and one can not be automatically inverted from backward.")
        else:
            # TODO: Technically, the schema should prevent this case
            # from ever happening.
            raise AttributeError(
                "WCS does not have a forward or backward transform")

    @property
    def backward(self):
        if 'backward' in self:
            return self['backward']
        elif 'forward' in self:
            try:
                return self['forward'].inverse()
            except NotImplementedError:
                raise AttributeError(
                    "WCS does not have a backward transform, "
                    "and one can not be automatically inverted from forward.")
        else:
            # TODO: Technically, the schema should prevent this case
            # from ever happening.
            raise AttributeError(
                "WCS does not have a forward or backward transform")


class Steps(modeling.SerialCompositeModel):
    def __init__(self, names, transforms, frames=None, units=None):
        if frames is None:
            frames = [None] * (len(transforms) + 1)

        if units is None:
            units = [None] * (len(transforms) + 1)

        if (len(transforms) != len(frames) - 1 or
            len(frames) != len(units) or
            len(frames) != len(names)):
            raise ValueError(
                "len(transforms) must be one less than len(frames), "
                "and len(names) === len(frames) === len(units)")

        super(Steps, self).__init__(transforms)
        self._names = names
        self._frames = frames
        self._units = units

    @property
    def names(self):
        return self._names

    @property
    def frames(self):
        return self._frames

    @property
    def units(self):
        return self._units


class StepsType(FinfType):
    name = "wcs/steps"
    types = [Steps]

    @classmethod
    def from_tree(cls, node, ctx):
        if node[-1].transform is not None:
            raise ValueError("The final WCS step should not have a transform")

        names = [x.name for x in node]
        transforms = [x.transform for x in node[:-1]]
        frames = [x.frames for x in node]
        units = [x.units for x in node]

        return Steps(names, transforms, frames, units)

    @classmethod
    def to_tree(cls, data, ctx):
        result = []
        for i in xrange(len(data.transforms)):
            subresult = ctx.to_tree(_StepType(
                data.names[i], data.frames[i],
                data.units[i], data.transforms[i]))
            result.append(subresult)

        i = len(data.transforms)
        result.append(ctx.to_tree(_StepType(
            data.names[i], data.frames[i], data.units[i])))

        return result


class _StepType(FinfType):
    name = "wcs/step"

    def __init__(self, name, frames, units, transform=None):
        self._name = name
        self._frames = frames
        if units is not None:
            new_units = []
            for unit in units:
                if unit is None:
                    new_units.append(None)
                else:
                    new_units.append(u.Unit(unit, format='vounit'))
        self._units = units
        self._transform = transform

    @property
    def step_name(self):
        return self._name

    @property
    def frames(self):
        return self._frames

    @property
    def units(self):
        return self._units

    @property
    def transform(self):
        return self._transform

    @classmethod
    def from_tree(cls, node, ctx):
        return cls(
            node['name'],
            node.get('frames', []),
            node.get('units', []),
            node.get('transform', None))

    @classmethod
    def to_tree(cls, data, ctx):
        result = {'name': ctx.to_tree(data.name)}
        if data.frames:
            result['frames'] = ctx.to_tree(data.frames)
        if data.units:
            result['units'] = ctx.to_tree(data.units)
        if data.transform:
            result['transform'] = ctx.to_tree(data.transform)
        return result
