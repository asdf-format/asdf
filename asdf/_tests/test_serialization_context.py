import numpy as np
import pytest

import asdf
from asdf import get_config
from asdf.extension import ExtensionManager
from asdf.extension._serialization_context import BlockAccess, SerializationContext


def test_serialization_context():
    extension_manager = ExtensionManager([])
    context = SerializationContext("1.4.0", extension_manager, "file://test.asdf", None)
    assert context.version == "1.4.0"
    assert context.extension_manager is extension_manager
    assert context._extensions_used == set()

    extension = get_config().extensions[0]
    context._mark_extension_used(extension)
    assert context._extensions_used == {extension}
    context._mark_extension_used(extension)
    assert context._extensions_used == {extension}
    context._mark_extension_used(extension.delegate)
    assert context._extensions_used == {extension}

    assert context.url == context._url == "file://test.asdf"

    with pytest.raises(TypeError, match=r"Extension must implement the Extension interface"):
        context._mark_extension_used(object())

    with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
        SerializationContext("0.5.4", extension_manager, None, None)


def test_get_block_data_callback(tmp_path):
    fn = tmp_path / "test.asdf"

    # make a file with 2 blocks
    arr0 = np.arange(3, dtype="uint8")
    arr1 = np.arange(10, dtype="uint8")
    asdf.AsdfFile({"arr0": arr0, "arr1": arr1}).write_to(fn)

    with asdf.open(fn) as af:
        context = af._create_serialization_context()
        with pytest.raises(NotImplementedError, match="abstract"):
            context.get_block_data_callback(0)

        op_ctx = af._create_serialization_context(BlockAccess.READ)
        cb0 = op_ctx.get_block_data_callback(0)

        # getting the same callback should pass and return the same object
        assert op_ctx.get_block_data_callback(0) is cb0

        # since we accessed block 0 we shouldn't be allowed to access block 1
        with pytest.raises(OSError, match=r"Converters accessing >1.*"):
            op_ctx.get_block_data_callback(1)

        # unless we use a key
        key = op_ctx.generate_block_key()
        cb1 = op_ctx.get_block_data_callback(1, key)
        assert op_ctx.get_block_data_callback(1, key) is cb1

        # we don't know the order of blocks, so find which block
        # was used for which array by looking at the size
        d0 = cb0()
        d1 = cb1()
        if d0.size == arr1.size:
            arr0, arr1 = arr1, arr0
        np.testing.assert_array_equal(d0, arr0)
        np.testing.assert_array_equal(d1, arr1)

        for access in (BlockAccess.NONE, BlockAccess.WRITE):
            op_ctx = af._create_serialization_context(access)
            with pytest.raises(NotImplementedError, match="abstract"):
                op_ctx.get_block_data_callback(0)


def test_find_available_block_index():
    af = asdf.AsdfFile()
    context = af._create_serialization_context()

    def cb():
        return np.arange(3, dtype="uint8")

    with pytest.raises(NotImplementedError, match="abstract"):
        context.find_available_block_index(cb)

    class Foo:
        pass

    op_ctx = af._create_serialization_context(BlockAccess.WRITE)
    op_ctx.assign_object(Foo())
    assert op_ctx.find_available_block_index(cb) == 0

    for access in (BlockAccess.NONE, BlockAccess.READ):
        op_ctx = af._create_serialization_context(access)
        with pytest.raises(NotImplementedError, match="abstract"):
            op_ctx.find_available_block_index(cb)


def test_generate_block_key():
    af = asdf.AsdfFile()
    context = af._create_serialization_context()

    with pytest.raises(NotImplementedError, match="abstract"):
        context.generate_block_key()

    class Foo:
        pass

    obj = Foo()
    op_ctx = af._create_serialization_context(BlockAccess.WRITE)
    op_ctx.assign_object(obj)
    key = op_ctx.generate_block_key()
    assert key._is_valid()
    assert key._matches_object(obj)

    obj = Foo()
    op_ctx = af._create_serialization_context(BlockAccess.READ)
    # because this test generates but does not assign a key
    # it should raise an exception
    with pytest.raises(OSError, match=r"Converter generated a key.*"):
        key = op_ctx.generate_block_key()
        # the key does not yet have an assigned object
        assert not key._is_valid()
        op_ctx.assign_blocks()


@pytest.mark.parametrize("block_access", [None, *list(BlockAccess)])
def test_get_set_array_storage(block_access):
    af = asdf.AsdfFile()
    if block_access is None:
        context = af._create_serialization_context()
    else:
        context = af._create_serialization_context(block_access)
    arr = np.zeros(3)
    storage = "external"
    assert af.get_array_storage(arr) != storage
    context.set_array_storage(arr, storage)
    assert af.get_array_storage(arr) == storage
    assert context.get_array_storage(arr) == storage


@pytest.mark.parametrize("block_access", [None, *list(BlockAccess)])
def test_get_set_array_compression(block_access):
    af = asdf.AsdfFile()
    if block_access is None:
        context = af._create_serialization_context()
    else:
        context = af._create_serialization_context(block_access)
    arr = np.zeros(3)
    compression = "bzp2"
    kwargs = {"a": 1}
    assert af.get_array_compression(arr) != compression
    assert af.get_array_compression_kwargs(arr) != kwargs
    context.set_array_compression(arr, compression, **kwargs)
    assert af.get_array_compression(arr) == compression
    assert af.get_array_compression_kwargs(arr) == kwargs
    assert context.get_array_compression(arr) == compression
    assert context.get_array_compression_kwargs(arr) == kwargs


def test_get_set_array_save_base():
    af = asdf.AsdfFile()
    context = af._create_serialization_context()
    arr = np.zeros(3)
    cfg = asdf.get_config()
    save_base = cfg.default_array_save_base
    assert af.get_array_save_base(arr) == save_base
    assert context.get_array_save_base(arr) == save_base

    save_base = not save_base
    context.set_array_save_base(arr, save_base)
    assert af.get_array_save_base(arr) == save_base
    assert context.get_array_save_base(arr) == save_base

    save_base = not save_base
    af.set_array_save_base(arr, save_base)
    assert af.get_array_save_base(arr) == save_base
    assert context.get_array_save_base(arr) == save_base

    af.set_array_save_base(arr, None)
    assert af.get_array_save_base(arr) is None
    assert context.get_array_save_base(arr) is None


@pytest.mark.parametrize("value", [1, "true"])
def test_invalid_set_array_save_base(value):
    af = asdf.AsdfFile()
    context = af._create_serialization_context()
    arr = np.zeros(3)
    with pytest.raises(ValueError, match="save_base must be a bool or None"):
        af.set_array_save_base(arr, value)
    with pytest.raises(ValueError, match="save_base must be a bool or None"):
        context.set_array_save_base(arr, value)
