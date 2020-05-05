from copy import deepcopy, copy

from asdf.tagged import TaggedList, TaggedDict, TaggedString


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
