from asdf.extension import Converter


class AsdfObjectConverter(Converter):
    # Since AsdfObject is just a dict, we're able to use the same converter
    # for both tag versions.
    tags = [
        "tag:stsci.edu:asdf/core/asdf-1.0.0",
        "tag:stsci.edu:asdf/core/asdf-1.1.0",
    ]
    types = ["asdf.core._entities.AsdfObject"]

    def to_yaml_tree(self, obj, tag, ctx):
        return dict(obj)

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import AsdfObject

        return AsdfObject(node)


class ExternalArrayReferenceConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/externalarray-1.0.0"]
    types = ["asdf.core._entities.ExternalArrayReference"]

    def to_yaml_tree(self, obj, tag, ctx):
        node = {
            "fileuri": obj.fileuri,
            "target": obj.target,
            "datatype": obj.datatype,
            "shape": list(obj.shape),
        }

        node.update(obj.extra)

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import ExternalArrayReference

        extra = dict(node)
        fileuri = extra.pop("fileuri")
        target = extra.pop("target")
        datatype = extra.pop("datatype")
        shape = tuple(extra.pop("shape"))

        return ExternalArrayReference(
            fileuri=fileuri,
            target=target,
            datatype=datatype,
            shape=shape,
            extra=extra,
        )


class SoftwareConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/software-1.0.0"]
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

        node.update(obj.extra)

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import Software

        extra = dict(node)
        name = extra.pop("name")
        version = extra.pop("version")

        try:
            author = extra.pop("author")
        except KeyError:
            author = None

        try:
            homepage = extra.pop("homepage")
        except KeyError:
            homepage = None

        return Software(
            name=name,
            version=version,
            author=author,
            homepage=homepage,
            extra=extra,
        )


class HistoryEntryConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/history_entry-1.0.0"]
    types = ["asdf.core._entities.HistoryEntry"]

    def to_yaml_tree(self, obj, tag, ctx):
        node = {"description": obj.description}

        if obj.time is not None:
            node["time"] = obj.time

        if len(obj.software) > 0:
            node["software"] = obj.software

        node.update(obj.extra)

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import HistoryEntry, Software

        extra = dict(node)

        description = extra.pop("description")

        try:
            time = extra.pop("time")
        except KeyError:
            time = None

        try:
            software = extra.pop("software")
        except KeyError:
            software = []

        if isinstance(software, Software):
            software = [software]

        return HistoryEntry(
            description=description,
            time=time,
            software=software,
            extra=extra,
        )


class ExtensionMetadataConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/extension_metadata-1.0.0"]
    types = ["asdf.core._entities.ExtensionMetadata"]

    def to_yaml_tree(self, obj, tag, ctx):
        node = {"extension_class": obj.extension_class}

        if obj.extension_uri is not None:
            node["extension_uri"] = obj.extension_uri

        if obj.software is not None:
            node["software"] = obj.software

        node.update(obj.extra)

        return node

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.core import ExtensionMetadata, Software

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

        # A bug in version 2.5.x of this library caused files to be written with
        # an untagged software object here.
        if isinstance(software, dict):
            software = Software(**software)

        return ExtensionMetadata(
            extension_class=extension_class,
            extension_uri=extension_uri,
            software=software,
            extra=extra,
        )
