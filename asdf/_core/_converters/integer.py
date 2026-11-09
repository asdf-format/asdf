from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

import numpy as np

from asdf.extension import Converter
from asdf.tags.core.integer import IntegerType

if TYPE_CHECKING:
    from asdf.extension import SerializationContext


class IntegerNode(TypedDict):
    words: Any
    sign: str
    string: str


class IntegerConverter(Converter[IntegerType, IntegerNode]):
    tags = [
        "tag:stsci.edu:asdf/core/integer-1.0.0",
        "tag:stsci.edu:asdf/core/integer-1.1.0",
        "tag:stsci.edu:asdf/core/integer-1.2.0",
    ]
    types = ["asdf.tags.core.integer.IntegerType"]

    def to_yaml_tree(self, obj: IntegerType, tag: str, ctx: SerializationContext) -> IntegerNode:
        abs_value = int(np.abs(obj._value))

        # pack integer value into 32-bit words
        words = []
        value = abs_value
        while value > 0:
            words.append(value & 0xFFFFFFFF)
            value >>= 32

        array = np.array(words, dtype=np.uint32)

        ctx.set_array_storage(array, obj._storage)

        return {"words": array, "sign": obj._sign, "string": str(int(obj._value))}

    def from_yaml_tree(self, node: IntegerNode, tag: str, ctx: SerializationContext) -> IntegerType:
        value = 0
        for x in node["words"][::-1]:
            value <<= 32
            value |= int(x)

        if node["sign"] == "-":
            value = -value

        return IntegerType(value)
