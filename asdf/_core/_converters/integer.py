import numpy as np

from asdf.extension import Converter


class IntegerConverter(Converter):
    tags = [
        "tag:stsci.edu:asdf/core/integer-1.0.0",
        "tag:stsci.edu:asdf/core/integer-1.1.0",
    ]
    types = ["asdf.tags.core.integer.IntegerType"]

    def to_yaml_tree(self, obj, tag, ctx):
        abs_value = int(np.abs(obj._value))

        # pack integer value into 32-bit words
        words = []
        value = abs_value
        while value > 0:
            words.append(value & 0xFFFFFFFF)
            value >>= 32

        array = np.array(words, dtype=np.uint32)

        tree = {}
        ctx.set_array_storage(array, obj._storage)
        tree["words"] = array
        tree["sign"] = obj._sign
        tree["string"] = str(int(obj._value))

        return tree

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core.integer import IntegerType

        value = 0
        for x in node["words"][::-1]:
            value <<= 32
            value |= int(x)

        if node["sign"] == "-":
            value = -value

        return IntegerType(value)
