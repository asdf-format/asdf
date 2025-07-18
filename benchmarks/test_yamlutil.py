import pytest

import asdf


@pytest.fixture(scope="module")
def ctx_asdf_file():
    return asdf.AsdfFile()


@pytest.fixture()
def tagged_tree(tree, ctx_asdf_file):
    return asdf.yamlutil.custom_tree_to_tagged_tree(tree, ctx_asdf_file)


def test_custom_tree_to_tagged_tree(tree, ctx_asdf_file, benchmark):
    benchmark(asdf.yamlutil.custom_tree_to_tagged_tree, tree, ctx_asdf_file)


def test_tagged_tree_to_tagged_tree(tagged_tree, ctx_asdf_file, benchmark):
    benchmark(asdf.yamlutil.tagged_tree_to_custom_tree, tagged_tree, ctx_asdf_file)
