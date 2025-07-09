import pytest

import asdf


def test_resolver_deprecation():

    def resolver(uri):
        return uri

    with pytest.warns(DeprecationWarning, match="resolver is deprecated"):
        asdf.schema.load_schema("http://stsci.edu/schemas/asdf/asdf-schema-1.0.0", resolver=resolver)


@pytest.mark.parametrize("value", (True, False))
def test_deprecate_refresh_extension_manager(value):
    af = asdf.AsdfFile({"foo": 1})
    with pytest.warns(DeprecationWarning, match="refresh_extension_manager is deprecated"):
        af.schema_info(refresh_extension_manager=value)
    with pytest.warns(DeprecationWarning, match="refresh_extension_manager is deprecated"):
        af.info(refresh_extension_manager=value)
    sr = af.search("foo")
    with pytest.warns(DeprecationWarning, match="refresh_extension_manager is deprecated"):
        sr.schema_info(refresh_extension_manager=value)


@pytest.mark.parametrize(
    "schema_property, schema_value",
    (
        ("ndim", 3),
        ("datatype", "uint8"),
        ("max_ndim", 3),
    ),
)
def test_validator_deprecation(tmp_path, schema_property, schema_value):
    schema = f"""%YAML 1.1
---
type: object
properties:
  a:
    {schema_property}: {schema_value}"""

    schema_path = tmp_path / "custom_schema.yaml"
    with schema_path.open("w") as f:
        f.write(schema)

    af = asdf.AsdfFile({"a": 1}, custom_schema=schema_path)
    with pytest.warns(DeprecationWarning, match=f"Use of the {schema_property} validator with non-ndarray tag"):
        with pytest.raises(asdf.exceptions.ValidationError):
            af.validate()


def test_url_mapping_deprecation():
    with pytest.warns(DeprecationWarning, match="url_mapping is deprecated"):
        asdf.schema.get_validator(url_mapping=lambda s: s)
