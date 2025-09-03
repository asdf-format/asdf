import pytest

import asdf


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
