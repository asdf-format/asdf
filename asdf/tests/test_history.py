import datetime
import fractions

import pytest

import asdf
from asdf.extension import Converter, Extension
from asdf.tests.helpers import yaml_to_asdf, assert_no_warnings
from asdf.core import HistoryEntry, Software
from asdf.exceptions import AsdfWarning


def test_history():
    ff = asdf.AsdfFile()
    assert 'history' not in ff.tree
    ff.add_history_entry(
        'This happened',
        [Software(name="my_tool", homepage="http://nowhere.org", author="John Doe", version="2.0")],
    )

    assert len(ff.tree['history']['entries']) == 1

    ff.add_history_entry('This other thing happened')
    assert len(ff.tree['history']['entries']) == 2

    assert isinstance(ff.tree['history']['entries'][0].time, datetime.datetime)

def test_history_to_file(tmpdir):

    tmpfile = str(tmpdir.join('history.asdf'))

    with asdf.AsdfFile() as ff:
        ff.add_history_entry(
            'This happened',
            [Software(name="my_tool", homepage="http://nowhere.org", author="John Doe", version="2.0",)],
        )
        ff.write_to(tmpfile)

    with asdf.open(tmpfile) as ff:
        assert 'entries' in ff.tree['history']
        assert 'extensions' in ff.tree['history']
        assert len(ff.tree['history']['entries']) == 1

        entry = ff.tree['history']['entries'][0]
        assert entry.description == 'This happened'
        assert entry.software[0].name == 'my_tool'
        assert entry.software[0].version == '2.0'

        # Test the history entry retrieval API
        entries = ff.get_history_entries()
        assert len(entries) == 1
        assert isinstance(entries, list)
        assert isinstance(entries[0], HistoryEntry)
        assert entries[0].description == "This happened"
        assert entries[0].software[0].name == 'my_tool'


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

        # Test the history entry retrieval API
        entries = af.get_history_entries()
        assert len(entries) == 1
        assert isinstance(entries, list)
        assert isinstance(entries[0], HistoryEntry)
        assert entries[0].description == "Here's a test of old history entries"
        assert entries[0].software[0].name == 'foo'

def test_get_history_entries(tmpdir):
    """
    Test edge cases for the get_history_entries API. Other cases tested above
    """

    tmpfile = str(tmpdir.join('empty.asdf'))

    with asdf.AsdfFile() as af:
        af.write_to(tmpfile)

    # Make sure this works when there is no history section at all
    with asdf.open(tmpfile) as af:
        assert len(af['history']['extensions']) > 0
        assert len(af.get_history_entries()) == 0


def test_extension_metadata(tmpdir):

    ff = asdf.AsdfFile()

    tmpfile = str(tmpdir.join('extension.asdf'))
    ff.write_to(tmpfile)

    with asdf.open(tmpfile) as af:
        assert len(af.tree['history']['extensions']) == 2
        metadata = af.tree['history']['extensions'][0]
        assert metadata.extension_class == 'asdf.extension.BuiltinExtension'
        # Don't bother with testing the version here since it will depend on
        # how recently the package was built (version is auto-generated)
        assert metadata.software.name == 'asdf'

        metadata = af.tree['history']['extensions'][1]
        assert metadata.extension_class == 'asdf.extension._manifest.ManifestExtension'
        # Don't bother with testing the version here since it will depend on
        # how recently the package was built (version is auto-generated)
        assert metadata.software.name == 'asdf'


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
    with pytest.warns(AsdfWarning, match="File was created with extension class 'foo.bar.FooBar'"):
        with asdf.open(buff):
            pass


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
    with pytest.warns(AsdfWarning, match="File was created with extension class 'asdf.extension.BuiltinExtension'"):
        with asdf.open(buff):
            pass

    buff.seek(0)

    # Make sure suppressing the warning works too
    with assert_no_warnings():
        with asdf.open(buff, ignore_missing_extensions=True):
            pass


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
        with asdf.open(buff, strict_extension_check=True):
            pass

    # Make sure to test for incompatibility with ignore_missing_extensions
    buff.seek(0)
    with pytest.raises(ValueError):
        with asdf.open(buff, strict_extension_check=True, ignore_missing_extensions=True):
            pass


def test_metadata_with_custom_extension(tmp_path):
    class FractionConverter(Converter):
        tags = ["asdf://nowhere.org/tags/fraction-*"]
        types = [fractions.Fraction]

        def to_yaml_tree(self, obj, tag, ctx):
            return [obj.numerator, obj.denominator]

        def from_yaml_tree(self, node, tag, ctx):
            return fractions.Fraction(node[0], node[1])

    class FractionExtension(Extension):
        extension_uri = "asdf://nowhere.org/extensions/fraction-1.0.0"
        converters = [FractionConverter()]
        tags = ["asdf://nowhere.org/tags/fraction-1.0.0"]

    file_path = tmp_path / "custom_extension.asdf"
    with asdf.config_context() as config:
        config.add_extension(FractionExtension())

        tree = {
            "fraction": fractions.Fraction(2, 3)
        }
        with asdf.AsdfFile(tree) as af:
            af.write_to(file_path)

        # We expect metadata about both the Builtin/core extensions and the custom one
        with asdf.open(file_path) as af:
            assert len(af["history"]["extensions"]) == 3

    with pytest.warns(AsdfWarning, match="was created with extension"):
        with asdf.open(file_path, ignore_unrecognized_tag=True):
            pass

    # If we use the extension but we don't serialize any types that require it,
    # no metadata about this extension should be added to the file
    file_path2 = tmp_path / "no_extension.asdf"
    with asdf.config_context() as config:
        config.add_extension(FractionExtension())
        tree2 = { "x": [x for x in range(10)] }

        with asdf.AsdfFile(tree2) as af:
            af.write_to(file_path2)

        with asdf.open(file_path2) as af:
            assert len(af["history"]["extensions"]) == 2

    with assert_no_warnings():
        with asdf.open(file_path2):
            pass

    # Make sure that this works even when constructing the tree on-the-fly
    file_path3 = tmp_path / "custom_extension2.asdf"
    with asdf.config_context() as config:
        config.add_extension(FractionExtension())

        with asdf.AsdfFile() as af:
            af["fraction"] = fractions.Fraction(4, 5)
            af.write_to(file_path3)

        with asdf.open(file_path3) as af:
            assert len(af["history"]["extensions"]) == 3
