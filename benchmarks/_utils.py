import io
import string

import numpy as np

import asdf

tree_sizes = ["small", "flat", "deep", "large"]
data_sizes = ["0", "3x3", "128x128"]


def data_function(size):
    if not size:
        return ord
    dims = [int(d) for d in size.split("x")]
    return lambda k: np.zeros(dims) * ord(k)


def build_tree(size, value_function=None):
    if value_function is None:
        value_function = str
    if isinstance(value_function, str):
        value_function = data_function(value_function)
    if size == "small":
        return {k: value_function(k) for k in string.ascii_lowercase[:3]}
    if size == "flat":
        return {k: value_function(k) for k in string.ascii_lowercase[:26]}
    if size == "deep":
        tree = {}
        for k in string.ascii_lowercase[:26]:
            tree[k] = {"value": value_function(k)}
            tree = tree[k]
        return tree
    if size == "large":
        tree = {}
        for k in string.ascii_lowercase[:26]:
            tree[k] = {k2: value_function(k2) for k2 in string.ascii_lowercase[:26]}
        return tree
    msg = f"Unknown tree size: {size}"
    raise ValueError(msg)


def write_to_bytes(af):
    bs = io.BytesIO()
    with asdf.generic_io.get_file(bs, "w") as f:
        af.write_to(f)
    bs.seek(0)
    return bs


def build_tree_keys():
    return {f"{k}_{dk}" for k in tree_sizes for dk in data_sizes}
