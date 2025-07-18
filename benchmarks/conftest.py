import itertools
import string

import numpy as np
import pytest

import asdf

SMALL_SET = string.ascii_lowercase[:3]
LARGE_SET = string.ascii_lowercase[:26]

DATA_GENS = ["no_data", "small_data", "large_data"]
TREE_GENS = ["small_tree", "flat_tree", "deep_tree", "large_tree"]


def no_data(i):
    return i


def small_data(i):
    return np.full((3, 3), i)


def large_data(i):
    return np.full((128, 128), i)


def small_tree(data_gen):
    return {k: data_gen(ord(k)) for k in SMALL_SET}


def flat_tree(data_gen):
    return {k: data_gen(ord(k)) for k in LARGE_SET}


def deep_tree(data_gen):
    tree = {}
    for k in LARGE_SET:
        tree[k] = {"value": data_gen(k)}
        tree = tree[k]
    return tree


def large_tree(data_gen):
    tree = {}
    for k in LARGE_SET:
        tree["value"] = {k: data_gen(ord(k)) for k in LARGE_SET}
        tree[k] = {}
        tree = tree[k]
    return tree


@pytest.fixture(params=itertools.product(DATA_GENS, TREE_GENS))
def tree(request):
    data_gen_name, tree_gen_name = request.param
    # some gymnastics to work around pytest not allowing
    # getfixturevalue to use parametrized fixtures
    return globals()[tree_gen_name](globals()[data_gen_name])


@pytest.fixture
def tree_bytes(tree):
    return asdf.dumps(tree)


@pytest.fixture
def asdf_file(tree):
    return asdf.AsdfFile(tree)
