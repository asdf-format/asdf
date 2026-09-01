from functools import cached_property
from typing import Any

from . import versioning
from ._version import version as asdf_package_version


def validate_version(version):
    # Account for the possibility of AsdfVersion
    version = str(version)
    if version not in versioning.supported_versions:
        msg = "ASDF Standard version {} is not supported by asdf=={}.  Available ASDF Standard versions: {}".format(
            version,
            asdf_package_version,
            ", ".join(str(v) for v in versioning.supported_versions),
        )
        raise ValueError(msg)
    return version


class _IsSet:
    """Base class that tracks when its attributes are set.

    Attributes are only considered set when they have been *re-assigned* after initially being created.
    """

    @cached_property
    def _is_set(self):
        return set()

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, name):
            self._is_set.add(name)

        super().__setattr__(name, value)


def is_set(obj: _IsSet, attr: str) -> bool:
    """Get whether `attr` has been set on `obj`."""
    if not isinstance(obj, _IsSet):
        msg = f"Object with type {type(obj).__name__} is not an instance of _IsSet"
        raise TypeError(msg)
    if not hasattr(obj, attr):
        raise AttributeError(attr)

    return attr in obj._is_set
