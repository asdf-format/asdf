import yaml

import pytest

import asdf
from asdf.core._integration import get_resource_mappings, get_extensions


@pytest.mark.parametrize("uri", [
    "http://json-schema.org/draft-04/schema",
    "http://stsci.edu/schemas/yaml-schema/draft-01",
    "http://stsci.edu/schemas/asdf/core/asdf-1.1.0",
    "asdf://asdf-format.org/core/schemas/extension_manifest-1.0.0",
])
def test_get_resource_mappings(uri):
    mappings = get_resource_mappings()

    mapping = next(m for m in mappings if uri in m)
    assert mapping is not None

    assert uri.encode("utf-8") in mapping[uri]


def test_get_extensions():
    extensions = get_extensions()
    extension_uris = {e.extension_uri for e in extensions}

    # No duplicates
    assert len(extension_uris) == len(extensions)

    resource_extension_uris = set()
    resource_manager = asdf.get_config().resource_manager
    for resource_uri in resource_manager:
        if resource_uri.startswith("asdf://asdf-format.org/core/manifests/core-"):
            resource_extension_uris.add(yaml.safe_load(resource_manager[resource_uri])["extension_uri"])

    # Make sure every core manifest has a corresponding extension
    assert resource_extension_uris == extension_uris
