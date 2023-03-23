import io

import asdf

from . import _utils


def build_tree_keys():
    return [f"{tree_size}_{data_size}" for tree_size in _utils.tree_sizes for data_size in _utils.data_sizes]


class InitSuite:

    params = build_tree_keys()

    def setup(self, key):
        self.tree = _utils.build_tree(*key.split('_'))

    def time_AsdfFile_init(self, key):
        af = asdf.AsdfFile(self.tree)

    def mem_AsdfFile_init(self, key):
        return asdf.AsdfFile(self.tree)


class ValidateSuite:

    params = build_tree_keys()

    def setup(self, key):
        self.asdf_file = asdf.AsdfFile(_utils.build_tree(*key.split('_')))

    def time_AsdfFile_validate(self, key):
        af = self.asdf_file.validate()

    def peakmem_AsdfFile(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_AsdfFile_validate(self, key):
        # peakmem includes setup
        af = self.asdf_file.validate()


class WriteToSuite:

    params = build_tree_keys()

    def setup(self, key):
        self.asdf_file = asdf.AsdfFile(_utils.build_tree(*key.split('_')))

    def time_AsdfFile_write_to(self, key):
        with asdf.generic_io.get_file(io.BytesIO(), "w") as f:
            self.asdf_file.write_to(f)

    def peakmem_AsdfFile(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_AsdfFile_write_to(self, size):
        with asdf.generic_io.get_file(io.BytesIO(), "w") as f:
            self.asdf_file.write_to(f)


class OpenSuite:

    params = build_tree_keys()

    def setup(self, key):
        self.byte_file = _util.write_to_bytes(asdf.AsdfFile(_utils.build_tree(*key.split('_'))))

    def time_AsdfFile_open(self, key):
        with asdf.open(self.byte_file) as af:
            pass

    def peakmem_AsdfFile(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_AsdfFile_open(self, key):
        with asdf.open(self.byte_file) as af:
            pass
