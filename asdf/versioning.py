# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
This module deals with things that change between different versions
of the ASDF spec.
"""

import yaml
from functools import total_ordering

if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_loader = yaml.SafeLoader

from semantic_version import Version, SpecItem, Spec

from . import generic_io
from . import resolver
from . import util


__all__ = ['AsdfVersion', 'AsdfSpec']


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
            raise ValueError(
                "Could not load version map for version {0}".format(version))
        _version_map[version] = version_map

    return version_map


@total_ordering
class AsdfVersionMixin(object):
    """This mix-in is required in order to impose the total ordering that we
    want for ``AsdfVersion``, rather than accepting the total ordering that is
    already provided by ``Version`` from ``semantic_version``. Defining these
    comparisons directly in ``AsdfVersion`` and applying ``total_ordering``
    there will not work since ``total_ordering`` only defines comparison
    operations if they do not exist already and the base class ``Version``
    already defines these operations.
    """

    def __eq__(self, other):
        # Seems like a bit of a hack...
        if isinstance(other, SpecItem):
            return other == self
        if isinstance(other, (str, tuple, list)):
            other = AsdfVersion(other)
        return Version.__eq__(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, (str, tuple, list)):
            other = AsdfVersion(other)
        return Version.__lt__(self, other)

    def __hash__(self):
        # To be honest, I'm not sure why I had to make this explicit
        return Version.__hash__(self)


class AsdfVersion(AsdfVersionMixin, Version):
    """This class adds features to the existing ``Version`` class from the
    ``semantic_version`` module. Namely, it allows ``Version`` objects to be
    constructed from tuples and lists as well as strings, and it allows
    ``Version`` objects to be compared with tuples, lists, and strings, instead
    of just other ``Version`` objects.

    If any of these features are added to the ``Version`` class itself (as
    requested in https://github.com/rbarrois/python-semanticversion/issues/52),
    then this class will become obsolete.
    """

    def __init__(self, version):
        # This is a dirty hack and you know it
        if isinstance(version, AsdfVersion):
            version = str(version)
        if isinstance(version, (tuple, list)):
            version = '.'.join([str(x) for x in version])
        super(AsdfVersion, self).__init__(version)


class AsdfSpec(SpecItem, Spec):

    def __init__(self, *args, **kwargs):
        super(AsdfSpec, self).__init__(*args, **kwargs)

    def match(self, version):
        if isinstance(version, (str, tuple, list)):
            version = AsdfVersion(version)
        return super(AsdfSpec, self).match(version)

    def __iterate_versions(self, versions):
        for v in versions:
            if isinstance(v, (str, tuple, list)):
                v = AsdfVersion(v)
            yield v

    def select(self, versions):
        return super(AsdfSpec, self).select(self.__iterate_versions(versions))

    def filter(self, versions):
        return super(AsdfSpec, self).filter(self.__iterate_versions(versions))

    def __eq__(self, other):
        """Equality between Spec and Version, string, or tuple, means match"""
        if isinstance(other, SpecItem):
            return super(AsdfSpec, self).__eq__(other)
        return self.match(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super(AsdfSpec, self).__hash__()


default_version = AsdfVersion('1.2.0')


supported_versions = [
    AsdfVersion('1.0.0'),
    AsdfVersion('1.1.0'),
    AsdfVersion('1.2.0')
]


class VersionedMixin(object):
    _version = default_version

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        if version not in supported_versions:
            human_versions = util.human_list(
                [str(x) for x in supported_versions])
            raise ValueError(
                "asdf only understands how to handle ASDF versions {0}. "
                "Got '{1}'".format(human_versions, version))

        self._version = version

    @property
    def version_string(self):
        return str(self._version)

    @property
    def version_map(self):
        try:
            version_map = get_version_map(self.version_string)
        except ValueError:
            raise ValueError(
                "Don't have information about version {0}".format(
                    self.version_string))
        return version_map
