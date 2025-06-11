from contextlib import nullcontext

import pytest

import asdf
from asdf.exceptions import ValidationError

# test cases with:
# - custom schema path
# - tree
# - expected error (or None)
TEST_CASES = [
    (
        "custom_schema.yaml",
        {"stuff": 42, "other_stuff": "hello"},
        ".* is a required property",
    ),
    (
        "custom_schema.yaml",
        {"foo": {"x": 42, "y": 10}, "bar": {"a": "hello", "b": "banjo"}},
        None,
    ),
    (
        "custom_schema_definitions.yaml",
        {"forb": {"biz": "hello", "baz": "world"}},
        ".* is a required property",
    ),
    (
        "custom_schema_definitions.yaml",
        {"thing": {"biz": "hello", "baz": "world"}},
        None,
    ),
    (
        "custom_schema_external_ref.yaml",
        {"foo": asdf.tags.core.Software(name="Microsoft Windows", version="95")},
        None,
    ),
    (
        "custom_schema_external_ref.yaml",
        {"foo": False},
        "False is not valid under any of the given schemas",
    ),
]


@pytest.fixture(params=[lambda x: x, str])
def as_pathlib(request):
    """
    Fixture to test both pathlib.Path and str.
    """
    return request.param


@pytest.fixture
def schema_name(request, test_data_path, as_pathlib):
    """
    Fixture to convert the provided schema name to a path.
    """
    return as_pathlib(test_data_path / request.param)


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_write_to(tmp_path, schema_name, tree, expected_error):
    asdf_file = tmp_path / "out.asdf"

    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()
    with ctx:
        asdf.AsdfFile(tree, custom_schema=schema_name).write_to(asdf_file)


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_open(tmp_path, schema_name, tree, expected_error):
    asdf_file = tmp_path / "out.asdf"

    asdf.AsdfFile(tree).write_to(asdf_file)
    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()

    with ctx, asdf.open(asdf_file, custom_schema=schema_name):
        pass


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_validate(schema_name, tree, expected_error):

    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()

    with ctx:
        asdf.AsdfFile(tree, custom_schema=schema_name).validate()


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_dumps(schema_name, tree, expected_error):

    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()

    with ctx:
        asdf.dumps(tree, custom_schema=schema_name)


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_loads(schema_name, tree, expected_error):

    contents = asdf.dumps(tree)

    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()

    with ctx:
        asdf.loads(contents, custom_schema=schema_name)


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_dump(tmp_path, schema_name, tree, expected_error):
    asdf_file = tmp_path / "out.asdf"

    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()

    with ctx:
        asdf.dump(tree, asdf_file, custom_schema=schema_name)


@pytest.mark.parametrize(
    "schema_name, tree, expected_error",
    TEST_CASES,
    indirect=["schema_name"],
)
def test_custom_validation_load(tmp_path, schema_name, tree, expected_error):
    asdf_file = tmp_path / "out.asdf"

    asdf.AsdfFile(tree).write_to(asdf_file)
    ctx = pytest.raises(ValidationError, match=expected_error) if expected_error else nullcontext()

    with ctx:
        asdf.load(asdf_file, custom_schema=schema_name)
