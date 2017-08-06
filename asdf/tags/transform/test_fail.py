from __future__ import absolute_import, division, unicode_literals, print_function

from ... import yamlutil
from .basic import TransformType
from astropy.modeling.core import Model

__all__ = ['TestFailType', 'TestFail']


class TestFail(Model):
    """
    Class to compute the z coordinate through the NIRSPEC grating wheel.

    """
    separable = False

    inputs = ("x",)
    outputs = ("z",)

    def __init__(self, tab, **kwargs):
        self.tab = tab
        super(TestFail, self).__init__(**kwargs)
        
    def evaluate(self, x):
        return self.tab(x)

    
class TestFailType(TransformType):
    name = "transform/test_fail"
    types = [TestFail]
    version = "1.1.0"


    @classmethod
    def from_tree_transform(cls, node, ctx):
        tab = node['model']
        return TestFail(tab)

    @classmethod
    def to_tree_transform(cls, model, ctx):
        node = {'model': model.tab}
        return yamlutil.custom_tree_to_tagged_tree(node, ctx)
