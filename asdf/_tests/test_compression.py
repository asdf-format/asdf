import io
import lzma
import os

import numpy as np
import pytest

import asdf
from asdf import _compression, config_context, generic_io
from asdf._tests import _helpers as helpers
from asdf.extension import Compressor, Extension

RNG = np.random.default_rng(0)


def _get_large_tree():
    x = RNG.normal(size=(128, 128))
    return {"science_data": x}


def _get_sparse_tree():
    arr = np.zeros((128, 128))
    for x, y, z in RNG.normal(size=(64, 3)):
        arr[int(x * 127), int(y * 127)] = z
    arr[0, 0] = 5.0
    return {"science_data": arr}


def _roundtrip(tmp_path, tree, compression=None, write_options=None, read_options=None):
    read_options = {} if read_options is None else read_options
    write_options = {} if write_options is None else write_options.copy()
    write_options.update(all_array_compression=compression)

    tmpfile = os.path.join(str(tmp_path), "test.asdf")

    ff = asdf.AsdfFile(tree)
    ff.write_to(tmpfile, **write_options)

    with asdf.open(tmpfile, mode="rw") as ff:
        ff.update(**write_options)

    with asdf.open(tmpfile, **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    # Also test saving to a buffer
    buff = io.BytesIO()

    ff = asdf.AsdfFile(tree)
    ff.write_to(buff, **write_options)

    buff.seek(0)
    with asdf.open(buff, **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    # Test saving to a non-seekable buffer
    buff = io.BytesIO()

    ff = asdf.AsdfFile(tree)
    ff.write_to(generic_io.OutputStream(buff), **write_options)

    buff.seek(0)
    with asdf.open(generic_io.InputStream(buff), **read_options) as ff:
        helpers.assert_tree_match(tree, ff.tree)

    return tmpfile


def test_invalid_compression():
    tree = _get_large_tree()
    ff = asdf.AsdfFile(tree)
    with pytest.raises(ValueError, match=r"Invalid compression type: foo"):
        ff.set_array_compression(tree["science_data"], "foo")
    with pytest.raises(ValueError, match=r"Unknown compression type: .*"):
        _compression._get_compressor("foo")


def test_get_compressed_size():
    assert _compression.get_compressed_size(b"0" * 1024, "zlib") < 1024


def test_decompress_too_long_short():
    fio = io.BytesIO()
    _compression.compress(fio, b"0" * 1024, "zlib")
    size = fio.tell()
    fio.seek(0)
    blocks = lambda us: [fio.read(us)]  # noqa: E731
    fio.read_blocks = blocks
    _compression.decompress(fio, size, 1024, "zlib")
    fio.seek(0)
    with pytest.raises(ValueError, match=r"Decompressed data wrong size"):
        _compression.decompress(fio, size, 1025, "zlib")
    fio.seek(0)
    with pytest.raises(ValueError, match=r"memoryview assignment: lvalue and rvalue have different structures"):
        _compression.decompress(fio, size, 1023, "zlib")


def test_zlib(tmp_path):
    tree = _get_large_tree()

    _roundtrip(tmp_path, tree, "zlib")


def test_bzp2(tmp_path):
    tree = _get_large_tree()

    _roundtrip(tmp_path, tree, "bzp2")


def test_lz4(tmp_path):
    pytest.importorskip("lz4")
    tree = _get_large_tree()

    _roundtrip(tmp_path, tree, "lz4")


def test_recompression(tmp_path):
    tree = _get_large_tree()
    tmpfile = os.path.join(str(tmp_path), "test1.asdf")
    afile = asdf.AsdfFile(tree)
    afile.write_to(tmpfile, all_array_compression="zlib")
    afile.close()
    afile = asdf.open(tmpfile)
    tmpfile = os.path.join(str(tmp_path), "test2.asdf")
    afile.write_to(tmpfile, all_array_compression="bzp2")
    afile.close()
    afile = asdf.open(tmpfile)
    helpers.assert_tree_match(tree, afile.tree)
    afile.close()


def test_input(tmp_path):
    tree = _get_large_tree()
    tmpfile = os.path.join(str(tmp_path), "test1.asdf")
    afile = asdf.AsdfFile(tree)
    afile.write_to(tmpfile, all_array_compression="zlib")
    afile.close()
    afile = asdf.open(tmpfile)
    tmpfile = os.path.join(str(tmp_path), "test2.asdf")
    afile.write_to(tmpfile)
    afile.close()
    afile = asdf.open(tmpfile)
    helpers.assert_tree_match(tree, afile.tree)
    assert afile.get_array_compression(afile.tree["science_data"]) == "zlib"
    afile.close()


def test_none(tmp_path):
    tree = _get_large_tree()

    tmpfile1 = os.path.join(str(tmp_path), "test1.asdf")
    with asdf.AsdfFile(tree) as afile:
        afile.write_to(tmpfile1)

    tmpfile2 = os.path.join(str(tmp_path), "test2.asdf")
    with asdf.open(tmpfile1) as afile:
        assert afile.get_array_compression(afile.tree["science_data"]) is None
        afile.write_to(tmpfile2, all_array_compression="zlib")

    with asdf.open(tmpfile2) as afile:
        assert afile.get_array_compression(afile.tree["science_data"]) == "zlib"
        afile.write_to(tmpfile1, all_array_compression=None)

    with asdf.open(tmpfile1) as afile:
        helpers.assert_tree_match(tree, afile.tree)
        assert afile.get_array_compression(afile.tree["science_data"]) is None


def test_set_array_compression(tmp_path):
    tmpfile = os.path.join(str(tmp_path), "compressed.asdf")

    zlib_data = np.array(list(range(1000)))
    bzp2_data = np.array(list(range(1000)))

    tree = {"zlib_data": zlib_data, "bzp2_data": bzp2_data}
    with asdf.AsdfFile(tree) as af_out:
        af_out.set_array_compression(zlib_data, "zlib", level=1)
        af_out.set_array_compression(bzp2_data, "bzp2", compresslevel=9000)
        with pytest.raises(ValueError, match=r"compresslevel must be between 1 and 9"):
            af_out.write_to(tmpfile)
        af_out.set_array_compression(bzp2_data, "bzp2", compresslevel=9)
        af_out.write_to(tmpfile)
        assert af_out.get_array_compression_kwargs(bzp2_data)["compresslevel"] == 9

    with asdf.open(tmpfile) as af_in:
        assert af_in.get_array_compression(af_in.tree["zlib_data"]) == "zlib"
        assert af_in.get_array_compression(af_in.tree["bzp2_data"]) == "bzp2"


def test_nonnative_endian_compression(tmp_path):
    ledata = np.arange(1000, dtype="<i8")
    bedata = np.arange(1000, dtype=">i8")

    _roundtrip(tmp_path, {"ledata": ledata, "bedata": bedata}, "lz4")


class LzmaCompressor(Compressor):
    def compress(self, data, **kwargs):
        comp = lzma.compress(data, **kwargs)
        yield comp

    def decompress(self, blocks, out, **kwargs):
        decompressor = lzma.LZMADecompressor(**kwargs)
        i = 0
        for block in blocks:
            decomp = decompressor.decompress(block)
            out[i : i + len(decomp)] = decomp
            i += len(decomp)
        return i

    @property
    def label(self):
        return b"lzma"


class LzmaExtension(Extension):
    @property
    def extension_uri(self):
        return "asdf://somewhere.org/extensions/lzma-1.0"

    @property
    def compressors(self):
        return [LzmaCompressor()]


def test_compression_with_extension(tmp_path):
    tree = _get_large_tree()

    with pytest.raises(ValueError, match="Supported compression types are"), config_context() as cfg:
        cfg.all_array_compression = "lzma"

    with config_context() as config:
        config.add_extension(LzmaExtension())

        with config_context() as cfg:
            cfg.all_array_compression = "lzma"

        with pytest.raises(lzma.LZMAError, match=r"Invalid or unsupported options"):
            _roundtrip(tmp_path, tree, "lzma", write_options={"compression_kwargs": {"preset": 9000}})
        fn = _roundtrip(tmp_path, tree, "lzma", write_options={"compression_kwargs": {"preset": 6}})

        hist = {
            "extension_class": "asdf._tests.test_compression.LzmaExtension",
            "extension_uri": "asdf://somewhere.org/extensions/lzma-1.0",
            "supported_compression": ["lzma"],
        }

        with asdf.open(fn) as af:
            assert hist in af["history"]["extensions"]
