import asdf

from . import _utils


def build_tree_keys():
    return [f"{tree_size}_{data_size}" for tree_size in _utils.tree_sizes for data_size in _utils.data_sizes]


class WalkTree:
    params = build_tree_keys()

    def setup(self, key):
        self.tree = _utils.build_tree(*key.split("_"))

    def time_walk(self, key):
        asdf.treeutil.walk(self.tree, lambda x: None)
