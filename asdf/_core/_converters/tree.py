from typing import Any

from asdf.extension import Converter, SerializationContext
from asdf.tags.core import AsdfObject, ExtensionMetadata, HistoryEntry, Software, SubclassMetadata
from asdf.typing import TreeKey

_YamlMap = dict[TreeKey, Any]


class AsdfObjectConverter(Converter[AsdfObject, _YamlMap]):
    # Since AsdfObject is just a dict, we're able to use the same converter
    # for both tag versions.
    tags = [
        "tag:stsci.edu:asdf/core/asdf-1.0.0",
        "tag:stsci.edu:asdf/core/asdf-1.1.0",
    ]
    types = ["asdf.tags.core.AsdfObject"]

    def to_yaml_tree(self, obj: AsdfObject, tag: str, ctx: SerializationContext) -> _YamlMap:
        return dict(obj)

    def from_yaml_tree(self, node: _YamlMap, tag: str, ctx: SerializationContext) -> AsdfObject:
        return AsdfObject(node)


class ExtensionMetadataConverter(Converter[ExtensionMetadata, _YamlMap]):
    tags = ["tag:stsci.edu:asdf/core/extension_metadata-1.0.0"]
    types = ["asdf.tags.core.ExtensionMetadata"]

    def to_yaml_tree(self, obj: ExtensionMetadata, tag: str, ctx: SerializationContext) -> _YamlMap:
        return dict(obj)

    def from_yaml_tree(self, node: _YamlMap, tag: str, ctx: SerializationContext) -> ExtensionMetadata:
        return ExtensionMetadata(node)


class HistoryEntryConverter(Converter[HistoryEntry, _YamlMap]):
    tags = ["tag:stsci.edu:asdf/core/history_entry-1.0.0"]
    types = ["asdf.tags.core.HistoryEntry"]

    def to_yaml_tree(self, obj: HistoryEntry, tag: str, ctx: SerializationContext) -> _YamlMap:
        return dict(obj)

    def from_yaml_tree(self, node: _YamlMap, tag: str, ctx: SerializationContext) -> HistoryEntry:
        return HistoryEntry(node)


class SoftwareConverter(Converter[Software, _YamlMap]):
    tags = ["tag:stsci.edu:asdf/core/software-1.0.0"]
    types = ["asdf.tags.core.Software"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        return Software(node)


class SubclassMetadataConverter(Converter[SubclassMetadata, _YamlMap]):
    tags = ["tag:stsci.edu:asdf/core/subclass_metadata-1.0.0"]
    types = ["asdf.tags.core.SubclassMetadata"]

    def to_yaml_tree(self, obj: SubclassMetadata, tag: str, ctx: SerializationContext) -> _YamlMap:
        return dict(obj)

    def from_yaml_tree(self, node: _YamlMap, tag: str, ctx: SerializationContext) -> SubclassMetadata:
        return SubclassMetadata(node)
