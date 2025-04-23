import enum
import importlib.util
import inspect
import math
import re
import struct
import sys
from functools import lru_cache

import numpy as np
import yaml

from . import constants

# The standard library importlib.metadata returns duplicate entrypoints
# for all python versions up to and including 3.11
# https://github.com/python/importlib_metadata/issues/410#issuecomment-1304258228
# see PR https://github.com/asdf-format/asdf/pull/1260
# see issue https://github.com/asdf-format/asdf/issues/1254
if sys.version_info >= (3, 12):
    pass
else:
    pass


# We're importing our own copy of urllib.parse because
# we need to patch it to support asdf:// URIs, but it'd
# be irresponsible to do this for all users of a
# standard library.
urllib_parse_spec = importlib.util.find_spec("urllib.parse")
_patched_urllib_parse = importlib.util.module_from_spec(urllib_parse_spec)
urllib_parse_spec.loader.exec_module(_patched_urllib_parse)
del urllib_parse_spec

# urllib.parse needs to know that it should treat asdf://
# URIs like http:// URIs for the purposes of joining
# a relative path to a base URI.
_patched_urllib_parse.uses_relative.append("asdf")
_patched_urllib_parse.uses_netloc.append("asdf")


__all__ = [
    "FileType",
    "NotSet",
    "calculate_padding",
    "get_array_base",
    "get_base_uri",
    "get_class_name",
    "get_file_type",
    "load_yaml",
    "uri_match",
]


def load_yaml(init, tagged=False):
    """
    Load just the yaml portion of an ASDF file

    Parameters
    ----------

    init : filename or file-like
        If file-like this must be opened in binary mode.

    tagged: bool, optional
        Return tree with instances of `asdf.tagged.Tagged` this
        can be helpful if the yaml tags are of interest.
        If False, the tree will only contain basic python types
        (see the pyyaml ``BaseLoader`` documentation).

    Returns
    -------

    tree : dict
        Dictionary representing the ASDF tree
    """

    from .generic_io import get_file
    from .yamlutil import AsdfLoader, _IgnoreCustomTagsLoader

    if tagged:
        loader = AsdfLoader
    else:
        loader = _IgnoreCustomTagsLoader

    with get_file(init, "r") as gf:
        reader = gf.reader_until(
            constants.YAML_END_MARKER_REGEX,
            7,
            "End of YAML marker",
            include=True,
        )
        # The following call to yaml.load is safe because we're
        # using only loaders that don't create custom python objects
        content = yaml.load(reader, Loader=loader)  # noqa: S506
    return content


def get_array_base(arr):
    """
    For a given Numpy array, finds the base array that "owns" the
    actual data.
    """
    from .tags.core import ndarray

    base = arr
    while isinstance(base.base, (np.ndarray, ndarray.NDArrayType)):
        base = base.base
    return base


def get_base_uri(uri):
    """
    For a given URI, return the part without any fragment.
    """
    parts = _patched_urllib_parse.urlparse(uri)
    return _patched_urllib_parse.urlunparse([*list(parts[:5]), ""])


def _iter_subclasses(cls):
    """
    Returns all subclasses of a class.
    """
    for x in cls.__subclasses__():
        yield x
        yield from _iter_subclasses(x)


def calculate_padding(content_size, pad_blocks, block_size):
    """
    Calculates the amount of extra space to add to a block given the
    user's request for the amount of extra space.  Care is given so
    that the total of size of the block with padding is evenly
    divisible by block size.

    Parameters
    ----------
    content_size : int
        The size of the actual content

    pad_blocks : float or bool
        If `False`, add no padding (always return 0).  If `True`, add
        a default amount of padding of 10% If a float, it is a factor
        to multiple content_size by to get the new total size.

    block_size : int
        The filesystem block size to use.

    Returns
    -------
    nbytes : int
        The number of extra bytes to add for padding.
    """
    if not pad_blocks:
        return 0
    if pad_blocks is True:
        pad_blocks = 1.1
    new_size = content_size * pad_blocks
    new_size = int((math.ceil(float(new_size) / block_size) + 1) * block_size)
    return max(new_size - content_size, 0)


class _BinaryStruct:
    """
    A wrapper around the Python stdlib struct module to define a
    binary struct more like a dictionary than a tuple.
    """

    def __init__(self, descr, endian=">"):
        """
        Parameters
        ----------
        descr : list of tuple
            Each entry is a pair ``(name, format)``, where ``format``
            is one of the format types understood by `struct`.

        endian : str, optional
            The endianness of the struct.  Must be ``>`` or ``<``.
        """
        self._fmt = [endian]
        self._offsets = {}
        self._names = []
        i = 0
        for name, fmt in descr:
            self._fmt.append(fmt)
            self._offsets[name] = (i, (endian + fmt).encode("ascii"))
            self._names.append(name)
            i += struct.calcsize(fmt.encode("ascii"))
        self._fmt = "".join(self._fmt).encode("ascii")
        self._size = struct.calcsize(self._fmt)

    @property
    def size(self):
        """
        Return the size of the struct.
        """
        return self._size

    def pack(self, **kwargs):
        """
        Pack the given arguments, which are given as kwargs, and
        return the binary struct.
        """
        fields = [0] * len(self._names)
        for key, val in kwargs.items():
            if key not in self._offsets:
                msg = f"No header field '{key}'"
                raise KeyError(msg)
            i = self._names.index(key)
            fields[i] = val
        return struct.pack(self._fmt, *fields)

    def unpack(self, buff):
        """
        Unpack the given binary buffer into the fields.  The result
        is a dictionary mapping field names to values.
        """
        args = struct.unpack_from(self._fmt, buff[: self._size])
        return dict(zip(self._names, args))

    def update(self, fd, **kwargs):
        """
        Update part of the struct in-place.

        Parameters
        ----------
        fd : generic_io.GenericIO instance
            A writable, seekable file descriptor, currently seeked
            to the beginning of the struct.

        **kwargs : values
            The values to update on the struct.
        """
        updates = []
        for key, val in kwargs.items():
            if key not in self._offsets:
                msg = f"No header field '{key}'"
                raise KeyError(msg)
            updates.append((self._offsets[key], val))
        updates.sort()

        start = fd.tell()
        for (offset, datatype), val in updates:
            fd.seek(start + offset)
            fd.write(struct.pack(datatype, val))


class HashableDict(dict):
    """
    A simple wrapper around dict to make it hashable.

    This is sure to be slow, but for small dictionaries it shouldn't
    matter.
    """

    def __hash__(self):
        return hash(frozenset(self.items()))


def get_class_name(obj, instance=True):
    """
    Given a class or instance of a class, returns a string representing the
    fully specified path of the class.

    Parameters
    ----------

    obj : object
        An instance of any object
    instance: bool
        Indicates whether given object is an instance of the class to be named
    """
    typ = type(obj) if instance else obj
    return f"{typ.__module__}.{typ.__qualname__}"


class _InheritDocstrings(type):
    """
    This metaclass makes methods of a class automatically have their
    docstrings filled in from the methods they override in the base
    class.

    If the class uses multiple inheritance, the docstring will be
    chosen from the first class in the bases list, in the same way as
    methods are normally resolved in Python.  If this results in
    selecting the wrong docstring, the docstring will need to be
    explicitly included on the method.

    For example::

        >>> from asdf.util import _InheritDocstrings
        >>> class A(metaclass=_InheritDocstrings):
        ...     def wiggle(self):
        ...         "Wiggle the thingamajig"
        ...         pass
        >>> class B(A):
        ...     def wiggle(self):
        ...         pass
        >>> B.wiggle.__doc__
        'Wiggle the thingamajig'
    """

    def __init__(cls, name, bases, dct):
        def is_public_member(key):
            return (key.startswith("__") and key.endswith("__") and len(key) > 4) or not key.startswith("_")

        for key, val in dct.items():
            if inspect.isfunction(val) and is_public_member(key) and val.__doc__ is None:
                for base in cls.__mro__[1:]:
                    super_method = getattr(base, key, None)
                    if super_method is not None:
                        val.__doc__ = super_method.__doc__
                        break

        super().__init__(name, bases, dct)


class _NotSetType:
    def __repr__(self):
        return "NotSet"


"""
Special value indicating that a parameter is not set.  Distinct
from None, which may for example be a value of interest in a search.
"""
NotSet = _NotSetType()


def uri_match(pattern, uri):
    """
    Determine if a URI matches a URI pattern with possible
    wildcards.  The two recognized wildcards:

    "*":  match any character except /

    "**": match any character

    Parameters
    ----------
    pattern : str
        URI pattern.
    uri : str
        URI to check against the pattern.

    Returns
    -------
    bool
        `True` if URI matches the pattern.
    """
    if not isinstance(uri, str):
        return False

    if "*" in pattern:
        return _compile_uri_match_pattern(pattern).fullmatch(uri) is not None

    return pattern == uri


@lru_cache(1024)
def _compile_uri_match_pattern(pattern):
    # Escape the pattern in case it contains regex special characters
    # ('.' in particular is common in URIs) and then replace the
    # escaped asterisks with the appropriate regex matchers.
    pattern = re.escape(pattern)
    pattern = pattern.replace(r"\*\*", r".*")
    pattern = pattern.replace(r"\*", r"[^/]*")
    return re.compile(pattern)


def get_file_type(fd):
    """
    Determine the file type of an open GenericFile instance.

    Parameters
    ----------

    fd : ``asdf.generic_io.GenericFile``

    Returns
    -------

    `asdf.util.FileType`
    """
    if fd.peek(5) == constants.ASDF_MAGIC:
        return FileType.ASDF

    if fd.peek(6) == constants.FITS_MAGIC:
        return FileType.FITS

    return FileType.UNKNOWN


class FileType(enum.Enum):
    """
    Enum representing if a file is ASDF, FITS or UNKNOWN.
    """

    ASDF = 1
    FITS = 2
    UNKNOWN = 3
