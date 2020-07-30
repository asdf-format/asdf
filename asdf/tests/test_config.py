import threading

import pytest

import asdf
from asdf import get_config
from asdf import resource
from asdf.extension import BuiltinExtension, ExtensionProxy
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
            pass

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
    # fixture in asdf/tests/conftest.py.


def test_validate_on_read():
    with asdf.config_context() as config:
        assert config.validate_on_read == asdf._config.DEFAULT_VALIDATE_ON_READ
        config.validate_on_read = False
        assert get_config().validate_on_read is False
        config.validate_on_read = True
        assert get_config().validate_on_read is True


def test_default_asdf_standard_version():
    with asdf.config_context() as config:
        assert config.default_version == asdf._config.DEFAULT_DEFAULT_VERSION
        assert "1.2.0" != asdf._config.DEFAULT_DEFAULT_VERSION
        config.default_version = "1.2.0"
        assert config.default_version == "1.2.0"
        with pytest.raises(ValueError):
            config.default_version = "0.1.5"


def test_resource_mappings():
    with asdf.config_context() as config:
        core_mappings = resource.get_core_resource_mappings()

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
        config.add_resource_mapping(ResourceMappingProxy({"http://somewhere.org/schemas/bar-1.0.0": b"bar"}, package_name="foo"))
        config.remove_resource_mapping(package="foo")
        assert len(config.resource_mappings) == len(default_mappings)

        # Removing a mapping should be idempotent:
        config.add_resource_mapping(new_mapping)
        config.remove_resource_mapping(new_mapping)
        config.remove_resource_mapping(new_mapping)
        assert len(config.resource_mappings) == len(default_mappings)


def test_resource_manager():
    with asdf.config_context() as config:
        # Initial resource manager should contain just the entry points resources:
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        assert "http://somewhere.org/schemas/foo-1.0.0" not in config.resource_manager

        # Add a mapping and confirm that the manager now contains it:
        new_mapping = {"http://somewhere.org/schemas/foo-1.0.0": b"foo"}
        config.add_resource_mapping(new_mapping)
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        assert "http://somewhere.org/schemas/foo-1.0.0" in config.resource_manager
        assert config.resource_manager["http://somewhere.org/schemas/foo-1.0.0"] == b"foo"

        # Remove a mapping and confirm that the manager no longer contains it:
        config.remove_resource_mapping(new_mapping)
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        assert "http://somewhere.org/schemas/foo-1.0.0" not in config.resource_manager

        # Reset and confirm that the manager no longer contains the custom mapping:
        config.add_resource_mapping(new_mapping)
        config.reset_resources()
        assert "http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager
        assert b"http://stsci.edu/schemas/asdf/core/asdf-1.1.0" in config.resource_manager["http://stsci.edu/schemas/asdf/core/asdf-1.1.0"]
        assert "http://somewhere.org/schemas/foo-1.0.0" not in config.resource_manager


def test_extensions():
    with asdf.config_context() as config:
        original_extensions = config.extensions
        assert any(isinstance(e.delegate, BuiltinExtension) for e in original_extensions)

        class FooExtension:
            extension_uri = "http://somewhere.org/extensions/foo"
        new_extension = FooExtension()

        # Add an extension:
        config.add_extension(new_extension)
        assert len(config.extensions) == len(original_extensions) + 1
        assert any(e for e in config.extensions if e.delegate is new_extension)

        # Adding an extension should be idempotent:
        config.add_extension(new_extension)
        assert len(config.extensions) == len(original_extensions) + 1

        # Even when wrapped:
        config.add_extension(ExtensionProxy(new_extension))
        assert len(config.extensions) == len(original_extensions) + 1

        # Remove an extension:
        config.remove_extension(new_extension)
        assert len(config.extensions) == len(original_extensions)

        # Removing should work when wrapped:
        config.add_extension(new_extension)
        config.remove_extension(ExtensionProxy(new_extension))
        assert len(config.extensions) == len(original_extensions)

        # May also remove by URI:
        config.add_extension(new_extension)
        config.remove_extension(FooExtension.extension_uri)
        assert len(config.extensions) == len(original_extensions)

        # Remove by the name of the extension's package:
        config.add_extension(ExtensionProxy(new_extension, package_name="foo"))
        config.add_extension(ExtensionProxy(FooExtension(), package_name="foo"))
        config.remove_extension(package="foo")

        # Removing an extension should be idempotent:
        config.add_extension(new_extension)
        config.remove_extension(new_extension)
        config.remove_extension(new_extension)
        assert len(config.extensions) == len(original_extensions)

        # Resetting should get rid of any additions:
        config.add_extension(new_extension)
        config.add_extension(FooExtension())
        config.reset_extensions()
        assert len(config.extensions) == len(original_extensions)


def test_default_extensions():
    with asdf.config_context() as config:
        original_extensions = config.extensions
        original_default_extensions = config.default_extensions
        assert all(e.default for e in original_default_extensions)

        class NotDefaultExtension:
            extension_uri = "http://somewhere.org/extensions/not-default"
            default = False
        not_default_extension = NotDefaultExtension()

        class DefaultExtension:
            default = True
            extension_uri = "http://somewhere.org/extensions/default"
            default = True

        default_extension = DefaultExtension()

        # Adding a default extension should add it to the list:
        config.add_extension(default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1
        assert any(e for e in config.default_extensions if e.delegate is default_extension)

        # Adding should be idempotent:
        config.add_extension(default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1

        # Even when wrapped:
        config.add_extension(ExtensionProxy(default_extension))
        assert len(config.default_extensions) == len(original_default_extensions) + 1

        # Reset should clear the default list:
        config.reset_extensions()
        assert len(config.default_extensions) == len(original_default_extensions)

        # Non-default extension should not show up:
        config.add_extension(not_default_extension)
        assert len(config.default_extensions) == len(original_default_extensions)
        assert len(config.extensions) == len(original_extensions) + 1

        # But it can be made default:
        config.add_default_extension(not_default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1

        # Once again, idempotent:
        config.add_default_extension(not_default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1

        # Removing default status should not remove the extension entirely:
        config.remove_default_extension(not_default_extension)
        assert len(config.default_extensions) == len(original_default_extensions)
        assert len(config.extensions) == len(original_extensions) + 1

        # Removing is idempotent:
        config.remove_default_extension(not_default_extension)
        assert len(config.default_extensions) == len(original_default_extensions)
        assert len(config.extensions) == len(original_extensions) + 1

        # Add by URI:
        config.add_default_extension(NotDefaultExtension.extension_uri)
        assert len(config.default_extensions) == len(original_default_extensions) + 1

        # Remove by URI:
        config.remove_default_extension(NotDefaultExtension.extension_uri)
        assert len(config.default_extensions) == len(original_default_extensions)

        config.reset_extensions()

        # Remove default status from a default=True extension:
        config.add_extension(default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1
        config.remove_default_extension(default_extension)
        assert len(config.default_extensions) == len(original_default_extensions)

        config.reset_extensions()

        # Add a default extension that wasn't already registered:
        config.add_default_extension(not_default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1
        assert len(config.extensions) == len(original_extensions) + 1

        config.reset_extensions()

        # The same operation with an extension marked default:
        config.add_default_extension(default_extension)
        assert len(config.default_extensions) == len(original_default_extensions) + 1
        assert len(config.extensions) == len(original_extensions) + 1

        config.reset_extensions()

        # Remove default status by package name:
        config.add_extension(ExtensionProxy(default_extension, package_name="foo"))
        config.add_extension(ExtensionProxy(DefaultExtension(), package_name="foo"))
        assert len(config.default_extensions) == len(original_default_extensions) + 2
        config.remove_default_extension(package="foo")
        assert len(config.default_extensions) == len(original_default_extensions)


def test_get_extension():
    class SomeExtension:
        extension_uri = "http://somewhere.org/extensions/some"
    extension = SomeExtension()

    with asdf.config_context() as config:
        # Raise KeyError when extension does not exist
        with pytest.raises(KeyError):
            config.get_extension(SomeExtension.extension_uri)

        config.add_extension(extension)

        assert config.get_extension(SomeExtension.extension_uri).delegate is extension


def test_config_repr():
    with asdf.config_context() as config:
        config.validate_on_read = True
        config.default_version = "1.5.0"

        assert "validate_on_read: True" in repr(config)
        assert "default_version: 1.5.0" in repr(config)
