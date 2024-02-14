import threading

import asdf_standard.integration
import pytest

import asdf
from asdf import get_config
from asdf._core._integration import get_json_schema_resource_mappings
from asdf.extension import ExtensionProxy
from asdf.resource import ResourceMappingProxy


def test_config_context():
    assert get_config().validate_on_read is True

    with asdf.config_context() as config:
        config.validate_on_read = False
        assert get_config().validate_on_read is False

    assert get_config().validate_on_read is True


def test_config_context_nested():
    assert get_config().validate_on_read is True

    with asdf.config_context() as config1:
        config1.validate_on_read = False
        with asdf.config_context() as config2:
            config2.validate_on_read = True
            with asdf.config_context() as config3:
                config3.validate_on_read = False
                assert get_config().validate_on_read is False

    assert get_config().validate_on_read is True


def test_config_context_threaded():
    assert get_config().validate_on_read is True

    thread_value = None

    def worker():
        nonlocal thread_value
        thread_value = get_config().validate_on_read
        with asdf.config_context() as config:
            config.validate_on_read = False

    with asdf.config_context() as config:
        config.validate_on_read = False
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

    assert thread_value is True
    assert get_config().validate_on_read is True


def test_global_config():
    assert get_config().validate_on_read is True

    get_config().validate_on_read = False
    assert get_config().validate_on_read is False

    with asdf.config_context() as config:
        assert config.validate_on_read is False
        config.validate_on_read = True
        assert get_config().validate_on_read is True

    assert get_config().validate_on_read is False

    # Global config is reset to defaults by autouse
    # fixture in asdf/_tests/conftest.py.


def test_validate_on_read():
    with asdf.config_context() as config:
        assert config.validate_on_read == asdf.config.DEFAULT_VALIDATE_ON_READ
        config.validate_on_read = False
        assert get_config().validate_on_read is False
        config.validate_on_read = True
        assert get_config().validate_on_read is True


def test_default_version():
    with asdf.config_context() as config:
        assert config.default_version == asdf.config.DEFAULT_DEFAULT_VERSION
        assert asdf.config.DEFAULT_DEFAULT_VERSION != "1.2.0"
        config.default_version = "1.2.0"
        assert config.default_version == "1.2.0"
        with pytest.raises(ValueError, match=r"ASDF Standard version .* is not supported by asdf==.*"):
            config.default_version = "0.1.5"


def test_legacy_fill_schema_defaults():
    with asdf.config_context() as config:
        assert config.legacy_fill_schema_defaults == asdf.config.DEFAULT_LEGACY_FILL_SCHEMA_DEFAULTS
        config.legacy_fill_schema_defaults = False
        assert get_config().legacy_fill_schema_defaults is False
        config.legacy_fill_schema_defaults = True
        assert get_config().legacy_fill_schema_defaults is True


def test_array_inline_threshold():
    with asdf.config_context() as config:
        assert config.array_inline_threshold == asdf.config.DEFAULT_ARRAY_INLINE_THRESHOLD
        config.array_inline_threshold = 10
        assert get_config().array_inline_threshold == 10
        config.array_inline_threshold = None
        assert get_config().array_inline_threshold is None


def test_all_array_storage():
    with asdf.config_context() as config:
        assert config.all_array_storage == asdf.config.DEFAULT_ALL_ARRAY_STORAGE
        config.all_array_storage = "internal"
        assert get_config().all_array_storage == "internal"
        config.all_array_storage = None
        assert get_config().all_array_storage is None
        with pytest.raises(ValueError, match=r"Invalid value for all_array_storage"):
            config.all_array_storage = "foo"


def test_all_array_compression():
    with asdf.config_context() as config:
        assert config.all_array_compression == asdf.config.DEFAULT_ALL_ARRAY_COMPRESSION
        config.all_array_compression = "zlib"
        assert get_config().all_array_compression == "zlib"
        config.all_array_compression = None
        assert get_config().all_array_compression is None
        with pytest.raises(ValueError, match=r"Supported compression types are"):
            config.all_array_compression = "foo"


def test_all_array_compression_kwargs():
    with asdf.config_context() as config:
        assert config.all_array_compression_kwargs == asdf.config.DEFAULT_ALL_ARRAY_COMPRESSION_KWARGS
        config.all_array_compression_kwargs = {}
        assert get_config().all_array_compression_kwargs == {}
        config.all_array_compression_kwargs = None
        assert get_config().all_array_compression_kwargs is None
        with pytest.raises(ValueError, match=r"Invalid value for all_array_compression_kwargs"):
            config.all_array_compression_kwargs = "foo"


def test_resource_mappings():
    with asdf.config_context() as config:
        core_mappings = get_json_schema_resource_mappings() + asdf_standard.integration.get_resource_mappings()

        default_mappings = config.resource_mappings
        assert len(default_mappings) >= len(core_mappings)

        new_mapping = {"http://somewhere.org/schemas/foo-1.0.0": b"foo"}
        config.add_resource_mapping(new_mapping)

        assert len(config.resource_mappings) == len(default_mappings) + 1
        assert any(m for m in config.resource_mappings if m.delegate is new_mapping)

        # Adding a mapping should be idempotent:
        config.add_resource_mapping(new_mapping)
        # ... even if wrapped:
        config.add_resource_mapping(ResourceMappingProxy(new_mapping))
        assert len(config.resource_mappings) == len(default_mappings) + 1

        # Adding a mapping should place it at the front of the line:
        front_mapping = {"http://somewhere.org/schemas/baz-1.0.0": b"baz"}
        config.add_resource_mapping(front_mapping)
        assert len(config.resource_mappings) == len(default_mappings) + 2
        assert config.resource_mappings[0].delegate is front_mapping

        # ... even if the mapping is already in the list:
        config.add_resource_mapping(new_mapping)
        assert len(config.resource_mappings) == len(default_mappings) + 2
        assert config.resource_mappings[0].delegate is new_mapping

        # Reset should get rid of any additions:
        config.reset_resources()
        assert len(config.resource_mappings) == len(default_mappings)

        # Should be able to remove a mapping:
        config.add_resource_mapping(new_mapping)
        config.remove_resource_mapping(new_mapping)
        assert len(config.resource_mappings) == len(default_mappings)

        # ... even if wrapped:
        config.add_resource_mapping(new_mapping)
        config.remove_resource_mapping(ResourceMappingProxy(new_mapping))
        assert len(config.resource_mappings) == len(default_mappings)

        # ... and also by the name of the package the mappings came from:
        config.add_resource_mapping(ResourceMappingProxy(new_mapping, package_name="foo"))
        config.add_resource_mapping(
            ResourceMappingProxy({"http://somewhere.org/schemas/bar-1.0.0": b"bar"}, package_name="foo"),
        )
        config.remove_resource_mapping(package="foo")
        assert len(config.resource_mappings) == len(default_mappings)

        # Can combine the package and mapping filters when removing:
        config.add_resource_mapping(ResourceMappingProxy(new_mapping, package_name="foo"))
        config.remove_resource_mapping(new_mapping, package="foo")
        assert len(config.resource_mappings) == len(default_mappings)

        # But not omit both:
        with pytest.raises(ValueError, match=r"Must specify at least one of mapping or package"):
            config.remove_resource_mapping()

        # Removing a mapping should be idempotent:
        config.add_resource_mapping(new_mapping)
        config.remove_resource_mapping(new_mapping)
        config.remove_resource_mapping(new_mapping)
        assert len(config.resource_mappings) == len(default_mappings)


def test_resource_manager():
    with asdf.config_context() as config:
        # Initial resource manager should contain just the entry points resources:
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert (
            b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0"
            in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        )
        assert "http://somewhere.org/schemas/foo-1.0.0" not in config.resource_manager

        # Add a mapping and confirm that the manager now contains it:
        new_mapping = {"http://somewhere.org/schemas/foo-1.0.0": b"foo"}
        config.add_resource_mapping(new_mapping)
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert (
            b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0"
            in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        )
        assert "http://somewhere.org/schemas/foo-1.0.0" in config.resource_manager
        assert config.resource_manager["http://somewhere.org/schemas/foo-1.0.0"] == b"foo"

        # Remove a mapping and confirm that the manager no longer contains it:
        config.remove_resource_mapping(new_mapping)
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert (
            b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0"
            in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        )
        assert "http://somewhere.org/schemas/foo-1.0.0" not in config.resource_manager

        # Reset and confirm that the manager no longer contains the custom mapping:
        config.add_resource_mapping(new_mapping)
        config.reset_resources()
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert (
            b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0"
            in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        )
        assert "http://somewhere.org/schemas/foo-1.0.0" not in config.resource_manager


def test_extensions():
    with asdf.config_context() as config:
        original_extensions = config.extensions

        class BarExtension:
            extension_uri = "asdf://somewhere.org/extensions/bar-1.0"
            types = []
            tag_mapping = []
            url_mapping = []

        uri_extension = BarExtension()

        # Add an extension:
        config.add_extension(uri_extension)
        assert len(config.extensions) == len(original_extensions) + 1
        assert any(e for e in config.extensions if e.delegate is uri_extension)

        # Adding an extension should be idempotent:
        config.add_extension(uri_extension)
        assert len(config.extensions) == len(original_extensions) + 1

        # Even when wrapped:
        config.add_extension(ExtensionProxy(uri_extension))
        assert len(config.extensions) == len(original_extensions) + 1

        # Remove an extension:
        config.remove_extension(uri_extension)
        assert len(config.extensions) == len(original_extensions)

        # Removing should work when wrapped:
        config.add_extension(uri_extension)
        config.remove_extension(ExtensionProxy(uri_extension))
        assert len(config.extensions) == len(original_extensions)

        # And also by URI:
        config.add_extension(uri_extension)
        config.remove_extension(uri_extension.extension_uri)
        assert len(config.extensions) == len(original_extensions)

        # And also by URI pattern:
        config.add_extension(uri_extension)
        config.remove_extension("asdf://somewhere.org/extensions/*")
        assert len(config.extensions) == len(original_extensions)

        # Remove by the name of the extension's package:
        config.add_extension(ExtensionProxy(uri_extension, package_name="foo"))
        config.remove_extension(package="foo")
        assert len(config.extensions) == len(original_extensions)

        # Can combine remove filters:
        config.add_extension(ExtensionProxy(uri_extension, package_name="foo"))
        config.add_extension(ExtensionProxy(uri_extension, package_name="bar"))
        config.remove_extension(uri_extension.extension_uri, package="foo")
        assert len(config.extensions) == len(original_extensions) + 1

        # ... but not omit both:
        with pytest.raises(ValueError, match=r"Must specify at least one of extension or package"):
            config.remove_extension()

        # Removing an extension should be idempotent:
        config.add_extension(uri_extension)
        config.remove_extension(uri_extension)
        config.remove_extension(uri_extension)
        assert len(config.extensions) == len(original_extensions)

        # Resetting should get rid of any additions:
        config.add_extension(uri_extension)
        config.reset_extensions()
        assert len(config.extensions) == len(original_extensions)


def test_config_repr():
    with asdf.config_context() as config:
        config.validate_on_read = True
        config.default_version = "1.5.0"
        config.io_block_size = 9999
        config.legacy_fill_schema_defaults = False
        config.array_inline_threshold = 14

        assert "validate_on_read: True" in repr(config)
        assert "default_version: 1.5.0" in repr(config)
        assert "io_block_size: 9999" in repr(config)
        assert "legacy_fill_schema_defaults: False" in repr(config)
        assert "array_inline_threshold: 14" in repr(config)


@pytest.mark.parametrize("value", [True, False])
def test_get_set_default_array_save_base(value):
    with asdf.config_context() as config:
        config.default_array_save_base = value
        assert config.default_array_save_base == value


@pytest.mark.parametrize("value", [1, None])
def test_invalid_set_default_array_save_base(value):
    with asdf.config_context() as config:
        with pytest.raises(ValueError, match="default_array_save_base must be a bool"):
            config.default_array_save_base = value
