import pytest

from asdf import config_context
from asdf.asdf import AsdfFile, open_asdf
from asdf.extension import ExtensionProxy
from asdf.exceptions import AsdfWarning
from asdf.tests.helpers import yaml_to_asdf


def assert_correct_extensions(asdf_file, includes=[], excludes=[]):
    """
    Helper that asserts that extensions are included and/or
    excluded from an AsdfFile's enabled extension list.
    """
    includes = [ExtensionProxy.maybe_wrap(e) for e in includes]
    excludes = [ExtensionProxy.maybe_wrap(e) for e in excludes]

    def _count(extensions, extension):
        return sum(1 for e in extensions if e.delegate is extension.delegate)

    for extension in includes:
        assert _count(asdf_file.extensions, extension) == 1
        assert _count(asdf_file.extension_list.extensions, extension) == 1
    for extension in excludes:
        assert _count(asdf_file.extensions, extension) == 0
        assert _count(asdf_file.extension_list.extensions, extension) == 0


class TestExtension:
    __test__ = False

    def __init__(
        self,
        extension_uri,
        default=False,
        always_enabled=False,
        asdf_standard_requirement=None,
        legacy_class_names=None,
    ):
        self.extension_uri = extension_uri
        self.default = default
        self.always_enabled = always_enabled
        self.asdf_standard_requirement = asdf_standard_requirement
        if legacy_class_names is None:
            self.legacy_class_names = set()
        else:
            self.legacy_class_names = legacy_class_names


class LegacyExtension:
    pass


def test_asdf_file_initial_extensions():
    """
    Test extensions enabled on a new file under various
    config conditions.
    """
    with config_context() as config:
        non_default_extension = TestExtension("http://somewhere.org/extensions/non-default")
        config.add_extension(non_default_extension)
        assert_correct_extensions(AsdfFile(), excludes=[non_default_extension])
        assert_correct_extensions(AsdfFile(extensions=[non_default_extension]), includes=[non_default_extension])

    with config_context() as config:
        default_extension = TestExtension("http://somewhere.org/extensions/default", default=True)
        config.add_extension(default_extension)
        assert_correct_extensions(AsdfFile(), includes=[default_extension])
        assert_correct_extensions(AsdfFile(extensions=[]), excludes=[default_extension])
        assert_correct_extensions(AsdfFile(extensions=[default_extension]), includes=[default_extension])

    with config_context() as config:
        always_extension = TestExtension("http://somewhere.org/extensions/always", always_enabled=True)
        config.add_extension(always_extension)
        assert_correct_extensions(AsdfFile(), includes=[always_extension])
        assert_correct_extensions(AsdfFile(extensions=[]), includes=[always_extension])
        assert_correct_extensions(AsdfFile(extensions=[always_extension]), includes=[always_extension])

    with config_context() as config:
        version_extension = TestExtension("http://somewhere.org/extensions/version", default=True, asdf_standard_requirement=">1.3")
        config.add_extension(version_extension)
        assert_correct_extensions(AsdfFile(version="1.3.0"), excludes=[version_extension])
        assert_correct_extensions(AsdfFile(version="1.4.0"), includes=[version_extension])
        assert_correct_extensions(AsdfFile(version="1.4.0", extensions=[version_extension]), includes=[version_extension])

        with pytest.warns(AsdfWarning, match="does not support ASDF Standard version 1.3.0"):
            assert_correct_extensions(AsdfFile(version="1.3.0", extensions=[version_extension]), excludes=[version_extension])


def test_asdf_file_modify_extensions():
    af = AsdfFile(version="1.3.0")
    extension = TestExtension("http://somewhere.org/extensions/test")

    # Enable and disable by extension instance:
    af.add_extension(extension)
    assert_correct_extensions(af, includes=[extension])
    af.remove_extension(extension)
    assert_correct_extensions(af, excludes=[extension])

    with config_context() as config:
        # Enable and disable by URI:
        config.add_extension(extension)
        af.add_extension("http://somewhere.org/extensions/test")
        assert_correct_extensions(af, includes=[extension])
        af.remove_extension(extension)
        assert_correct_extensions(af, excludes=[extension])

    version_extension = TestExtension("http://somewhere.org/extensions/version", asdf_standard_requirement="==1.3.0")
    af.add_extension(version_extension)
    assert_correct_extensions(af, includes=[version_extension])

    invalid_version_extension = TestExtension("http://somewhere.org/extensions/invalid-version", asdf_standard_requirement="==1.4.0")
    with pytest.raises(ValueError):
        af.add_extension(invalid_version_extension)


def test_open_asdf_extensions():
    default_extension = TestExtension("http://somewhere.org/extensions/default", default=True)
    always_extension = TestExtension("http://somewhere.org/extensions/always", always_enabled=True)
    version_1_3_extension = TestExtension("http://somewhere.org/extensions/version-1.3.0", asdf_standard_requirement="==1.3.0")
    legacy_extension = ExtensionProxy(LegacyExtension(), legacy=True)
    auto_enabled_extension = TestExtension("http://somewhere.org/extensions/auto-enabled")

    with config_context() as config:
        config.add_extension(default_extension)
        config.add_extension(always_extension)
        config.add_extension(version_1_3_extension)
        config.add_extension(legacy_extension)
        config.add_extension(auto_enabled_extension)

        # Test missing history:
        content = """
        foo: bar
        """
        buff = yaml_to_asdf(content, standard_version="1.4.0")

        buff.seek(0)
        af = open_asdf(buff)
        assert_correct_extensions(
            af,
            includes=[always_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension, auto_enabled_extension]
        )

        buff.seek(0)
        af = open_asdf(buff, extensions=[default_extension])
        assert_correct_extensions(
            af,
            includes=[always_extension, default_extension, legacy_extension],
            excludes=[version_1_3_extension, auto_enabled_extension]
        )

        buff.seek(0)
        with pytest.warns(AsdfWarning, match="does not support ASDF Standard version 1.4.0"):
            af = open_asdf(buff, extensions=[version_1_3_extension, default_extension])
        assert_correct_extensions(
            af,
            includes=[always_extension, default_extension, legacy_extension],
            excludes=[version_1_3_extension, auto_enabled_extension]
        )

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

        buff.seek(0)
        af = open_asdf(buff)
        assert_correct_extensions(
            af,
            includes=[always_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension, auto_enabled_extension]
        )

        # Test auto-enabling based on metadata:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_class: asdf.extension.BuiltinExtension
            - !core/extension_metadata-1.0.0
              extension_uri: http://somewhere.org/extensions/auto-enabled
              extension_class: asdf.tests.test_asdf.TestExtension
            - !core/extension_metadata-1.0.0
              extension_class: asdf.tests.test_asdf.LegacyExtension
        """
        buff = yaml_to_asdf(content, standard_version="1.3.0")

        buff.seek(0)
        af = open_asdf(buff)
        assert_correct_extensions(
            af,
            includes=[always_extension, auto_enabled_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension]
        )

        # Test an extension from the new entry point selecting
        # on a legacy extension's class name:
        legacy_supporting_extension = TestExtension(
            "http://somewhere.org/extensions/legacy-supporting",
            legacy_class_names={"asdf.tests.test_asdf.LegacyExtension"}
        )
        config.add_extension(legacy_supporting_extension)

        buff.seek(0)
        af = open_asdf(buff)
        assert_correct_extensions(
            af,
            includes=[always_extension, auto_enabled_extension, legacy_supporting_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension]
        )
        # The extension list should contain both, but the new extension
        # should occur later so that its tag support overrides:
        legacy_index = [e.delegate for e in af.extensions].index(legacy_extension.delegate)
        legacy_supporting_index = [e.delegate for e in af.extensions].index(legacy_supporting_extension)
        assert legacy_supporting_index > legacy_index

        # Test that we receive a warning when extensions are manually
        # selected but exclude an extension listed in the metadata:
        buff.seek(0)
        with pytest.warns(AsdfWarning, match=r"File was created with extension URI http://somewhere\.org/extensions/auto-enabled"):
            af = open_asdf(buff, extensions=[])
        assert_correct_extensions(
            af,
            includes=[always_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension, legacy_supporting_extension]
        )

        # Missing extensions with a software property follow
        # a different code path:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_class: asdf.extension.BuiltinExtension
            - !core/extension_metadata-1.0.0
              extension_uri: http://somewhere.org/extensions/auto-enabled
              extension_class: asdf.tests.test_asdf.TestExtension
              software: !core/software-1.0.0
                name: FooSoft
                version: 5.10.1
        """
        buff = yaml_to_asdf(content, standard_version="1.3.0")
        buff.seek(0)
        with pytest.warns(AsdfWarning, match=r"File was created with extension URI http://somewhere\.org/extensions/auto-enabled \(from package FooSoft==5\.10\.1\)"):
            af = open_asdf(buff, extensions=[])
        assert_correct_extensions(
            af,
            includes=[always_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension, legacy_supporting_extension]
        )

        # Missing extensions without a URI follow yet another
        # code path:
        content = """
        history:
          extensions:
            - !core/extension_metadata-1.0.0
              extension_class: asdf.extension.BuiltinExtension
            - !core/extension_metadata-1.0.0
              extension_class: asdf.tests.test_asdf.TestExtension
              software: !core/software-1.0.0
                name: FooSoft
                version: 5.10.1
        """
        buff = yaml_to_asdf(content, standard_version="1.3.0")
        buff.seek(0)
        with pytest.warns(AsdfWarning, match=r"File was created with extension class asdf.tests.test_asdf.TestExtension \(from package FooSoft==5\.10\.1\)"):
            af = open_asdf(buff, extensions=[])
        assert_correct_extensions(
            af,
            includes=[always_extension, legacy_extension],
            excludes=[default_extension, version_1_3_extension, legacy_supporting_extension]
        )
