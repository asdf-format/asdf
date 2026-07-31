from __future__ import annotations

from typing import TYPE_CHECKING

from . import versioning
from ._version import version as asdf_package_version

if TYPE_CHECKING:
    from asdf.versioning import AsdfVersion


def validate_version(version: str | AsdfVersion) -> str:
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
