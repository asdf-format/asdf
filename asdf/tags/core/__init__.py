from ...types import AsdfType


class AsdfObject(dict):
    pass

from .ndarray import NDArrayType


__all__ = ['AsdfObject', 'NDArrayType']


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
