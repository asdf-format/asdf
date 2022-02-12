import pytest

from asdf.asdf import AsdfFile, open_asdf, SerializationContext
from asdf import config_context, get_config
from asdf.versioning import AsdfVersion
from asdf.exceptions import AsdfWarning
from asdf.extension import ExtensionProxy, ExtensionManager
from asdf.tests.helpers import yaml_to_asdf, assert_no_warnings


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

        with pytest.raises(ValueError):
            AsdfFile(version="0.5.4")

        with pytest.raises(ValueError):
            AsdfFile(version=AsdfVersion("0.5.4"))

        af = AsdfFile()

        af.version = "1.3.0"
        assert af.version == AsdfVersion("1.3.0")
        assert af.version_string == "1.3.0"

        af.version = AsdfVersion("1.4.0")
        assert af.version == AsdfVersion("1.4.0")
        assert af.version_string == "1.4.0"

        with pytest.raises(ValueError):
            af.version = "0.5.4"

        with pytest.raises(ValueError):
            af.version = AsdfVersion("2.5.4")

        af.version = "1.0.0"
        assert af.version_map["tags"]["tag:stsci.edu:asdf/core/asdf"] == "1.0.0"

        af.version = "1.2.0"
        assert af.version_map["tags"]["tag:stsci.edu:asdf/core/asdf"] == "1.1.0"


def test_serialization_context():
    extension_manager = ExtensionManager([])
    context = SerializationContext("1.4.0", extension_manager, "file://test.asdf")
    assert context.version == "1.4.0"
    assert context.extension_manager is extension_manager
    assert context._extensions_used == set()

    extension = get_config().extensions[0]
    context._mark_extension_used(extension)
    assert context._extensions_used == {extension}
    context._mark_extension_used(extension)
    assert context._extensions_used == {extension}
    context._mark_extension_used(extension.delegate)
    assert context._extensions_used == {extension}

    assert context.url == context._url == "file://test.asdf"

    with pytest.raises(TypeError):
        context._mark_extension_used(object())

    with pytest.raises(ValueError):
        SerializationContext("0.5.4", extension_manager, None)


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
        content = """
        foo: bar
        """
        buff = yaml_to_asdf(content)
        with assert_no_warnings():
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
        buff = yaml_to_asdf(content, standard_version="1.0.0")
        with assert_no_warnings():
            open_asdf(buff)

        # Test legacy extension matching by actual class name:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_class: asdf.tests.test_asdf.TestExtension
        """
        buff = yaml_to_asdf(content)
        with assert_no_warnings():
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
        with assert_no_warnings():
            open_asdf(buff)

        # Test matching by legacy class name:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_class: some.legacy.class.Name
        """
        buff = yaml_to_asdf(content)
        with assert_no_warnings():
            open_asdf(buff)

        # Warn when the URI is missing, even if there's
        # a class name match:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_uri: some-missing-URI
              extension_class: {}
        """.format(extension_with_uri.class_name)
        buff = yaml_to_asdf(content)
        with pytest.warns(AsdfWarning, match="URI 'some-missing-URI'"):
            open_asdf(buff)

        # Warn when the class name is missing:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_class: some.missing.class.Name
        """
        buff = yaml_to_asdf(content)
        with pytest.warns(AsdfWarning, match="class 'some.missing.class.Name'"):
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
        with pytest.warns(AsdfWarning, match="older package"):
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
        with assert_no_warnings():
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
        with assert_no_warnings():
            open_asdf(buff)
