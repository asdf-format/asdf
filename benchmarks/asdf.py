import io

import asdf

from . import _utils


def build_tree_keys():
    return [f"{tree_size}_{data_size}" for tree_size in _utils.tree_sizes for data_size in _utils.data_sizes]


class AsdfFileInitSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.tree = _utils.build_tree(*key.split("_"))

    def _init(self, key):
        return asdf.AsdfFile(self.tree)

    def time_init(self, key):
        self._init(key)

    def mem_init(self, key):
        return self._init(key)


class AsdfFileValidateSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.asdf_file = asdf.AsdfFile(_utils.build_tree(*key.split("_")))

    def _validate(self, key):
        self.asdf_file.validate()

    def time_validate(self, key):
        self._validate(key)

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_validate(self, key):
        # peakmem includes setup
        self._validate(key)


class AsdfFileWriteToSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.asdf_file = asdf.AsdfFile(_utils.build_tree(*key.split("_")))

    def _write_to(self, key):
        with asdf.generic_io.get_file(io.BytesIO(), "w") as f:
            self.asdf_file.write_to(f)

    def time_write_to(self, key):
        self._write_to(key)

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_write_to(self, key):
        self._write_to(key)


class AsdfFileOpenSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.byte_file = _utils.write_to_bytes(asdf.AsdfFile(_utils.build_tree(*key.split("_"))))

    def _open(self, key):
        self.byte_file.seek(0)
        with asdf.open(self.byte_file):
            pass

    def time_open(self, key):
        self._open(key)

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_open(self, key):
        self._open(key)


class AsdfFileUpdateSuite:
    params = build_tree_keys()

    def setup(self, key):
        self.byte_file = _utils.write_to_bytes(asdf.AsdfFile(_utils.build_tree(*key.split("_"))))

    def _update(self, key):
        self.byte_file.seek(0)
        with asdf.open(self.byte_file, mode="rw") as af:
            af.update()

    def time_update(self, key):
        self._update(key)

    def peakmem_pass(self, key):
        # peakmem includes setup, this is for comparison
        pass

    def peakmem_update(self, key):
        self._update(key)


def timeraw_first_asdf_file():
    # Time creation of first AsdfFile which will trigger extension loading
    # and other one time operations
    return """
    import asdf
    af = asdf.AsdfFile()
    """
