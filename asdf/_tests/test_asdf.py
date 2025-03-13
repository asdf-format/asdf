import os

import pytest

from asdf import config_context
from asdf._asdf import AsdfFile, open_asdf
from asdf._entry_points import get_extensions
from asdf._tests._helpers import assert_tree_match
from asdf.exceptions import AsdfWarning
from asdf.extension import ExtensionProxy
from asdf.testing.helpers import yaml_to_asdf
from asdf.versioning import AsdfVersion


def test_no_warnings_get_extensions():
    """
    Smoke test for changes to the `importlib.metadata` entry points API.
    """

    get_extensions()


class TestExtension:
    __test__ = False

    def __init__(
        self,
        extension_uri=None,
        legacy_class_names=None,
        asdf_standard_requirement=None,
        types=None,
        tag_mapping=None,
        url_mapping=None,
    ):
        self._extension_uri = extension_uri
        self._legacy_class_names = set() if legacy_class_names is None else legacy_class_names
        self._asdf_standard_requirement = asdf_standard_requirement
        self._types = [] if types is None else types
        self._tag_mapping = [] if tag_mapping is None else tag_mapping
        self._url_mapping = [] if url_mapping is None else url_mapping

    @property
    def types(self):
        return self._types

    @property
    def tag_mapping(self):
        return self._tag_mapping

    @property
    def url_mapping(self):
        return self._url_mapping

    @property
    def extension_uri(self):
        return self._extension_uri

    @property
    def legacy_class_names(self):
        return self._legacy_class_names

    @property
    def asdf_standard_requirement(self):
        return self._asdf_standard_requirement


def test_asdf_file_version():
    with config_context() as config:
        config.default_version = "1.2.0"

        af = AsdfFile()
        assert af.version == AsdfVersion("1.2.0")
        assert af.version_string == "1.2.0"

        af = AsdfFile(version="1.3.0")
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        af = AsdfFile(version=AsdfVersion("1.3.0"))
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
            AsdfFile(version="0.5.4")

        with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
            AsdfFile(version=AsdfVersion("0.5.4"))

        af = AsdfFile()

        af.version = "1.3.0"
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        af.version = AsdfVersion("1.4.0")
        assert af.version == AsdfVersion("1.4.0")
        assert af.version_string == "1.4.0"

        with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
            af.version = "0.5.4"

        with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
            af.version = AsdfVersion("2.5.4")


def test_asdf_file_extensions():
    af = AsdfFile()
    assert af.extensions == []

    extension = TestExtension(extension_uri="asdf://somewhere.org/extensions/foo-1.0")

    for arg in ([extension], extension):
        af = AsdfFile(extensions=arg)
        assert af.extensions == [ExtensionProxy(extension)]

        af = AsdfFile()
        af.extensions = arg
        assert af.extensions == [ExtensionProxy(extension)]

    msg = r"[The extensions parameter must be an extension.*, Extension must implement the Extension interface]"
    for arg in (object(), [object()]):
        with pytest.raises(TypeError, match=msg):
            AsdfFile(extensions=arg)


def test_asdf_file_version_requirement():
    extension_with_requirement = TestExtension(
        extension_uri="asdf://somewhere.org/extensions/foo-1.0",
        asdf_standard_requirement="==1.5.0",
    )

    # No warnings if the requirement is fulfilled:
    AsdfFile(version="1.5.0", extensions=[extension_with_requirement])

    # Version doesn't match the requirement, so we should see a warning
    # and the extension should not be enabled:
    with pytest.warns(AsdfWarning, match=r"does not support ASDF Standard 1.4.0"):
        af = AsdfFile(version="1.4.0", extensions=[extension_with_requirement])
        assert ExtensionProxy(extension_with_requirement) not in af.extensions

    # Version initially matches the requirement, but changing
    # the version on the AsdfFile invalidates it:
    af = AsdfFile(version="1.5.0", extensions=[extension_with_requirement])
    assert ExtensionProxy(extension_with_requirement) in af.extensions
    with pytest.warns(AsdfWarning, match=r"does not support ASDF Standard 1.4.0"):
        af.version = "1.4.0"
    assert ExtensionProxy(extension_with_requirement) not in af.extensions

    # Extension registered with the config should not provoke
    # a warning:
    with config_context() as config:
        config.add_extension(extension_with_requirement)
        af = AsdfFile(version="1.4.0")

        # ... unless the user explicitly requested the invalid extension:
        with pytest.warns(AsdfWarning, match=r"does not support ASDF Standard 1.4.0"):
            af = AsdfFile(version="1.4.0", extensions=[extension_with_requirement])


def test_open_asdf_extensions(tmp_path):
    extension = TestExtension(extension_uri="asdf://somewhere.org/extensions/foo-1.0")

    path = str(tmp_path / "test.asdf")

    with AsdfFile() as af:
        af.write_to(path)

    with open_asdf(path) as af:
        assert af.extensions == []

    for arg in ([extension], extension):
        with open_asdf(path, extensions=arg) as af:
            assert af.extensions == [ExtensionProxy(extension)]

    msg = r"[The extensions parameter must be an extension.*, Extension must implement the Extension interface]"
    for arg in (object(), [object()]):
        with pytest.raises(TypeError, match=msg), open_asdf(path, extensions=arg) as af:
            pass


def test_reading_extension_metadata():
    extension_with_uri = ExtensionProxy(
        TestExtension(extension_uri="asdf://somewhere.org/extensions/foo-1.0"),
        package_name="foo",
        package_version="1.2.3",
    )
    extension_without_uri = ExtensionProxy(
        TestExtension(),
        package_name="foo",
        package_version="1.2.3",
    )
    extension_with_legacy_class_names = ExtensionProxy(
        TestExtension(
            extension_uri="asdf://somewhere.org/extensions/with-legacy-1.0",
            legacy_class_names={"some.legacy.class.Name"},
        ),
        package_name="foo",
        package_version="1.2.3",
    )

    with config_context() as config:
        config.add_extension(extension_with_uri)
        config.add_extension(extension_without_uri)
        config.add_extension(extension_with_legacy_class_names)

        # Test missing history:
        content = "foo: bar"
        buff = yaml_to_asdf(content)
        open_asdf(buff)

        # Test the old history format:
        content = """
history:
  - !core/history_entry-1.0.0
    description: Once upon a time, there was a carnivorous panda.
  - !core/history_entry-1.0.0
    description: This entry intentionally left blank.
foo: bar
        """
        buff = yaml_to_asdf(content, version="1.0.0")
        open_asdf(buff)

        # Test matching by URI:
        content = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_uri: asdf://somewhere.org/extensions/foo-1.0
      extension_class: some.unrecognized.extension.class.Name
        """
        buff = yaml_to_asdf(content)
        open_asdf(buff)

        # Test matching by legacy class name:
        content = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_class: some.legacy.class.Name
        """
        buff = yaml_to_asdf(content)
        open_asdf(buff)

        # Warn when the URI is missing, even if there's
        # a class name match:
        content = f"""
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_uri: some-missing-URI
      extension_class: {extension_with_uri.class_name}
        """
        buff = yaml_to_asdf(content)
        with pytest.warns(AsdfWarning, match=r"URI 'some-missing-URI'"):
            open_asdf(buff)

        # Warn when the class name is missing:
        content = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_class: some.missing.class.Name
        """
        buff = yaml_to_asdf(content)
        with pytest.warns(AsdfWarning, match=r"class 'some.missing.class.Name'"):
            open_asdf(buff)

        # Warn when the package version is older:
        content = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_uri: asdf://somewhere.org/extensions/foo-1.0
      extension_class: some.class.Name
      software: !core/software-1.0.0
        name: foo
        version: 9.2.4
        """
        buff = yaml_to_asdf(content)
        with pytest.warns(AsdfWarning, match=r"older package"):
            open_asdf(buff)

        # Shouldn't warn when the package version is later:
        content = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_uri: asdf://somewhere.org/extensions/foo-1.0
      extension_class: some.class.Name
      software: !core/software-1.0.0
        name: foo
        version: 0.1.2
        """
        buff = yaml_to_asdf(content)
        open_asdf(buff)

        # Shouldn't receive a warning when the package
        # name changes, even if the version is later:
        content = """
history:
  extensions:
    - !core/extension_metadata-1.0.0
      extension_uri: asdf://somewhere.org/extensions/foo-1.0
      extension_class: some.class.Name
      software: !core/software-1.0.0
        name: bar
        version: 9.4.5
        """
        buff = yaml_to_asdf(content)
        open_asdf(buff)


def test_bad_input(tmp_path):
    """Make sure these functions behave properly with bad input"""
    text_file = str(tmp_path / "test.txt")

    with open(text_file, "w") as fh:
        fh.write("I <3 ASDF!!!!!")

    with pytest.raises(
        ValueError,
        match=r"Does not appear to be a ASDF file.",
    ):
        open_asdf(text_file)


def test_unclosed_file(tmp_path):
    """
    Issue #1006 reported an unclosed file when asdf.open fails
    This is a regression test for the fix in PR #1221
    """
    path = tmp_path / "empty.asdf"
    path.touch()

    with (
        pytest.raises(
            ValueError,
            match=r"Does not appear to be a ASDF file.",
        ),
        open_asdf(path),
    ):
        pass


def test_fsspec(tmp_path):
    """
    Issue #1146 reported errors when opening a fsspec 'file'
    This is a regression test for the fix in PR #1226
    """
    fsspec = pytest.importorskip("fsspec")

    tree = {"a": 1}
    af = AsdfFile(tree)
    fn = tmp_path / "test.asdf"
    af.write_to(fn)

    with fsspec.open(fn) as f:
        af = open_asdf(f)
        assert_tree_match(tree, af.tree)


@pytest.mark.remote_data()
def test_fsspec_http(httpserver):
    """
    Issue #1146 reported errors when opening a fsspec url (using the http
    filesystem)
    This is a regression test for the fix in PR #1228
    """
    fsspec = pytest.importorskip("fsspec")

    tree = {"a": 1}
    af = AsdfFile(tree)
    path = os.path.join(httpserver.tmpdir, "test")
    af.write_to(path)

    fn = httpserver.url + "test"
    with fsspec.open(fn) as f:
        af = open_asdf(f)
        assert_tree_match(tree, af.tree)
