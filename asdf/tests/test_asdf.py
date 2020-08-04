import pytest

from asdf.asdf import AsdfFile, open_asdf, SerializationContext
from asdf import config_context, get_config
from asdf.versioning import AsdfVersion
from asdf.extension import ExtensionProxy, AsdfExtensionList


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


def test_asdf_file_extensions():
    af = AsdfFile()
    assert af.extensions == get_config().extensions

    class FooExtension:
        types = []
        tag_mapping = []
        url_mapping = []
    extension = FooExtension()

    for arg in ([extension], extension, AsdfExtensionList([extension])):
        af = AsdfFile(extensions=arg)
        assert af.extensions[0] == ExtensionProxy(extension)
        assert af.extensions[1:] == get_config().extensions

        af = AsdfFile()
        af.extensions = arg
        assert af.extensions[0] == ExtensionProxy(extension)
        assert af.extensions[1:] == get_config().extensions

    for arg in (object(), [object()]):
        with pytest.raises(TypeError):
            AsdfFile(extensions=arg)


def test_open_asdf_extensions(tmpdir):
    class FooExtension:
        types = []
        tag_mapping = []
        url_mapping = []
    extension = FooExtension()

    path = str(tmpdir/"test.asdf")

    with AsdfFile() as af:
        af.write_to(path)

    with open_asdf(path) as af:
        assert af.extensions == get_config().extensions

    for arg in ([extension], extension, AsdfExtensionList([extension])):
        with open_asdf(path, extensions=arg) as af:
            assert af.extensions[0] == ExtensionProxy(extension)
            assert af.extensions[1:] == get_config().extensions

    for arg in (object(), [object()]):
        with pytest.raises(TypeError):
            with open_asdf(path, extensions=arg) as af:
                pass


def test_serialization_context():
    context = SerializationContext("1.4.0")
    assert context.version == "1.4.0"
    assert context.extensions_used == set()

    extension = get_config().extensions[0]
    context.mark_extension_used(extension)
    assert context.extensions_used == {extension}
    context.mark_extension_used(extension)
    assert context.extensions_used == {extension}
    context.mark_extension_used(extension.delegate)
    assert context.extensions_used == {extension}

    with pytest.raises(TypeError):
        context.mark_extension_used(object())

    with pytest.raises(ValueError):
        SerializationContext("0.5.4")
