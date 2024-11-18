import datetime
import fractions
import warnings

import pytest

import asdf
from asdf.exceptions import AsdfWarning, ValidationError
from asdf.extension import Converter, Extension, ExtensionProxy
from asdf.tags.core import HistoryEntry
from asdf.testing import helpers


def test_history():
    ff = asdf.AsdfFile()
    assert "history" not in ff.tree
    ff.add_history_entry(
        "This happened",
        {"name": "my_tool", "homepage": "http://nowhere.org", "author": "John Doe", "version": "2.0"},
    )
    assert len(ff.tree["history"]["entries"]) == 1

    with pytest.raises(ValidationError, match=r".* is not valid under any of the given schemas"):
        ff.add_history_entry("That happened", {"author": "John Doe", "version": "2.0"})
    assert len(ff.tree["history"]["entries"]) == 1

    ff.add_history_entry("This other thing happened")
    assert len(ff.tree["history"]["entries"]) == 2

    assert isinstance(ff.tree["history"]["entries"][0]["time"], datetime.datetime)


def test_history_to_file(tmp_path):
    file_path = tmp_path / "history.asdf"

    with asdf.AsdfFile() as ff:
        ff.add_history_entry(
            "This happened",
            {"name": "my_tool", "homepage": "http://nowhere.org", "author": "John Doe", "version": "2.0"},
        )
        ff.write_to(file_path)

    with asdf.open(file_path) as ff:
        assert "entries" in ff.tree["history"]
        assert "extensions" in ff.tree["history"]
        assert len(ff.tree["history"]["entries"]) == 1

        entry = ff.tree["history"]["entries"][0]
        assert entry["description"] == "This happened"
        assert entry["software"]["name"] == "my_tool"
        assert entry["software"]["version"] == "2.0"

        # Test the history entry retrieval API
        entries = ff.get_history_entries()
        assert len(entries) == 1
        assert isinstance(entries, list)
        assert isinstance(entries[0], HistoryEntry)
        assert entries[0]["description"] == "This happened"
        assert entries[0]["software"]["name"] == "my_tool"


def test_old_history():
    """Make sure that old versions of the history format are still accepted"""

    yaml = """
history:
  - !core/history_entry-1.0.0
    description: "Here's a test of old history entries"
    software: !core/software-1.0.0
      name: foo
      version: 1.2.3
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.open(buff) as af:
        assert len(af.tree["history"]) == 1

        # Test the history entry retrieval API
        entries = af.get_history_entries()
        assert len(entries) == 1
        assert isinstance(entries, list)
        assert isinstance(entries[0], HistoryEntry)
        assert entries[0]["description"] == "Here's a test of old history entries"
        assert entries[0]["software"]["name"] == "foo"


def test_get_history_entries(tmp_path):
    """
    Test edge cases for the get_history_entries API. Other cases tested above
    """
    file_path = tmp_path / "empty.asdf"

    with asdf.AsdfFile() as af:
        af.write_to(file_path)

    # Make sure this works when there is no history section at all
    with asdf.open(file_path) as af:
        assert len(af["history"]["extensions"]) > 0
        assert len(af.get_history_entries()) == 0


def test_extension_metadata(tmp_path):
    file_path = tmp_path / "extension.asdf"

    ff = asdf.AsdfFile()
    ff.write_to(file_path)

    with asdf.open(file_path) as af:
        assert len(af.tree["history"]["extensions"]) == 1
        metadata = af.tree["history"]["extensions"][0]
        assert metadata.extension_uri == "asdf://asdf-format.org/core/extensions/core-1.6.0"
        assert metadata.extension_class == "asdf.extension._manifest.ManifestExtension"
        assert metadata.software["name"] == "asdf"
        assert metadata.software["version"] == asdf.__version__


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

    buff = helpers.yaml_to_asdf(yaml)
    with pytest.warns(AsdfWarning, match=r"File was created with extension class 'foo.bar.FooBar'"), asdf.open(buff):
        pass


def test_extension_version_warning():
    uri = "asdf://somewhere.org/extensions/foo-1.0.0"
    package_name = "foo"
    file_package_version = "2.0.0"
    installed_package_version = "1.0.0"

    class FooExtension:
        extension_uri = uri

    yaml = f"""
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_class: {FooExtension.__qualname__}
      extension_uri: {uri}
      software: !core/software-1.0.0
        name: {package_name}
        version: {file_package_version}
    """

    buff = helpers.yaml_to_asdf(yaml)
    with asdf.config_context() as cfg:
        cfg.add_extension(ExtensionProxy(FooExtension(), package_name, installed_package_version))
        with (
            pytest.warns(
                AsdfWarning,
                match=f"older package \\({package_name}=={installed_package_version}\\)",
            ),
            asdf.open(buff),
        ):
            pass

        buff.seek(0)

        # Make sure suppressing the warning works too
        with warnings.catch_warnings():
            warnings.simplefilter("error")
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

    buff = helpers.yaml_to_asdf(yaml)
    with (
        pytest.raises(
            RuntimeError,
            match=r"File was created with extension class .*, which is not currently installed",
        ),
        asdf.open(buff, strict_extension_check=True),
    ):
        pass

    # Make sure to test for incompatibility with ignore_missing_extensions
    buff.seek(0)
    with (
        pytest.raises(
            ValueError,
            match=r"'strict_extension_check' and 'ignore_missing_extensions' are incompatible options",
        ),
        asdf.open(buff, strict_extension_check=True, ignore_missing_extensions=True),
    ):
        pass


def test_metadata_with_custom_extension(tmp_path):
    class FractionConverter(Converter):
        tags = ["asdf://nowhere.org/tags/fraction-1.0.0"]
        types = [fractions.Fraction]

        def to_yaml_tree(self, obj, tag, ctx):
            return [obj.numerator, obj.denominator]

        def from_yaml_tree(self, node, tag, ctx):
            return fractions.Fraction(node[0], node[1])

    class FractionExtension(Extension):
        extension_uri = "asdf://nowhere.org/extensions/fraction-1.0.0"
        converters = [FractionConverter()]
        tags = FractionConverter.tags

    file_path = tmp_path / "custom_extension.asdf"

    with asdf.config_context() as config:
        config.add_extension(FractionExtension())

        tree = {"fraction": fractions.Fraction(2, 3)}

        with asdf.AsdfFile(tree) as ff:
            ff.write_to(file_path)

        # We expect metadata about both the Builtin extension and the custom one
        with asdf.open(file_path) as af:
            assert len(af["history"]["extensions"]) == 2

    with (
        pytest.warns(AsdfWarning, match=r"was created with extension"),
        asdf.open(
            file_path,
            ignore_unrecognized_tag=True,
        ),
    ):
        pass

    file_path_2 = tmp_path / "no_extension.asdf"

    # If we use the extension but we don't serialize any types that require it,
    # no metadata about this extension should be added to the file
    with asdf.config_context() as config:
        config.add_extension(FractionExtension())

        tree2 = {"x": list(range(10))}
        with asdf.AsdfFile(tree2) as ff:
            ff.write_to(file_path_2)

        with asdf.open(file_path_2) as af:
            assert len(af["history"]["extensions"]) == 1

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with asdf.open(file_path_2):
            pass

    file_path_3 = tmp_path / "custom_extension2.asdf"

    with asdf.config_context() as config:
        config.add_extension(FractionExtension())
        # Make sure that this works even when constructing the tree on-the-fly
        with asdf.AsdfFile() as ff:
            ff.tree["fraction"] = fractions.Fraction(4, 5)
            ff.write_to(file_path_3)

        with asdf.open(file_path_3) as af:
            assert len(af["history"]["extensions"]) == 2
