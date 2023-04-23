from asdf.extension import Converter


class AsdfObjectConverter(Converter):
    # Since AsdfObject is just a dict, we're able to use the same converter
    # for both tag versions.
    tags = [
        "tag:stsci.edu:asdf/core/asdf-1.0.0",
        "tag:stsci.edu:asdf/core/asdf-1.1.0",
    ]
    types = ["asdf.tags.core.AsdfObject"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import AsdfObject

        return AsdfObject(node)


class ExtensionMetadataConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/extension_metadata-1.0.0"]
    types = ["asdf.tags.core.ExtensionMetadata"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import ExtensionMetadata

        return ExtensionMetadata(node)


class HistoryEntryConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/history_entry-1.0.0"]
    types = ["asdf.tags.core.HistoryEntry"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import HistoryEntry

        return HistoryEntry(node)


class SoftwareConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/software-1.0.0"]
    types = ["asdf.tags.core.Software"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import Software

        return Software(node)


class SubclassMetadataConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/subclass_metadata-1.0.0"]
    types = ["asdf.tags.core.SubclassMetadata"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import SubclassMetadata

        return SubclassMetadata(node)
