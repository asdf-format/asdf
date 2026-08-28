"""
Helpers for writing unit tests of ASDF support.
"""

from contextlib import contextmanager
from io import BytesIO

import asdf

__all__ = ["config", "roundtrip_object", "yaml_to_asdf"]


@contextmanager
def config(**kwargs):
    """Temporarily set config values via keyword argument.

    Can be used as a context manager or as a function decorator.
    """

    with asdf.config_context() as cfg:
        for key, val in kwargs.items():
            setattr(cfg, key, val)
        yield cfg


def roundtrip_object(obj, version=None):
    """
    Add the specified object to an AsdfFile's tree, write the file to
    a buffer, then read it back in and return the deserialized object.

    Parameters
    ----------
    obj : object
        Object to serialize.
    version : str or None.
        ASDF Standard version.  If None, use the library's default version.

    Returns
    -------
    object
        The deserialized object.
    """
    buff = BytesIO()
    with asdf.AsdfFile(version=version) as af:
        af["obj"] = obj
        af.write_to(buff)

    buff.seek(0)
    with asdf.open(buff, lazy_load=False, memmap=False) as af:
        return af["obj"]


def yaml_to_asdf(yaml_content, version=None):
    """
    Given a string of YAML content, adds the extra pre-
    and post-amble to make it an ASDF file.

    Parameters
    ----------
    yaml_content : string or bytes
        YAML content.
    version : str or None.
        ASDF Standard version.  If None, use the library's default version.

    Returns
    -------
    io.BytesIO
        A file-like object containing the ASDF file.
    """
    if isinstance(yaml_content, str):
        yaml_content = yaml_content.encode("utf-8")

    buff = BytesIO()
    with asdf.AsdfFile(version=version) as af:
        af["$REPLACE"] = "ME"
        af.write_to(buff)

    buff.seek(0)
    asdf_content = buff.read().replace(b"$REPLACE: ME", yaml_content)

    return BytesIO(asdf_content)
