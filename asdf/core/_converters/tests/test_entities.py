import datetime

import asdf
from asdf.core import (
    AsdfObject,
    ExternalArrayReference,
    ExtensionMetadata,
    HistoryEntry,
    Software,
)
from asdf.testing import helpers


def test_asdf_object():
    asdf_object = AsdfObject({"foo": "bar"})

    result = helpers.roundtrip_object(asdf_object)

    assert result == asdf_object


def test_external_array_reference():
    ref = ExternalArrayReference("./nonexistant.fits", 1, "np.float64", (100, 100))

    result = helpers.roundtrip_object(ref)

    assert result == ref


def test_extension_metadata():
    metadata = ExtensionMetadata(
        "foo.extension.FooExtension",
        "http://foo.biz/extensions/foo-1.0.0",
        Software("FooSoft", "1.5"),
        {"extra": "property"}
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
        af["metadata"].extension_class == "foo.extension.FooExtension"
        af["metadata"].software.name == "FooSoft"
        af["metadata"].software.version == "1.5"
        af["metadata"].extension_uri == "http://foo.biz/extensions/foo-1.0.0"
        af["metadata"].extra == {"extra": "property"}


def test_software():
    software = Software(
        "FooSoft",
        "1.5.0",
        "The Foo Developers",
        "http://nowhere.org",
    )

    result = helpers.roundtrip_object(software)

    assert result == software


def test_history_entry():
    history_entry = HistoryEntry(
        "Some history happened here",
        time=datetime.datetime.now(),
        software=[Software("FooSoft", "1.5.0")]
    )

    result = helpers.roundtrip_object(history_entry)

    assert result == history_entry
