from asdf import _types

from .complex import ComplexType
from .constant import ConstantType
from .external_reference import ExternalArrayReference
from .integer import IntegerType
from .ndarray import NDArrayType

__all__ = [
    "AsdfObject",
    "Software",
    "HistoryEntry",
    "ExtensionMetadata",
    "SubclassMetadata",
    "ConstantType",
    "NDArrayType",
    "ComplexType",
    "IntegerType",
    "ExternalArrayReference",
]


class AsdfObject(dict):
    pass


class AsdfObjectType(_types.AsdfType):
    name = "core/asdf"
    version = "1.1.0"
    supported_versions = {"1.0.0", "1.1.0"}
    types = [AsdfObject]

    @classmethod
    def from_tree(cls, node, ctx):
        return AsdfObject(node)

    @classmethod
    def to_tree(cls, data, ctx):
        return dict(data)


class Software(dict, _types.AsdfType):
    name = "core/software"
    version = "1.0.0"


class HistoryEntry(dict, _types.AsdfType):
    name = "core/history_entry"
    version = "1.0.0"


class ExtensionMetadata(dict, _types.AsdfType):
    name = "core/extension_metadata"
    version = "1.0.0"

    @property
    def extension_uri(self):
        return self.get("extension_uri")

    @property
    def extension_class(self):
        return self["extension_class"]

    @property
    def software(self):
        return self.get("software")


class SubclassMetadata(dict, _types.AsdfType):
    """
    The tagged object supported by this class is part of
    an experimental feature that has since been dropped
    from this library.  This class remains so that ASDF
    files that used that feature will still deserialize
    without warnings.
    """

    name = "core/subclass_metadata"
    version = "1.0.0"
