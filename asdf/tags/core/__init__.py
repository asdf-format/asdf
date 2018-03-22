# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


from ...asdftypes import AsdfType
from ...yamlutil import custom_tree_to_tagged_tree


class AsdfObject(dict, AsdfType):
    name = 'core/asdf'
    version = '1.1.0'


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
        tree['software'] = custom_tree_to_tagged_tree(node.software, ctx)
        return tree


from .constant import ConstantType
from .ndarray import NDArrayType
from .complex import ComplexType
from .external_reference import ExternalArrayReference
