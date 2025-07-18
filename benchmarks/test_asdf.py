import io

import asdf


def test_init(tree, benchmark):
    benchmark(asdf.AsdfFile, tree)


def test_validate(asdf_file, benchmark):
    benchmark(asdf_file.validate)


def test_write_to(asdf_file, benchmark):
    bs = io.BytesIO()
    benchmark(asdf_file.write_to, bs)


def test_open(tree_bytes, benchmark):
    bs = io.BytesIO(tree_bytes)
    benchmark(asdf.open, bs)


def test_update(tree_bytes, benchmark):
    bs = io.BytesIO(tree_bytes)
    af = asdf.open(bs)
    benchmark(af.update)


def test_dump(tree, benchmark):
    benchmark(asdf.dumps, tree)


def test_load(tree_bytes, benchmark):
    benchmark(asdf.loads, tree_bytes)
