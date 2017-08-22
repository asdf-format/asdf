# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This packages contains affiliated package tests.
"""

from .. import CustomType


class CustomTestType(CustomType):
    """This class is intended to be inherited by custom types that are used
    purely for the purposes of testing. The methods ``from_tree_tagged`` and
    ``from_tree`` are implemented solely in order to avoid custom type
    conversion warnings.
    """

    @classmethod
    def from_tree_tagged(cls, tree, ctx):
        return cls.from_tree(tree.data, ctx)

    @classmethod
    def from_tree(cls, tree, ctx):
        return tree
