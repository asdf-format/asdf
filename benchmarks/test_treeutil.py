import asdf


def test_walk(tree, benchmark):
    benchmark(asdf.treeutil.walk, tree, lambda x: None)
