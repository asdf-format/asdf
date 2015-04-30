# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

from .. import asdf
from .. import asdftypes
from . import helpers

from astropy.extern.six.moves.urllib.parse import urljoin
from astropy.extern.six.moves.urllib.request import pathname2url

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

    class FractionExtension(object):
        @property
        def types(self):
            return [FractionType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/1.0.0/',
                     urljoin('file:', pathname2url(os.path.join(
                         TEST_DATA_PATH))) + '/{url_suffix}.yaml')]

    class FractionCallable(FractionExtension):
        @property
        def tag_mapping(self):
            def check(tag):
                prefix = 'tag:nowhere.org:custom'
                if tag.startswith(prefix):
                    return 'http://nowhere.org/schemas/custom' + tag[len(prefix):]
            return [check]

    yaml = """
a: !<tag:nowhere.org:custom/1.0.0/fraction>
  [2, 3]
b: !core/complex
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(
        buff, extensions=FractionExtension()) as ff:
        assert ff.tree['a'] == fractions.Fraction(2, 3)

        buff = io.BytesIO()
        ff.write_to(buff)

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.AsdfFile.open(
            buff, extensions=FractionCallable()) as ff:
        assert ff.tree['a'] == fractions.Fraction(2, 3)

    buff = io.BytesIO()
    ff.write_to(buff)
    buff.close()
