from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from asdf.extension import Converter
from asdf.reference import Reference

if TYPE_CHECKING:
    from asdf.extension import SerializationContext

ReferenceNode = TypedDict("ReferenceNode", {"$ref": str})


class ReferenceConverter(Converter[Reference, ReferenceNode]):
    tags = []
    types = ["asdf.reference.Reference"]

    def to_yaml_tree(self, obj: Reference, tag: str, ctx: SerializationContext) -> ReferenceNode:
        from asdf.generic_io import relative_uri

        base_uri = None
        if ctx._blocks._write_fd is not None and ctx._blocks._write_fd.uri is not None:
            base_uri = ctx._blocks._write_fd.uri
        elif ctx.url is not None:
            base_uri = ctx.url
        uri = relative_uri(base_uri, obj._uri) if base_uri is not None else obj._uri
        return {"$ref": uri}

    def from_yaml_tree(self, node: ReferenceNode, tag: str, ctx: SerializationContext) -> Reference:
        raise NotImplementedError()

    def select_tag(self, obj: Reference, tags: list[str], ctx: SerializationContext) -> str | None:
        return None
