import pytest

from . import create_small_tree, create_large_tree

from asdf import config
from asdf import schema


@pytest.fixture
def small_tree():
    return create_small_tree()


@pytest.fixture
def large_tree():
    return create_large_tree()


@pytest.fixture(autouse=True)
def restore_default_config():
    yield
    config._global_config = config.AsdfConfig()
    config._local = config._ConfigLocal()


@pytest.fixture(autouse=True)
def clear_schema_cache():
    """
    Fixture that clears schema caches to prevent issues
    when tests use same URI for different schema content.
    """
    yield
    schema._load_schema.cache_clear()
    schema._load_schema_cached.cache_clear()
    schema.load_custom_schema.cache_clear()
