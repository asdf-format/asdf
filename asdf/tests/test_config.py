import threading

import asdf
from asdf import get_config
from asdf import resource
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
        assert config.validate_on_read == asdf.config.DEFAULT_VALIDATE_ON_READ
        config.validate_on_read = False
        assert get_config().validate_on_read is False
        config.validate_on_read = True
        assert get_config().validate_on_read is True


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


def test_config_repr():
    with asdf.config_context() as config:
        config.validate_on_read = True

        assert "validate_on_read: True" in repr(config)
