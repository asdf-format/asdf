# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import pytest

from . import create_small_tree, create_large_tree


@pytest.fixture
def small_tree():
    return create_small_tree()


@pytest.fixture
def large_tree():
    return create_large_tree()
