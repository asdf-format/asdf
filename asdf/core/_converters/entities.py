from asdf.extension import Converter


class ExternalArrayReferenceConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/externalarray-*"]
    types = ["asdf.core._entities.ExternalArrayReference"]

    def to_yaml_tree(self, obj, tag, ctx):
        return {
            "fileuri": obj.fileuri,
            "target": obj.target,
            "datatype": obj.datatype,
            "shape": list(obj.shape),
        }

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import ExternalArrayReference

        return ExternalArrayReference(
            fileuri=node["fileuri"],
            target=node["target"],
            datatype=node["datatype"],
            shape=tuple(node["shape"]),
        )


class SoftwareConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/software-*"]
    types = ["asdf.core._entities.Software"]

    def to_yaml_tree(self, obj, tag, ctx):
        node = {
            "name": obj.name,
            "version": obj.version,
        }

        if obj.author is not None:
            node["author"] = obj.author

        if obj.homepage is not None:
            node["homepage"] = obj.homepage

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import Software

        return Software(
            name=node["name"],
            version=node["version"],
            author=node.get("author"),
            homepage=node.get("homepage"),
        )


class HistoryEntryConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/history_entry-*"]
    types = ["asdf.core._entities.HistoryEntry"]

    def to_yaml_tree(self, obj, tag, ctx):
        node = {
            "description": obj.description
        }

        if obj.time is not None:
            node["time"] = obj.time

        if len(obj.software) > 0:
            node["software"] = obj.software

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import HistoryEntry, Software

        software = node.get("software", [])
        if isinstance(software, Software):
            software = [software]

        return HistoryEntry(
            description=node["description"],
            time=node.get("time"),
            software=software,
        )


class ExtensionMetadataConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/extension_metadata-*"]
    types = ["asdf.core._entities.ExtensionMetadata"]

    def to_yaml_tree(self, obj, tag, ctx):
        node = {
            "extension_class": obj.extension_class
        }

        if obj.extension_uri is not None:
            node["extension_uri"] = obj.extension_uri

        if obj.software is not None:
            node["software"] = obj.software

        node.update(obj.extra)

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import ExtensionMetadata

        extra = dict(node)

        extension_class = extra.pop("extension_class")

        try:
            extension_uri = extra.pop("extension_uri")
        except KeyError:
            extension_uri = None

        try:
            software = extra.pop("software")
        except KeyError:
            software = None

        return ExtensionMetadata(
            extension_class=extension_class,
            extension_uri=extension_uri,
            software=software,
            extra=extra,
        )
