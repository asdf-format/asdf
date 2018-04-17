# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import os
import datetime
import fractions

import pytest

from jsonschema import ValidationError

import asdf
from asdf import util
from asdf import asdftypes
from asdf.tests import helpers
from asdf.tests.helpers import yaml_to_asdf, display_warnings


SCHEMA_PATH = os.path.join(os.path.dirname(helpers.__file__), 'data')


class CustomExtension:
    """
    This is the base class that is used for extensions for custom tag
    classes that exist only for the purposes of testing.
    """
    @property
    def types(self):
        return []

    @property
    def tag_mapping(self):
        return [('tag:nowhere.org:custom',
                 'http://nowhere.org/schemas/custom{tag_suffix}')]

    @property
    def url_mapping(self):
        return [('http://nowhere.org/schemas/custom/',
                 util.filepath_to_url(SCHEMA_PATH) +
                 '/{url_suffix}.yaml')]


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

def test_history_to_file(tmpdir):

    tmpfile = str(tmpdir.join('history.asdf'))

    with asdf.AsdfFile() as ff:
        ff.add_history_entry('This happened',
                             {'name': 'my_tool',
                              'homepage': 'http://nowhere.com',
                              'author': 'John Doe',
                              'version': '2.0'})
        ff.write_to(tmpfile)

    with asdf.open(tmpfile) as ff:
        assert 'entries' in ff.tree['history']
        assert 'extensions' in ff.tree['history']
        assert len(ff.tree['history']['entries']) == 1

        entry = ff.tree['history']['entries'][0]
        assert entry['description'] == 'This happened'
        assert entry['software']['name'] == 'my_tool'
        assert entry['software']['version'] == '2.0'


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

    assert len(warnings) == 1, display_warnings(warnings)
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

    assert len(warnings) == 1, display_warnings(warnings)
    assert str(warnings[0].message).startswith(
        "File was created with extension 'asdf.extension.BuiltinExtension' "
        "from package asdf-100.0.3")

    buff.seek(0)

    # Make sure suppressing the warning works too
    with pytest.warns(None) as warnings:
        with asdf.open(buff, ignore_missing_extensions=True) as af:
            pass

    assert len(warnings) == 0, display_warnings(warnings)


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

    # Make sure to test for incompatibility with ignore_missing_extensions
    with pytest.raises(ValueError):
        with asdf.open(buff, strict_extension_check=True, ignore_missing_extensions=True) as af:
            pass


def test_metadata_with_custom_extension(tmpdir):

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

    class FractionExtension(CustomExtension):
        @property
        def types(self):
            return [FractionType]

    tree = {
        'fraction': fractions.Fraction(2, 3)
    }

    tmpfile = str(tmpdir.join('custom_extension.asdf'))
    with asdf.AsdfFile(tree, extensions=FractionExtension()) as ff:
        ff.write_to(tmpfile)

    # We expect metadata about both the Builtin extension and the custom one
    with asdf.open(tmpfile, extensions=FractionExtension()) as af:
        assert len(af['history']['extensions']) == 2

    with pytest.warns(None) as warnings:
        with asdf.open(tmpfile, ignore_unrecognized_tag=True) as af:
            pass

    # Since we're ignoring the unrecognized tag warning, we should only get
    # one warning here, which is the one about the missing extension
    assert len(warnings) == 1
    assert "was created with extension" in str(warnings[0].message)

    # If we use the extension but we don't serialize any types that require it,
    # no metadata about this extension should be added to the file
    tree2 = { 'x': [x for x in range(10)] }
    tmpfile2 = str(tmpdir.join('no_extension.asdf'))
    with asdf.AsdfFile(tree2, extensions=FractionExtension()) as ff:
        ff.write_to(tmpfile2)

    with asdf.open(tmpfile2) as af:
        assert len(af['history']['extensions']) == 1

    with pytest.warns(None) as warnings:
        with asdf.open(tmpfile2) as af:
            pass

    assert len(warnings) == 0
