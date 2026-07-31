from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np

from asdf import util
from asdf.extension import Converter

if TYPE_CHECKING:
    from asdf.extension import SerializationContext

_REPLACEMENTS = {
    re.compile("i(?!nf)"): "j",
    re.compile("I(?!NF)"): "J",
}


class ComplexConverter(Converter[complex, str]):
    tags = ["tag:stsci.edu:asdf/core/complex-1.0.0"]
    types = [*list(util._iter_subclasses(np.complexfloating)), complex]

    def to_yaml_tree(self, obj: complex, tag: str, ctx: SerializationContext) -> str:
        return str(obj)

    def from_yaml_tree(self, node: str, tag: str, ctx: SerializationContext) -> complex:
        for pattern, replacement in _REPLACEMENTS.items():
            node = pattern.sub(replacement, node)

        return complex(node)
