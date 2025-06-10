import pytest

import asdf
from asdf.exceptions import ValidationError


def test_custom_validation_bad(tmp_path, test_data_path):
    custom_schema_path = test_data_path / "custom_schema.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree does not conform to the custom schema
    tree = {"stuff": 42, "other_stuff": "hello"}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file using custom schema should fail
    af = asdf.AsdfFile(custom_schema=custom_schema_path)
    af._tree = asdf.tags.core.AsdfObject(tree)
    with pytest.raises(ValidationError, match=r".* is a required property"):
        af.validate()
        pass

    # Opening file without custom schema should pass
    with asdf.open(asdf_file):
        pass

    # Opening file with custom schema should fail
    with (
        pytest.raises(ValidationError, match=r".* is a required property"),
        asdf.open(
            asdf_file,
            custom_schema=custom_schema_path,
        ),
    ):
        pass


def test_custom_validation_good(tmp_path, test_data_path):
    custom_schema_path = test_data_path / "custom_schema.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"foo": {"x": 42, "y": 10}, "bar": {"a": "hello", "b": "banjo"}}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_pathlib(tmp_path, test_data_path):
    """
    Make sure custom schema paths can be pathlib.Path objects

    See https://github.com/asdf-format/asdf/issues/653 for discussion.
    """
    custom_schema_path = test_data_path / "custom_schema.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"foo": {"x": 42, "y": 10}, "bar": {"a": "hello", "b": "banjo"}}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_with_definitions_good(tmp_path, test_data_path):
    custom_schema_path = test_data_path / "custom_schema_definitions.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"thing": {"biz": "hello", "baz": "world"}}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_with_definitions_bad(tmp_path, test_data_path):
    custom_schema_path = test_data_path / "custom_schema_definitions.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree does NOT conform to the custom schema
    tree = {"forb": {"biz": "hello", "baz": "world"}}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file with custom schema should fail
    af = asdf.AsdfFile(custom_schema=custom_schema_path)
    af._tree = asdf.tags.core.AsdfObject(tree)
    with pytest.raises(ValidationError, match=r".* is a required property"):
        af.validate()

    # Opening file without custom schema should pass
    with asdf.open(asdf_file):
        pass

    # Opening file with custom schema should fail
    with (
        pytest.raises(ValidationError, match=r".* is a required property"),
        asdf.open(
            asdf_file,
            custom_schema=custom_schema_path,
        ),
    ):
        pass


def test_custom_validation_with_external_ref_good(tmp_path, test_data_path):
    custom_schema_path = test_data_path / "custom_schema_external_ref.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree conforms to the custom schema
    tree = {"foo": asdf.tags.core.Software(name="Microsoft Windows", version="95")}

    with asdf.AsdfFile(tree, custom_schema=custom_schema_path) as ff:
        ff.write_to(asdf_file)

    with asdf.open(asdf_file, custom_schema=custom_schema_path):
        pass


def test_custom_validation_with_external_ref_bad(tmp_path, test_data_path):
    custom_schema_path = test_data_path / "custom_schema_external_ref.yaml"
    asdf_file = str(tmp_path / "out.asdf")

    # This tree does not conform to the custom schema
    tree = {"foo": False}

    # Creating file without custom schema should pass
    with asdf.AsdfFile(tree) as ff:
        ff.write_to(asdf_file)

    # Creating file with custom schema should fail
    af = asdf.AsdfFile(custom_schema=custom_schema_path)
    af["foo"] = False
    with pytest.raises(ValidationError, match=r"False is not valid under any of the given schemas"):
        af.validate()

    # Opening file without custom schema should pass
    with asdf.open(asdf_file):
        pass

    # Opening file with custom schema should fail
    with (
        pytest.raises(ValidationError, match=r"False is not valid under any of the given schemas"),
        asdf.open(
            asdf_file,
            custom_schema=custom_schema_path,
        ),
    ):
        pass
