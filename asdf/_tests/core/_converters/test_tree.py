import datetime

import asdf
from asdf.tags.core import AsdfObject, ExtensionMetadata, HistoryEntry, Software, SubclassMetadata
from asdf.testing import helpers


def test_asdf_object():
    asdf_object = AsdfObject({"foo": "bar"})

    result = helpers.roundtrip_object(asdf_object)

    assert result == asdf_object


def test_extension_metadata():
    metadata = ExtensionMetadata(
        extension_class="foo.extension.FooExtension",
        extension_uri="http://foo.biz/extensions/foo-1.0.0",
        software=Software(name="FooSoft", version="1.5"),
    )

    result = helpers.roundtrip_object(metadata)

    assert result == metadata


def test_extension_metadata_extra_properties():
    yaml = """
metadata: !core/extension_metadata-1.0.0
  extension_class: foo.extension.FooExtension
  software: !core/software-1.0.0
    name: FooSoft
    version: "1.5"
  extension_uri: http://foo.biz/extensions/foo-1.0.0
  extra: property
    """

    buff = helpers.yaml_to_asdf(yaml)

    with asdf.open(buff) as af:
        assert af["metadata"].extension_class == "foo.extension.FooExtension"
        assert af["metadata"].software["name"] == "FooSoft"
        assert af["metadata"].software["version"] == "1.5"
        assert af["metadata"].extension_uri == "http://foo.biz/extensions/foo-1.0.0"
        assert af["metadata"]["extra"] == "property"


def test_software():
    software = Software(
        name="FooSoft",
        version="1.5.0",
        author="The Foo Developers",
        homepage="http://nowhere.org",
        extra="property",
    )

    result = helpers.roundtrip_object(software)

    assert result == software


def test_history_entry():
    history_entry = HistoryEntry(
        description="Some history happened here",
        time=datetime.datetime.now(),
        software=[Software(name="FooSoft", version="1.5.0")],
        extra="property",
    )

    result = helpers.roundtrip_object(history_entry)

    assert result == history_entry


def test_subclass_metadata():
    subclass_metadata = SubclassMetadata(name="SomeCoolSubclass")

    result = helpers.roundtrip_object(subclass_metadata)

    assert result == subclass_metadata
