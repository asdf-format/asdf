import io

import asdf

from . import _utils


def build_tree_keys():
    return [f"{tree_size}_{data_size}" for tree_size in _utils.tree_sizes for data_size in _utils.data_sizes]


class AsdfFileInitSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.tree = _utils.build_tree(*key.split("_"))

    def time_init(self, key):
        asdf.AsdfFile(self.tree)

    def mem_init(self, key):
        return asdf.AsdfFile(self.tree)


class AsdfFileValidateSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.asdf_file = asdf.AsdfFile(_utils.build_tree(*key.split("_")))

    def time_validate(self, key):
        self.asdf_file.validate()

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_validate(self, key):
        # peakmem includes setup
        self.asdf_file.validate()


class AsdfFileWriteToSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.asdf_file = asdf.AsdfFile(_utils.build_tree(*key.split("_")))

    def time_write_to(self, key):
        with asdf.generic_io.get_file(io.BytesIO(), "w") as f:
            self.asdf_file.write_to(f)

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_write_to(self, size):
        with asdf.generic_io.get_file(io.BytesIO(), "w") as f:
            self.asdf_file.write_to(f)


class AsdfFileOpenSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.byte_file = _utils.write_to_bytes(asdf.AsdfFile(_utils.build_tree(*key.split("_"))))

    def time_open(self, key):
        self.byte_file.seek(0)
        with asdf.open(self.byte_file):
            pass

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_open(self, key):
        self.byte_file.seek(0)
        with asdf.open(self.byte_file):
            pass
