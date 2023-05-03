from .constant import Constant
from .external_reference import ExternalArrayReference
from .integer import IntegerType
from .ndarray import NDArrayType
from .stream import Stream

__all__ = [
    "AsdfObject",
    "Constant",
    "Software",
    "HistoryEntry",
    "ExtensionMetadata",
    "SubclassMetadata",
    "NDArrayType",
    "IntegerType",
    "ExternalArrayReference",
    "Stream",
]


class AsdfObject(dict):
    pass


class Software(dict):
    pass


class HistoryEntry(dict):
    pass


class ExtensionMetadata(dict):
    @property
    def extension_uri(self):
        return self.get("extension_uri")

    @property
    def extension_class(self):
        return self["extension_class"]

    @property
    def software(self):
        return self.get("software")


class SubclassMetadata(dict):
    """
    The tagged object supported by this class is part of
    an experimental feature that has since been dropped
    from this library.  This class remains so that ASDF
    files that used that feature will still deserialize
    without warnings.
    """
