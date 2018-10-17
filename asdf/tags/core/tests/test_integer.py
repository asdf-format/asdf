# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import random

import pytest

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
