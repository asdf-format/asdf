import numpy as np

import asdf


def test_1013(tmp_path):
    class FooType:
        def __init__(self, data):
            self.data = data

    class FooConverter:
        tags = ["asdf://somewhere.org/tag/foo-1.0.0"]
        types = [FooType]

        def to_yaml_tree(self, obj, tag, ctx):
            if obj.data.ndim < 2:
                ctx._blocks._set_array_storage(obj.data, "inline")
            return {"data": obj.data}

        def from_yaml_tree(self, obj, tag, ctx):
            return FooType(obj["data"])

    class FooExtension:
        converters = [FooConverter()]
        tags = ["asdf://somewhere.org/tag/foo-1.0.0"]
        extension_uri = "asdf://somewhere.org/extensions/foo-1.0.0"

    with asdf.config_context() as cfg:
        cfg.add_extension(FooExtension())

        fn = tmp_path / "test.asdf"

        for shape in [3, (3, 3)]:
            arr = np.zeros(shape)
            n_blocks = 0 if arr.ndim == 1 else 1
            af = asdf.AsdfFile()
            # avoid a call to validate that will set the storage type
            assert af.get_array_storage(arr) == "internal"
            af.tree = {"foo": FooType(arr)}
            af.write_to(fn)
            assert af.get_array_storage(arr) == "internal"

            with asdf.open(fn) as af:
                np.testing.assert_array_equal(af["foo"].data, arr)
                assert len(af._blocks.blocks) == n_blocks
