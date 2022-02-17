import numpy as np

from ... import util
from ...types import AsdfType


class ComplexType(AsdfType):
    name = "core/complex"
    version = "1.0.0"
    types = list(util.iter_subclasses(np.complexfloating)) + [complex]

    @classmethod
    def to_tree(cls, node, ctx):
        return str(node)

    @classmethod
    def from_tree(cls, tree, ctx):
        tree = tree.replace("inf", "INF").replace("i", "j").replace("INF", "inf").replace("I", "J")
        return complex(tree)
