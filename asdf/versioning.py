"""
This module deals with things that change between different versions
of the ASDF spec.
"""

from functools import total_ordering

import yaml
from semantic_version import SimpleSpec, Version

_yaml_base_loader = yaml.CSafeLoader if getattr(yaml, "__with_libyaml__", None) else yaml.SafeLoader


__all__ = ["AsdfVersion", "AsdfSpec", "AsdfVersionMixin", "split_tag_version", "join_tag_version"]


def split_tag_version(tag):
    """
    Split a tag into its base and version.
    """
    name, version = tag.rsplit("-", 1)
    version = AsdfVersion(version)
    return name, version


def join_tag_version(name, version):
    """
    Join the root and version of a tag back together.
    """
    return f"{name}-{version}"


_version_map = {}


def get_version_map(version):
    version_map = _version_map.get(version)

    if version_map is None:
        from .config import get_config

        uri = f"http://stsci.edu/schemas/asdf/version_map-{version}"
        # The following call to yaml.load is safe because we're
        # using a loader that inherits from pyyaml's SafeLoader.
        version_map = yaml.load(get_config().resource_manager[uri], Loader=_yaml_base_loader)  # noqa: S506

        # Separate the core tags from the rest of the standard for convenience
        version_map["core"] = {}
        version_map["standard"] = {}
        for tag_name, tag_version in version_map["tags"].items():
            if tag_name.startswith("tag:stsci.edu:asdf/core"):
                version_map["core"][tag_name] = tag_version
            else:
                version_map["standard"][tag_name] = tag_version

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
            version = ".".join([str(x) for x in version])
        super().__init__(version)


class AsdfSpec(SimpleSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def match(self, version):
        if isinstance(version, (str, tuple, list)):
            version = AsdfVersion(version)
        return super().match(version)

    def __iterate_versions(self, versions):
        for v in versions:
            yield AsdfVersion(v) if isinstance(v, (str, tuple, list)) else v

    def select(self, versions):
        return super().select(self.__iterate_versions(versions))

    def filter(self, versions):  # noqa: A003
        return super().filter(self.__iterate_versions(versions))

    def __eq__(self, other):
        """Equality between Spec and Version, string, or tuple, means match"""
        if isinstance(other, SimpleSpec):
            return super().__eq__(other)
        return self.match(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()


supported_versions = [
    AsdfVersion("1.0.0"),
    AsdfVersion("1.1.0"),
    AsdfVersion("1.2.0"),
    AsdfVersion("1.3.0"),
    AsdfVersion("1.4.0"),
    AsdfVersion("1.5.0"),
    AsdfVersion("1.6.0"),
]


default_version = AsdfVersion("1.5.0")

# This is the ASDF Standard version that is currently in development
# it is possible that breaking changes will be made to this version.
asdf_standard_development_version = AsdfVersion("1.6.0")


# This is the ASDF Standard version at which the format of the history
# field changed to include extension metadata.
NEW_HISTORY_FORMAT_MIN_VERSION = AsdfVersion("1.2.0")


# This is the ASDF Standard version at which we begin restricting
# mapping keys to string, integer, and boolean only.
RESTRICTED_KEYS_MIN_VERSION = AsdfVersion("1.6.0")


# This library never removed defaults for ASDF Standard versions
# later than 1.5.0, so filling them isn't necessary.
FILL_DEFAULTS_MAX_VERSION = AsdfVersion("1.5.0")
