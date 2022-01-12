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
