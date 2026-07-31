from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from asdf.extension import Converter
from asdf.tags.core import ExternalArrayReference

if TYPE_CHECKING:
    from asdf.extension import SerializationContext


class ExternalArrayNode(TypedDict):
    fileuri: str
    target: Any
    datatype: str
    shape: list[str]


class ExternalArrayReferenceConverter(Converter[ExternalArrayReference, ExternalArrayNode]):
    tags = ["tag:stsci.edu:asdf/core/externalarray-1.0.0"]
    types = ["asdf.tags.core.external_reference.ExternalArrayReference"]

    def to_yaml_tree(self, obj: ExternalArrayReference, tag: str, ctx: SerializationContext) -> ExternalArrayNode:
        return {
            "fileuri": obj.fileuri,
            "target": obj.target,
            "datatype": obj.dtype,
            "shape": list(obj.shape),
        }

    def from_yaml_tree(self, node: ExternalArrayNode, tag: str, ctx: SerializationContext) -> ExternalArrayReference:
        return ExternalArrayReference(node["fileuri"], node["target"], node["datatype"], tuple(node["shape"]))
