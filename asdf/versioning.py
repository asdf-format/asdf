# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

"""
This module deals with things that change between different versions
of the ASDF spec.
"""

from functools import total_ordering

import yaml

if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_loader = yaml.SafeLoader

from semantic_version import Version, SimpleSpec

from . import generic_io
from . import resolver
from . import util
from .version import version as asdf_version


__all__ = ['AsdfVersion', 'AsdfSpec', 'split_tag_version', 'join_tag_version']


def split_tag_version(tag):
    """
    Split a tag into its base and version.
    """
    name, version = tag.rsplit('-', 1)
    version = AsdfVersion(version)
    return name, version


def join_tag_version(name, version):
    """
    Join the root and version of a tag back together.
    """
    return '{0}-{1}'.format(name, version)


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
        except Exception:
            raise ValueError(
                "Could not load version map for version {0}".format(version))

        # Separate the core tags from the rest of the standard for convenience
        version_map['core'] = {}
        version_map['standard'] = {}
        for name, version in version_map['tags'].items():
            if name.startswith('tag:stsci.edu:asdf/core'):
                version_map['core'][name] = version
            else:
                version_map['standard'][name] = version

        _version_map[version] = version_map

    return version_map


@total_ordering
class AsdfVersionMixin:
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
        if isinstance(other, SimpleSpec):
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


class AsdfSpec(SimpleSpec):

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
        if isinstance(other, SimpleSpec):
            return super(AsdfSpec, self).__eq__(other)
        return self.match(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super(AsdfSpec, self).__hash__()


supported_versions = [
    AsdfVersion('1.0.0'),
    AsdfVersion('1.1.0'),
    AsdfVersion('1.2.0'),
    AsdfVersion('1.3.0'),
    AsdfVersion('1.4.0'),
    AsdfVersion('1.5.0'),
]

default_version = supported_versions[-1]


class VersionedMixin:
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
                "This version of the asdf package ({0}) only understands how "
                "to handle versions {1} of the ASDF Standard. Got "
                "'{2}'".format(asdf_version, human_versions, version))

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


# This is the ASDF Standard version at which the format of the history
# field changed to include extension metadata.
NEW_HISTORY_FORMAT_MIN_VERSION = AsdfVersion("1.2.0")
