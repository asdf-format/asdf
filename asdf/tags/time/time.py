# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

import six

from ...asdftypes import AsdfType
from ... import yamlutil


_guessable_formats = set(['iso', 'byear', 'jyear', 'yday'])


_astropy_format_to_asdf_format = {
    'isot': 'iso',
    'byear_str': 'byear',
    'jyear_str': 'jyear'
}


class TimeType(AsdfType):
    name = 'time/time'
    types = ['astropy.time.core.Time']
    requires = ['astropy']

    @classmethod
    def to_tree(cls, node, ctx):
        from astropy import time

        format = node.format

        if format == 'byear':
            node = time.Time(node, format='byear_str')

        elif format == 'jyear':
            node = time.Time(node, format='jyear_str')

        elif format in ('fits', 'datetime', 'plot_date'):
            node = time.Time(node, format='isot')

        format = node.format

        format = _astropy_format_to_asdf_format.get(format, format)

        guessable_format = format in _guessable_formats

        if node.scale == 'utc' and guessable_format:
            if node.isscalar:
                return node.value
            else:
                return yamlutil.custom_tree_to_tagged_tree(
                    node.value, ctx)

        d = {'value': yamlutil.custom_tree_to_tagged_tree(node.value, ctx)}

        if not guessable_format:
            d['format'] = format

        if node.scale != 'utc':
            d['scale'] = node.scale

        if node.location is not None:
            d['location'] = {
                'x': node.location.x,
                'y': node.location.y,
                'z': node.location.z
            }

        return d

    @classmethod
    def from_tree(cls, node, ctx):
        from astropy import time
        from astropy import units as u

        if isinstance(node, (six.string_types, list, np.ndarray)):
            t = time.Time(node)
            format = _astropy_format_to_asdf_format.get(t.format, t.format)
            if format not in _guessable_formats:
                raise ValueError("Invalid time '{0}'".format(node))
            return t

        value = node['value']
        format = node.get('format')
        scale = node.get('scale')
        location = node.get('location')
        if location is not None:
            unit = location.get('unit', u.m)
            if 'x' in location:
                location = (location['x'] * unit,
                            location['y'] * unit,
                            location['z'] * unit)
            else:
                location = ('{0}d'.format(location['long']),
                            '{0}d'.format(location['lat']),
                            location.get('h', 0.0) * unit)

        return time.Time(value, format=format, scale=scale, location=location)

    @classmethod
    def assert_equal(cls, old, new):
        from numpy.testing import assert_array_equal

        assert old.format == new.format
        assert old.scale == new.scale
        assert old.location == new.location

        assert_array_equal(old, new)
