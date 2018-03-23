# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import datetime

import pytest

from jsonschema import ValidationError

import asdf
from asdf.tests.helpers import yaml_to_asdf


def test_history():
    ff = asdf.AsdfFile()
    assert 'history' not in ff.tree
    ff.add_history_entry('This happened',
                         {'name': 'my_tool',
                          'homepage': 'http://nowhere.com',
                          'author': 'John Doe',
                          'version': '2.0'})
    assert len(ff.tree['history']['entries']) == 1

    with pytest.raises(ValidationError):
        ff.add_history_entry('That happened',
                             {'author': 'John Doe',
                              'version': '2.0'})
    assert len(ff.tree['history']['entries']) == 1

    ff.add_history_entry('This other thing happened')
    assert len(ff.tree['history']['entries']) == 2

    assert isinstance(ff.tree['history']['entries'][0]['time'], datetime.datetime)


def test_old_history(tmpdir):
    """Make sure that old versions of the history format are still accepted"""

    yaml = """
history: 
  - !core/history_entry-1.0.0
    description: "Here's a test of old history entries"
    software: !core/software-1.0.0
      name: foo
      version: 1.2.3
    """

    buff = yaml_to_asdf(yaml)
    with asdf.open(buff) as af:
        assert len(af.tree['history']) == 1
