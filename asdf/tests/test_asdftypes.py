# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import os

try:
    import astropy
except ImportError:
    HAS_ASTROPY = False
else:
    HAS_ASTROPY = True

import pytest

from .. import asdf
from .. import asdftypes
from .. import extension
from .. import util
from .. import versioning

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
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/{url_suffix}.yaml')]

    class FractionCallable(FractionExtension):
        @property
        def tag_mapping(self):
            def check(tag):
                prefix = 'tag:nowhere.org:custom'
                if tag.startswith(prefix):
                    return 'http://nowhere.org/schemas/custom' + tag[len(prefix):]
            return [check]

    yaml = """
a: !<tag:nowhere.org:custom/fraction-1.0.0>
  [2, 3]
b: !core/complex-1.0.0
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


def test_version_mismatch():
    from astropy.tests.helper import catch_warnings

    yaml = """
a: !core/complex-42.0.0
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with catch_warnings() as w:
        with asdf.AsdfFile.open(buff) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file, "
        "but asdf only understands version 1.0.0.")

    # Make sure warning is repeatable
    buff.seek(0)
    with catch_warnings() as w:
        with asdf.AsdfFile.open(buff) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(w) == 1
    assert str(w[0].message) == (
        "'tag:stsci.edu:asdf/core/complex' with version 42.0.0 found in file, "
        "but asdf only understands version 1.0.0.")

    # If the major and minor match, there should be no warning.
    yaml = """
a: !core/complex-1.0.1
  0j
    """

    buff = helpers.yaml_to_asdf(yaml)
    with catch_warnings() as w:
        with asdf.AsdfFile.open(buff) as ff:
            assert isinstance(ff.tree['a'], complex)

    assert len(w) == 0


def test_versioned_writing():
    from ..tags.core.complex import ComplexType

    # Create a bogus version map
    versioning._version_map['42.0.0'] = {
        'FILE_FORMAT': '42.0.0',
        'YAML_VERSION': '1.1',
        'tags': {
            'tag:stsci.edu:asdf/core/complex': '42.0.0',
            'tag:stscu.edu:asdf/core/asdf': '1.0.0'
        }
    }

    versioning.supported_versions.append('42.0.0')

    class FancyComplexType(ComplexType):
        version = (42, 0, 0)

    class FancyComplexExtension(object):
        @property
        def types(self):
            return [FancyComplexType]

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return [('http://stsci.edu/schemas/asdf/core/complex-42.0.0',
                     util.filepath_to_url(TEST_DATA_PATH) +
                     '/complex-42.0.0.yaml')]

    tree = {'a': complex(0, -1)}

    buff = io.BytesIO()
    ff = asdf.AsdfFile(tree, version="42.0.0",
                       extensions=[FancyComplexExtension()])
    ff.write_to(buff)

    assert b'complex-42.0.0' in buff.getvalue()

    del versioning._version_map['42.0.0']
    versioning.supported_versions.pop()


def test_longest_match():
    class FancyComplexExtension(object):
        @property
        def types(self):
            return []

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return [('http://stsci.edu/schemas/asdf/core/',
                     'FOOBAR/{url_suffix}')]

    l = extension.AsdfExtensionList(
        [extension.BuiltinExtension(), FancyComplexExtension()])

    assert l.url_mapping(
        'http://stsci.edu/schemas/asdf/core/asdf-1.0.0') == 'FOOBAR/asdf-1.0.0'
    assert l.url_mapping(
        'http://stsci.edu/schemas/asdf/transform/transform-1.0.0') != 'FOOBAR/transform-1.0.0'
