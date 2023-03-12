import numpy as np

from asdf import constants
from asdf.extension import Converter
from asdf.tags.core import IntegerType


class IntegerConverter(Converter):
    tags = [
        "tag:stsci.edu:asdf/core/integer-1.0.0",
        "tag:stsci.edu:asdf/core/integer-1.1.0",
    ]

    types = [
        "builtins.int",
        "numpy.int8",
        "numpy.int16",
        "numpy.int32",
        "numpy.int64",
        "numpy.longlong",
        "numpy.uint8",
        "numpy.uint16",
        "numpy.uint32",
        "numpy.uint64",
        "numpy.ulonglong",
        "asdf.tags.core.integer.IntegerType",
    ]

    def select_tag(self, obj, tags, ctx):
        if isinstance(obj, IntegerType) or obj < constants.MIN_NUMBER or obj > constants.MAX_NUMBER:
            return tags[0]

        return None

    def to_yaml_tree(self, obj, tag, ctx):
        if tag is None:
            return int(obj)

        if isinstance(obj, IntegerType):
            obj = int(obj)

        abs_value = int(np.abs(obj))
        sign = "-" if obj < 0 else "+"

        # Pack integer value into 32-bit words:
        words = []
        value = abs_value
        while value > 0:
            words.append(value & 0xFFFFFFFF)
            value >>= 32

        return {
            "words": np.array(words, dtype=np.uint32),
            "sign": sign,
            "string": str(int(obj)),
        }

    def from_yaml_tree(self, node, tag, ctx):
        value = 0
        for x in node["words"][::-1]:
            value <<= 32
            value |= int(x)

        if node["sign"] == "-":
            value = -value

        return value
