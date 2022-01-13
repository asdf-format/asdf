import re

from asdf.extension import Converter


_REPLACEMENTS = {
    re.compile("i(?!nf)"): "j",
    re.compile("I(?!NF)"): "J",
}


class ComplexConverter(Converter):
    tags = ["tag:stsci.edu:asdf/core/complex-1.0.0"]
    types = ["builtins.complex", "numpy.complex64", "numpy.complex128", "numpy.complex256"]

    def to_yaml_tree(self, obj, tag, ctx):
        return str(obj)

    def from_yaml_tree(self, node, tag, ctx):
        for pattern, replacement in _REPLACEMENTS.items():
            node = pattern.sub(replacement, node)

        return complex(node)
