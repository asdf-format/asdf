# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
This packages contains affiliated package tests.
"""

import numpy as np

from .. import CustomType, util
from .helpers import get_test_data_path


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


def create_small_tree():
    x = np.arange(0, 10, dtype=np.float)
    tree = {
        'science_data': x,
        'subset': x[3:-3],
        'skipping': x[::2],
        'not_shared': np.arange(10, 0, -1, dtype=np.uint8)
    }
    return tree


def create_large_tree():
    # These are designed to be big enough so they don't fit in a
    # single block, but not so big that RAM/disk space for the tests
    # is enormous.
    x = np.random.rand(256, 256)
    y = np.random.rand(16, 16, 16)
    tree = {
        'science_data': x,
        'more': y
    }
    return tree


class CustomExtension:
    """
    This is the base class that is used for extensions for custom tag
    classes that exist only for the purposes of testing.
    """
    @property
    def types(self):
        return []

    @property
    def tag_mapping(self):
        return [('tag:nowhere.org:custom',
                 'http://nowhere.org/schemas/custom{tag_suffix}')]

    @property
    def url_mapping(self):
        return [('http://nowhere.org/schemas/custom/',
                 util.filepath_to_url(get_test_data_path('')) +
                 '/{url_suffix}.yaml')]
