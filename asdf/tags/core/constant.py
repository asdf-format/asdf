from asdf import _types


class Constant:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value


class ConstantType(_types.AsdfType):
    name = "core/constant"
    version = "1.0.0"
    types = [Constant]

    @classmethod
    def from_tree(cls, node, ctx):
        return Constant(node)

    @classmethod
    def to_tree(cls, data, ctx):
        return data.value
