import datetime

import asdf
from asdf.core import (
    AsdfObject,
    ExtensionMetadata,
    ExternalArrayReference,
    HistoryEntry,
    Software,
)
from asdf.testing import helpers


def test_asdf_object():
    asdf_object = AsdfObject({"foo": "bar"})

    result = helpers.roundtrip_object(asdf_object)

    assert result == asdf_object


def test_external_array_reference():
    ref = ExternalArrayReference(
        fileuri="./nonexistant.fits",
        target=1,
        datatype="np.float64",
        shape=(100, 100),
        extra={"extra": "property"},
    )

    result = helpers.roundtrip_object(ref)

    assert result == ref


def test_extension_metadata():
    metadata = ExtensionMetadata(
        extension_class="foo.extension.FooExtension",
        extension_uri="http://foo.biz/extensions/foo-1.0.0",
        software=Software("FooSoft", "1.5"),
        extra={"extra": "property"},
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
        name="FooSoft",
        version="1.5.0",
        author="The Foo Developers",
        homepage="http://nowhere.org",
        extra={"extra": "property"},
    )

    result = helpers.roundtrip_object(software)

    assert result == software


def test_history_entry():
    history_entry = HistoryEntry(
        "Some history happened here",
        time=datetime.datetime.now(),
        software=[Software("FooSoft", "1.5.0")],
        extra={"extra": "property"},
    )

    result = helpers.roundtrip_object(history_entry)

    assert result == history_entry
