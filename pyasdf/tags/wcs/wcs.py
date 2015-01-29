# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


from ...asdftypes import AsdfType
from ... import yamlutil


class GWCSAxis(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class GWCSStep(object):
    def __init__(self, name, axes, transform):
        self.name = name
        self.axes = axes
        self.transform = transform


class GWCS(object):
    def __init__(self, steps):
        self.steps = steps
        self.transform = steps[0].transform
        for step in steps[1:-1]:
            self.transform = self.transform | step.transform

        if self.steps[-1].transform is not None:
            raise ValueError("Last WCS step must not have a transform defined")


class AxisType(AsdfType):
    name = "wcs/axis"
    types = [GWCSAxis]

    @classmethod
    def from_tree(cls, node, ctx):
        return GWCSAxis(**node)

    @classmethod
    def to_tree(cls, axis, ctx):
        node = {}
        try:
            node['type'] = axis.type
        except AttributeError:
            raise ValueError("axis must have a type")

        try:
            node['name'] = axis.name
        except AttributeError:
            raise ValueError("axis must have a name")

        if getattr(axis, 'celestial_type', 'ICRS') != 'ICRS':
            node['celestial_type'] = axis.celestial_type

        if getattr(axis, 'equinox', 'J2000') != 'J2000':
            node['equinox'] = axis.equinox

        # TODO: observation_time, once we have "time"

        if getattr(axis, 'time_scale') is not None:
            node['time_scale'] = axis.time_scale

        # TODO: spectral_type

        return node


class GWCSType(AsdfType):
    name = "wcs/wcs"
    types = [GWCS]

    @classmethod
    def from_tree(cls, node, ctx):
        steps = []
        for step in node['steps']:
            name = step['name']
            axis = step.get('axis')
            if axis is not None:
                axis = yamlutil.tagged_tree_to_custom_tree(axis, ctx)
            transform = step.get('transform')
            if transform is not None:
                transform = yamlutil.tagged_tree_to_custom_tree(transform, ctx)
            steps.append(GWCSStep(name, axis, transform))

        return GWCS(steps)

    @classmethod
    def to_tree(cls, wcs, ctx):
        steps = []
        for step in wcs.steps:
            node = {'name': step.name}
            if step.axis is not None:
                node['axis'] = yamlutil.custom_tree_to_tagged_tree(
                    step.axis, ctx)
            if step.transform is not None:
                node['transform'] = yamlutil.custom_tree_to_tagged_tree(
                    step.transform, ctx)
            steps.append(node)
        return {'steps': steps}
