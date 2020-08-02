# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import pytest

from . import create_small_tree, create_large_tree

from asdf import config


@pytest.fixture
def small_tree():
    return create_small_tree()


@pytest.fixture
def large_tree():
    return create_large_tree()


@pytest.fixture(autouse=True)
def restore_default_config():
    yield
    config._global_config = config.AsdfConfig()
    config._local = config._ConfigLocal()
