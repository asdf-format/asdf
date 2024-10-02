from copy import copy, deepcopy

import pytest

import asdf
from asdf.tagged import TaggedDict, TaggedList, TaggedString


def test_tagged_list_deepcopy():
    original = TaggedList([0, 1, 2, ["foo"]], "tag:nowhere.org:custom/foo-1.0.0")
    result = deepcopy(original)
    assert result == original
    assert result.data == original.data
    assert result._tag == original._tag
    original.append(4)
    assert len(result) == 4
    original[3].append("bar")
    assert len(result[3]) == 1


def test_tagged_list_copy():
    original = TaggedList([0, 1, 2, ["foo"]], "tag:nowhere.org:custom/foo-1.0.0")
    result = copy(original)
    assert result == original
    assert result.data == original.data
    assert result._tag == original._tag
    original.append(4)
    assert len(result) == 4
    original[3].append("bar")
    assert len(result[3]) == 2


def test_tagged_list_isinstance():
    value = TaggedList([0, 1, 2, ["foo"]], "tag:nowhere.org:custom/foo-1.0.0")
    assert isinstance(value, list)


def test_tagged_list_base():
    value = TaggedList([0, 1, 2, ["foo"]], "tag:nowhere.org:custom/foo-1.0.0")

    assert not (value == value.base)  # base is not a tagged list
    assert value.data == value.base  # but the data is

    assert isinstance(value.base, list)
    assert not isinstance(value.base, TaggedList)
    assert value.base.__class__ is list


def test_tagged_dict_deepcopy():
    original = TaggedDict({"a": 0, "b": 1, "c": 2, "nested": {"d": 3}}, "tag:nowhere.org:custom/foo-1.0.0")
    result = deepcopy(original)
    assert result == original
    assert result.data == original.data
    assert result._tag == original._tag
    original["e"] = 4
    assert len(result) == 4
    original["nested"]["f"] = 5
    assert len(result["nested"]) == 1


def test_tagged_dict_copy():
    original = TaggedDict({"a": 0, "b": 1, "c": 2, "nested": {"d": 3}}, "tag:nowhere.org:custom/foo-1.0.0")
    result = copy(original)
    assert result == original
    assert result.data == original.data
    assert result._tag == original._tag
    original["e"] = 4
    assert len(result) == 4
    original["nested"]["f"] = 5
    assert len(result["nested"]) == 2


def test_tagged_dict_isinstance():
    value = TaggedDict({"a": 0, "b": 1, "c": 2, "nested": {"d": 3}}, "tag:nowhere.org:custom/foo-1.0.0")
    assert isinstance(value, dict)


def test_tagged_dict_base():
    value = TaggedDict({"a": 0, "b": 1, "c": 2, "nested": {"d": 3}}, "tag:nowhere.org:custom/foo-1.0.0")

    assert not (value == value.base)  # base is not a tagged  dict
    assert value.data == value.base  # but the data is

    assert isinstance(value.base, dict)
    assert not isinstance(value.base, TaggedDict)
    assert value.base.__class__ is dict


def test_tagged_string_deepcopy():
    original = TaggedString("You're it!")
    original._tag = "tag:nowhere.org:custom/foo-1.0.0"
    result = deepcopy(original)
    assert result == original
    assert result._tag == original._tag


def test_tagged_string_copy():
    original = TaggedString("You're it!")
    original._tag = "tag:nowhere.org:custom/foo-1.0.0"
    result = copy(original)
    assert result == original
    assert result._tag == original._tag


def test_tagged_string_isinstance():
    value = TaggedString("You're it!")
    assert isinstance(value, str)


def test_tagged_string_base():
    value = TaggedString("You're it!")
    value._tag = "tag:nowhere.org:custom/foo-1.0.0"

    assert not (value == value.base)  # base is not a tagged  dict
    assert value.data == value.base  # but the data is

    assert isinstance(value.base, str)
    assert not isinstance(value.base, TaggedString)
    assert value.base.__class__ is str


ASDF_UNIT_TAG = "stsci.edu:asdf/unit/unit-1.0.0"
TAGGED_UNIT_URI = "asdf://stsci.edu/schemas/tagged_unit-1.0.0"
TAGGED_UNIT_SCHEMA = f"""
%YAML 1.1
---
$schema: http://stsci.edu/schemas/yaml-schema/draft-01
id: {TAGGED_UNIT_URI}

properties:
  unit:
    tag: {ASDF_UNIT_TAG}
    enum: [m, kg]
...
"""


def create_units():
    meter = TaggedString("m")
    meter._tag = ASDF_UNIT_TAG

    kilogram = TaggedString("kg")
    kilogram._tag = ASDF_UNIT_TAG

    return meter, kilogram


@pytest.mark.parametrize("unit", create_units())
def test_check_valid_str_enum(unit):
    """
    Regression test for issue #1254
        https://github.com/asdf-format/asdf/issues/1256

    This ensures that tagged strings can be properly validated against ``enum`` lists.
    """
    with asdf.config_context() as conf:
        conf.add_resource_mapping({TAGGED_UNIT_URI: TAGGED_UNIT_SCHEMA})
        schema = asdf.schema.load_schema(TAGGED_UNIT_URI)

        # This should not raise an exception (check_schema will raise error)
        asdf.schema.check_schema(schema)

        # This should not raise exception (validate will raise error)
        asdf.schema.validate({"unit": unit}, schema=schema)


def test_check_invalid_str_enum():
    """
    Ensure that a tagged string that is not in the ``enum`` list is properly handled.
    """
    with asdf.config_context() as conf:
        conf.add_resource_mapping({TAGGED_UNIT_URI: TAGGED_UNIT_SCHEMA})
        schema = asdf.schema.load_schema(TAGGED_UNIT_URI)

        # This should not raise an exception (check_schema will raise error)
        asdf.schema.check_schema(schema)

        unit = TaggedString("foo")
        unit._tag = ASDF_UNIT_TAG

        with pytest.raises(asdf.ValidationError, match=r"'foo' is not one of \['m', 'kg'\]"):
            asdf.schema.validate({"unit": unit}, schema=schema)
