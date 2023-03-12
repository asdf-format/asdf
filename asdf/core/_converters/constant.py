from asdf.extension import Converter


class ConstantConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/constant-1.0.0"]
    types = ["asdf.tags.core.constant.Constant"]

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.value

    def from_yaml_tree(self, node, tag, ctx):
        from asdf.tags.core import Constant

        return Constant(node)
