# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
This module deals with things that change between different versions
of the ASDF spec.
"""

from __future__ import absolute_import, division, unicode_literals, print_function

import six

from . import util


def version_to_string(ver):
    return '.'.join(str(x) for x in ver)


default_version = (0, 1, 0)


class VersionSpec(object):
    """
    There is a subclass of `VersionSpec` for each version of the ASDF
    specification.  It declares things that are different between each
    version, such as the YAML version used.
    """
    yaml_version = (1, 1)
    organization = 'stsci.edu'

    @property
    def version_string(self):
        return version_to_string(self.version)


class VersionSpec_0_1_0(VersionSpec):
    version = (0, 1, 0)


versions = {
    (0, 1, 0): VersionSpec_0_1_0()
    }


class VersionedMixin(object):
    _version = default_version

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, val):
        if isinstance(val, bytes):
            try:
                val = tuple(int(x) for x in val.split('.'))
            except:
                pass

        if (not isinstance(val, tuple) or
            len(val) != 3 or
            any(not isinstance(x, int) for x in val)):
            raise TypeError("version must be a 3-tuple or byte string")

        if val not in versions:
            human_versions = util.human_list(
                [version_to_string(x) for x in six.iterkeys(versions)])
            raise ValueError(
                "pyasdf only understands how to handle ASDF versions {0}. "
                "Got '{1}'".format(
                    human_versions,
                    version_to_string(val)))

        self._version = val

    @property
    def version_string(self):
        return version_to_string(self._version)

    @property
    def versionspec(self):
        return versions[self._version]
