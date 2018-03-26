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


def test_extension_metadata(tmpdir):

    ff = asdf.AsdfFile()
    # So far only the base extension has been used
    assert len(ff.type_index.get_extensions_used()) == 1

    tmpfile = str(tmpdir.join('extension.asdf'))
    ff.write_to(tmpfile)

    with asdf.open(tmpfile) as af:
        assert len(af.tree['history']['extensions']) == 1
        metadata = af.tree['history']['extensions'][0]
        assert metadata.extension_class == 'asdf.extension.BuiltinExtension'
        # Don't bother with testing the version here since it will depend on
        # how recently the package was built (version is auto-generated)
        assert metadata.software['name'] == 'asdf'


def test_missing_extension_warning():

    yaml = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_class: foo.bar.FooBar
      software: !core/software-1.0.0
        name: foo
        version: 1.2.3
    """

    buff = yaml_to_asdf(yaml)
    with pytest.warns(None) as warnings:
        with asdf.open(buff) as af:
            pass

    assert len(warnings) == 1
    assert str(warnings[0].message).startswith(
        "File was created with extension 'foo.bar.FooBar'")


def test_extension_version_warning():

    yaml = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_class: asdf.extension.BuiltinExtension
      software: !core/software-1.0.0
        name: asdf
        version: 100.0.3
    """

    buff = yaml_to_asdf(yaml)
    with pytest.warns(None) as warnings:
        with asdf.open(buff) as af:
            pass

    assert len(warnings) == 1
    assert str(warnings[0].message).startswith(
        "File was created with extension 'asdf.extension.BuiltinExtension' "
        "from package asdf-100.0.3")


def test_strict_extension_check():

    yaml = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_class: foo.bar.FooBar
      software: !core/software-1.0.0
        name: foo
        version: 1.2.3
    """

    buff = yaml_to_asdf(yaml)
    with pytest.raises(RuntimeError):
        with asdf.open(buff, strict_extension_check=True) as af:
            pass
