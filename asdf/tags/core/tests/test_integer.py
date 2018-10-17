# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import random

import pytest

import asdf
from asdf import IntegerType
from asdf.tests import helpers


# Make sure tests are deterministic
random.seed(0)


@pytest.mark.parametrize('sign', ['+', '-'])
@pytest.mark.parametrize('value', [
    random.getrandbits(64),
    random.getrandbits(65),
    random.getrandbits(100),
    random.getrandbits(128),
    random.getrandbits(129),
    random.getrandbits(200),
])
def test_integer_value(tmpdir, value, sign):

    if sign == '-':
        value = -value

    integer = IntegerType(value)
    tree = dict(integer=integer)
    helpers.assert_roundtrip_tree(tree, tmpdir)


@pytest.mark.parametrize('inline', [False, True])
def test_integer_storage(tmpdir, inline):

    tmpfile = str(tmpdir.join('integer.asdf'))

    kwargs = dict()
    if inline:
        kwargs['storage_type'] = 'inline'

    random.seed(0)
    value = random.getrandbits(1000)
    tree = dict(integer=IntegerType(value, **kwargs))

    with asdf.AsdfFile(tree) as af:
        af.write_to(tmpfile)

    with asdf.open(tmpfile, _force_raw_types=True) as rf:
        if inline:
            assert 'source' not in rf.tree['integer']['words']
            assert 'data' in rf.tree['integer']['words']
        else:
            assert 'source' in rf.tree['integer']['words']
            assert 'data' not in rf.tree['integer']['words']
