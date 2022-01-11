from ...types import AsdfType


class AsdfObject(dict):
    pass

from .ndarray import NDArrayType
from .external_reference import ExternalArrayReference


__all__ = ['AsdfObject', 'Software', 'HistoryEntry', 'ExtensionMetadata',
    'NDArrayType', 'ExternalArrayReference']


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
