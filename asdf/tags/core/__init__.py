# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
import warnings

from ...types import AsdfType
from ...yamlutil import custom_tree_to_tagged_tree
from ...exceptions import AsdfDeprecationWarning


class AsdfObject(dict):
    pass


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

    def __init__(self, extension_class=None, package=None, software=None):
        if software is not None:
            warnings.warn("Previous versions of the ASDF library stored a 'software' property " +
                          "in extension metadata.  That property has been renamed to 'package' " +
                          "to match the ASDF standard.  Re-write your file with this version to " +
                          "eliminate the warning.",
                          AsdfDeprecationWarning)
            package = Software(software)

        self.extension_class = extension_class
        self.package = package

    @classmethod
    def from_tree(cls, node, ctx):
        return cls(**node)

    @classmethod
    def to_tree(cls, node, ctx):
        tree = {}
        tree['extension_class'] = node.extension_class
        tree['package'] = custom_tree_to_tagged_tree(node.package, ctx)

        return tree

    @property
    def software(self):
        warnings.warn("The 'software' property is deprecated.  Please use 'package' instead.", AsdfDeprecationWarning)
        return self.package


class SubclassMetadata(dict, AsdfType):
    name = 'core/subclass_metadata'
    version = '1.0.0'


from .constant import ConstantType
from .ndarray import NDArrayType
from .complex import ComplexType
from .integer import IntegerType
from .external_reference import ExternalArrayReference
