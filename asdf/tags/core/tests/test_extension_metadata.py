import asdf
from asdf.tests import helpers


def test_extra_properties():
    yaml = """
metadata: !core/extension_metadata-1.0.0
  extension_class: foo.extension.FooExtension
  software: !core/software-1.0.0
    name: FooSoft
    version: "1.5"
  extension_uri: http://foo.biz/extensions/foo-1.0.0
    """

    buff = helpers.yaml_to_asdf(yaml)

    with asdf.open(buff) as af:
        af["metadata"].extension_class == "foo.extension.FooExtension"
        af["metadata"].software["name"] == "FooSoft"
        af["metadata"].software["version"] == "1.5"
        af["metadata"]["extension_uri"] == "http://foo.biz/extensions/foo-1.0.0"
