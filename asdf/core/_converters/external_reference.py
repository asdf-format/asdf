from asdf.extension import Converter


class ExternalArrayReferenceConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/externalarray-1.0.0"]
    types = ["asdf.tags.core.external_reference.ExternalArrayReference"]

    def to_yaml_tree(self, obj, tag, ctx):
        return {
            "fileuri": obj.fileuri,
            "target": obj.target,
            "datatype": obj.dtype,
            "shape": list(obj.shape),
        }

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import ExternalArrayReference

        return ExternalArrayReference(node["fileuri"], node["target"], node["datatype"], tuple(node["shape"]))
