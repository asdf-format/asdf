# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
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


class ExtensionMetadata(AsdfType):
    name = 'core/extension_metadata'
    version = '1.0.0'

    def __init__(self, extension_class=None, software={}):
        self.extension_class = extension_class
        self.software = software

    @classmethod
    def from_tree(cls, node, ctx):
        return cls(**node)

    @classmethod
    def to_tree(cls, node, ctx):
        tree = {}
        tree['extension_class'] = node.extension_class
        tree['software'] = node.software

        return tree


class SubclassMetadata(dict, AsdfType):
    name = 'core/subclass_metadata'
    version = '1.0.0'
