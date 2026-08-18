import enum
import importlib.util
import math
import re
import struct
import warnings
from functools import lru_cache
from typing import Final, Generic

import numpy as np
import yaml
from typing_extensions import TypeVar

from asdf.exceptions import ChangingDefaultWarning

from . import constants

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
    "NOT_SET",
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


def calculate_padding(content_size: int, pad_blocks: float | bool | None, block_size: int) -> int:
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


class _NOT_SET_TYPE(enum.Enum):
    NOT_SET = "NotSet"

    def __repr__(self) -> str:
        return str(self.value)


#: Special value indicating that a parameter is not set.
#: Distinct from None, which may for example be a value of interest in a search.
NOT_SET: Final = _NOT_SET_TYPE.NOT_SET
NotSet: Final = NOT_SET


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


_T = TypeVar("_T")


# Adapted from https://docs.python.org/3/howto/descriptor.html#properties
class _ChangingDefault(Generic[_T]):
    """See `changing_default`."""

    def __init__(
        self,
        prop,
        new_default: _T,
        warning: type[ChangingDefaultWarning],
    ):
        self._prop = prop
        self.__doc__ = self._prop.__doc__
        self.new_default = new_default
        self.warning = warning

        self.is_set = False

    def __set_name__(self, owner, name):
        self.__name__ = name

    def __get__(self, obj, objtype=None):
        value = self._prop.__get__(obj, objtype)

        if not self.is_set:
            old_default = value
            # Using the actual class here so if the name changes it doesn't get missed
            cls = ChangingDefaultWarning.__name__
            msg = (
                f"In the future the default for {self.__name__} will be {self.new_default} "
                f"instead of the current default of {old_default}. "
                f"Explicitly pass {self.new_default} or {old_default} to silence this warning, "
                f'or use warnings.simplefilter("ignore", {cls}) to silence all changing default warnings.'
            )
            warnings.warn(msg, self.warning, stacklevel=2)
        return value

    def __set__(self, obj, value):
        self.is_set = True
        return self._prop.__set__(obj, value)

    def __delete__(self, obj):
        self._prop.__delete__(obj)

    def getter(self, fget):
        self._prop = type(self._prop)(fget, self._prop.fset, self._prop.fdel, self.__doc__)
        return self

    def setter(self, fset):
        self._prop = type(self._prop)(self._prop.fget, fset, self._prop.fdel, self.__doc__)
        return self

    def deleter(self, fdel):
        self._prop = type(self._prop)(self._prop.fget, self._prop.fset, fdel, self.__doc__)
        return self


def changing_default(new_default: _T, warning: type[ChangingDefaultWarning] = ChangingDefaultWarning):
    """Wrap a property to indicate that its default value will change in a future update.

    When the wrapped property is accessed, it will emit a warning if the property value hasn't been manually set.
    If the value has been manually set, this decorator has no effect.

    Parameters
    ----------
    new_default:
        New value that will become the default in the future.
    warning:
        Warning class to emit when the value isn't manually set.
        Must be a subclass of `asdf.exceptions.ChangingDefaultWarning`.

    Examples
    --------
    When planning to change the default value of a property simply add the ``@changing_default``
    decorator after the ``@property`` decorator::

        >>> class Config:
        ...    def __init__(self):
        ...        self._value = 1
        ...
        ...    @changing_default(2)
        ...    @property  # Make sure to still include the property decorator
        ...    def value(self) -> int:
        ...        return self._value
        ...
        ...    @value.setter  # Setter is defined as usual
        ...    def value(self, value: int) -> None:
        ...        self._value = value
        >>> cfg = Config()
        >>> cfg.value # doctest: +SKIP
        asdf.exceptions.ChangingDefaultWarning: In the future the default for value will
            be 2 instead of the current default of 1. Explicitly pass 1 or 2 to silence
            this warning, or use warnings.simplefilter("ignore", ChangingDefaultWarning)
            to silence all changing default warnings.
        1
        >>> cfg.value = 3
        >>> cfg.value
        3
    """

    def inner(prop):
        return _ChangingDefault(prop, new_default, warning)

    return inner
