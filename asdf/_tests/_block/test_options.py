import copy

import pytest

from asdf._block.options import Options
from asdf.config import config_context

valid_storage_types = ["internal", "external", "streamed", "inline"]
valid_default_storage_types = [st for st in valid_storage_types if st != "streamed"]
valid_compression_types = [None, "zlib", "bzp2", "lz4", ""]

invalid_storage_types = ["foo", "bar"]
invalid_compression_types = ["input", "foo"]


@pytest.mark.parametrize("storage", valid_storage_types)
def test_set_storage_init(storage):
    o = Options(storage)
    assert o.storage_type == storage


@pytest.mark.parametrize("storage", valid_default_storage_types)
def test_default_storage_init(storage):
    with config_context() as cfg:
        cfg.all_array_storage = storage
        o = Options()
        assert o.storage_type == storage


@pytest.mark.parametrize("storage", valid_storage_types)
def test_set_storage_attr(storage):
    # start with a different storage type
    o = Options("internal" if storage == "external" else "external")
    o.storage_type = storage
    assert o.storage_type == storage


@pytest.mark.parametrize("compression", valid_compression_types)
def test_set_compression_attr(compression):
    o = Options("internal")
    o.compression = compression
    # allow "" to become None, both are falsey
    assert o.compression == compression if compression else not o.compression


@pytest.mark.parametrize("compression", valid_compression_types)
def test_set_compression_init(compression):
    o = Options("internal", compression)
    # allow "" to become None, both are falsey
    assert o.compression == compression if compression else not o.compression


def test_set_compression_kwargs_attr():
    o = Options("internal")
    o.compression_kwargs = {"foo": 1}
    assert o.compression_kwargs == {"foo": 1}


def test_set_compression_kwargs_init():
    o = Options("internal", compression_kwargs={"foo": 1})
    assert o.compression_kwargs == {"foo": 1}


def test_default_compression():
    o = Options("internal")
    assert o.compression is None


@pytest.mark.parametrize("invalid_storage", invalid_storage_types)
def test_invalid_storage_type_init(invalid_storage):
    with pytest.raises(ValueError, match="array_storage must be one of.*"):
        Options(invalid_storage)


@pytest.mark.parametrize("invalid_storage", invalid_storage_types)
def test_invalid_storage_attr(invalid_storage):
    o = Options("internal")
    with pytest.raises(ValueError, match="array_storage must be one of.*"):
        o.storage_type = invalid_storage


@pytest.mark.parametrize("invalid_compression", invalid_compression_types)
def test_invalid_compression_attr(invalid_compression):
    o = Options("internal")
    with pytest.raises(ValueError, match="Invalid compression.*"):
        o.compression = invalid_compression


@pytest.mark.parametrize("invalid_compression", invalid_compression_types)
def test_invalid_compression_init(invalid_compression):
    with pytest.raises(ValueError, match="Invalid compression.*"):
        Options("internal", invalid_compression)


@pytest.mark.parametrize("storage", valid_storage_types)
@pytest.mark.parametrize("compression", valid_compression_types)
@pytest.mark.parametrize("compression_kwargs", [None, {"foo": 1}])
def test_copy(storage, compression, compression_kwargs):
    o = Options(storage, compression, compression_kwargs)
    o2 = copy.copy(o)
    assert o2 is not o
    assert o2.storage_type == storage
    # allow "" to become None, both are falsey
    assert o2.compression == compression if compression else not o2.compression
    # allow None to become {}, both are falsey
    assert o2.compression_kwargs == compression_kwargs if compression_kwargs else not o2.compression_kwargs
