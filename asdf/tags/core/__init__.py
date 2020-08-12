from ...types import AsdfType


class AsdfObject(dict):
    pass

from .constant import ConstantType
from .ndarray import NDArrayType
from .complex import ComplexType
from .integer import IntegerType
from .external_reference import ExternalArrayReference


__all__ = ['AsdfObject', 'Software', 'HistoryEntry', 'ExtensionMetadata',
    'SubclassMetadata', 'ConstantType', 'NDArrayType', 'ComplexType',
    'IntegerType', 'ExternalArrayReference']


class AsdfObjectType(AsdfType):
    name = 'core/asdf'
    version = '1.1.0'
    supported_versions = {'1.0.0', '1.1.0'}
    types = [AsdfObject]

    @classmethod
    def from_tree(cls, node, ctx):
        return AsdfObject(node)

    @classmethod
    def to_tree(cls, data, ctx):
        return dict(data)


class Software(dict, AsdfType):
    name = 'core/software'
    version = '1.0.0'


class HistoryEntry(dict, AsdfType):
    name = 'core/history_entry'
    version = '1.0.0'


class ExtensionMetadata(dict, AsdfType):
    name = 'core/extension_metadata'
    version = '1.0.0'

    @property
    def extension_uri(self):
        return self.get('extension_uri')

    @property
    def extension_class(self):
        return self['extension_class']

    @property
    def software(self):
        return self.get('software')


class SubclassMetadata(dict, AsdfType):
    """
    The tagged object supported by this class is part of
    an experimental feature that has since been dropped
    from this library.  This class remains so that ASDF
    files that used that feature will still deserialize
    without warnings.
    """
    name = 'core/subclass_metadata'
    version = '1.0.0'
