# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import datetime

import pytest

from jsonschema import ValidationError

from .... import asdf


def test_history():
    ff = asdf.AsdfFile()
    assert 'history' not in ff.tree
    ff.add_history_entry('This happened',
                         {'name': 'my_tool',
                          'homepage': 'http://nowhere.com',
                          'author': 'John Doe',
                          'version': '2.0'})
    assert len(ff.tree['history']) == 1

    with pytest.raises(ValidationError):
        ff.add_history_entry('That happened',
                             {'name': 'my_tool',
                              'author': 'John Doe',
                              'version': '2.0'})
    assert len(ff.tree['history']) == 1

    ff.add_history_entry('This other thing happened')
    assert len(ff.tree['history']) == 2

    assert isinstance(ff.tree['history'][0]['time'], datetime.datetime)
