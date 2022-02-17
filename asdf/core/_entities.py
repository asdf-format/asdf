from dataclasses import dataclass, field
import datetime
from typing import Any, Dict, List, Tuple, Union


class AsdfObject(dict):
    """
    The root of an ASDF tree.  Exists mainly to provide a type
    that corresponds to the asdf-x.y.z tag.
    """

    pass


@dataclass
class ExternalArrayReference:
    """
    Store a reference to an array in an external File.

    This class is a simple way of referring to an array in another file. It
    provides no way to resolve these references, that is left to the user. It
    also performs no checking to see if any of the arguments are correct. e.g.
    if the file exits.

    Parameters
    ----------

    fileuri: str
        The path to the path to be referenced. Can be relative to the file
        containing the reference.

    target: str or int
        Some internal target to the data in the file. Examples may include a HDU
        index, a HDF path or an asdf fragment.

    dtype: str
        The (numpy) dtype of the contained array.

    shape: tuple of int
        The shape of the array to be loaded.

    extra : dict, optional
        Additional metadata to include when serializing this
        object.

    Examples
    --------

    >>> import asdf
    >>> ref = asdf.core.ExternalArrayReference("myfitsfile.fits", 1, "float64", (100, 100))
    >>> tree = {'reference': ref}
    >>> with asdf.AsdfFile(tree) as ff:
    ...     ff.write_to("test.asdf")

    """

    fileuri: str
    target: Union[str, int]
    datatype: str
    shape: Tuple[int]
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Software:
    """
    General-purpose description of a software package.

    Parameters
    ----------

    name : str
        The name of the application or library.

    version : str
        The version of the software used.

    author : str, optional
        The author (or institution) that produced the software package.

    homepage: str, optional
        A URI to the homepage of the software.

    extra : dict, optional
        Additional metadata to include when serializing this
        object.
    """

    name: str
    version: str
    author: Union[str, None] = None
    homepage: Union[str, None] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryEntry:
    """
    An entry in the ASDF file history.

    Parameters
    ----------

    description : str
        A description of the transformation performed.

    time : datetime.datetime, optional
        A timestamp for the operation, in UTC.

    software : list of Software, optional
        The software that performed the operation.

    extra : dict, optional
        Additional metadata to include when serializing this
        object.
    """

    description: str
    time: Union[datetime.datetime, None] = None
    software: List[Software] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtensionMetadata:
    """
    Metadata about specific ASDF extensions that were used to create this file.

    Parameters
    ----------

    extension_class : str
        The fully-specified name of the extension class.

    extension_uri : str, optional
        The extension's identifying URI.

    software : Software, optional
        The software package that provided the extension.

    extra : dict, optional
        Additional metadata to include when serializing this
        object.
    """

    extension_class: str
    extension_uri: Union[str, None] = None
    software: Union[Software, None] = None
    extra: Dict[str, Any] = field(default_factory=dict)
