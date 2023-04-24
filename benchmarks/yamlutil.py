import asdf

from . import _utils


def build_tree_keys():
    return [f"{tree_size}_{data_size}" for tree_size in _utils.tree_sizes for data_size in _utils.data_sizes]


class YamlUtilSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.af = asdf.AsdfFile()
        self.custom_tree = _utils.build_tree(*key.split("_"))
        self.tagged_tree = asdf.yamlutil.custom_tree_to_tagged_tree(self.custom_tree, self.af)

    def _custom_tree_to_tagged_tree(self, key):
        asdf.yamlutil.custom_tree_to_tagged_tree(self.custom_tree, self.af)

    def _tagged_tree_to_custom_tree(self, key):
        asdf.yamlutil.tagged_tree_to_custom_tree(self.tagged_tree, self.af)

    def time_custom_tree_to_tagged_tree(self, key):
        self._custom_tree_to_tagged_tree(key)

    def time_tagged_tree_to_custom_tree(self, key):
        self._tagged_tree_to_custom_tree(key)

    def peakmem_pass(self, key):
        pass

    def peakmem_custom_tree_to_tagged_tree(self, key):
        self._custom_tree_to_tagged_tree(key)

    def peakmem_tagged_tree_to_custom_tree(self, key):
        self._tagged_tree_to_custom_tree(key)
