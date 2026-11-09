from __future__ import annotations

from typing import TYPE_CHECKING

from asdf.extension import Converter
from asdf.tags.core import Constant

if TYPE_CHECKING:
    from asdf.extension import SerializationContext
    from asdf.typing import YamlNode


class ConstantConverter(Converter[Constant]):
    tags = ["tag:stsci.edu:asdf/core/constant-1.0.0"]
    types = ["asdf.tags.core.constant.Constant"]

    def to_yaml_tree(self, obj: Constant, tag: str, ctx: SerializationContext) -> YamlNode:
        return obj.value

    def from_yaml_tree(self, node: YamlNode, tag: str, ctx: SerializationContext) -> Constant:
        return Constant(node)
