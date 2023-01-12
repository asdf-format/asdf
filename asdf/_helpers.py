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
