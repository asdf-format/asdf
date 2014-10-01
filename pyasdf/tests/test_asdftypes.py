# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os

from .. import asdf
from .. import asdftypes
from .. import resolver
from . import helpers


TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def test_custom_tag():
    import fractions

    class FractionType(asdftypes.AsdfType):
        name = 'fraction'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [fractions.Fraction]

        @classmethod
        def to_tree(cls, node, ctx):
            return [node.numerator, node.denominator]

        @classmethod
        def from_tree(cls, tree, ctx):
            return fractions.Fraction(tree[0], tree[1])

    tag_mapping = resolver.TagToSchemaResolver(
        [('tag:nowhere.org:custom', 'http://nowhere.org/schemas/custom{0}')])

    url_mapping = resolver.UrlMapping(
        [('http://nowhere.org/schemas/custom/1.0.0/',
          'file://' + TEST_DATA_PATH + '/{0}.yaml')])

    yaml = """
a: !<tag:nowhere.org:custom/1.0.0/fraction>
  [2, 3]
    """

    buff = helpers.yaml_to_asdf(yaml)
    ff = asdf.AsdfFile.read(
        buff,
        tag_to_schema_resolver=tag_mapping,
        url_mapping=url_mapping)
    assert ff.tree['a'] == fractions.Fraction(2, 3)
