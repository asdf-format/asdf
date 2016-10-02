# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
This module deals with things that change between different versions
of the ASDF spec.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

import six

import yaml

if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_loader = yaml.SafeLoader

from .extern import semver

from . import generic_io
from . import resolver
from . import util


_version_map = {}
def get_version_map(version):
    version_map = _version_map.get(version)

    if version_map is None:
        version_map_path = resolver.DEFAULT_URL_MAPPING[0][1].replace(
            '{url_suffix}', 'asdf/version_map-{0}'.format(version))
        try:
            with generic_io.get_file(version_map_path, 'r') as fd:
                version_map = yaml.load(
                    fd, Loader=_yaml_base_loader)
        except:
            version_string = version_to_string(version)
            raise ValueError(
                "Could not load version map for version {0}".format(version_string))
        _version_map[version] = version_map

    return version_map


def version_to_string(ver):
    if isinstance(ver, six.string_types):
        return ver
    elif isinstance(ver, dict):
        return semver.format_version(**ver)
    elif isinstance(ver, (tuple, list)):
        return semver.format_version(*ver)
    else:
        raise TypeError("Bad type for version {0}".format(ver))


default_version = semver.parse('1.0.0')


supported_versions = [
    '1.0.0'
]


class VersionedMixin(object):
    _version = default_version
    _version_string = version_to_string(default_version)

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        if version_to_string(version) not in supported_versions:
            human_versions = util.human_list(
                [version_to_string(x) for x in supported_versions])
            raise ValueError(
                "asdf only understands how to handle ASDF versions {0}. "
                "Got '{1}'".format(
                    human_versions,
                    version_to_string(version)))

        self._version = version
        self._version_string = version_to_string(version)

    @property
    def version_string(self):
        return self._version_string

    @property
    def version_map(self):
        try:
            version_map = get_version_map(self.version_string)
        except ValueError:
            raise ValueError(
                "Don't have information about version {0}".format(
                    self.version_string))
        return version_map
