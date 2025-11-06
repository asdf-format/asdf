"""
Test that warn_on_failed_conversion works as expected for:
    - lazy and non-lazy trees
    - nested objects
    - generator producing (yielding) converters

Broken out into a regtest since there is significant
test setup.

https://github.com/asdf-format/asdf/issues/1948
"""

import pytest

import asdf

test_dict_tag_uri = "asdf://somewhere.org/tags/test_dict-1.0.0"
failing_dict_tag_uri = "asdf://somewhere.org/tags/failing_dict-1.0.0"
failing_yield_dict_tag_uri = "asdf://somewhere.org/tags/failing_yield_dict-1.0.0"


class MyDict:
    def __init__(self, data):
        self.data = data


class FailingDict(MyDict):
    pass


class FailingYieldDict(MyDict):
    pass


class MyDictConverter:
    tags = [test_dict_tag_uri]
    types = [MyDict]
    lazy = True

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.data

    def from_yaml_tree(self, node, tag, ctx):
        return MyDict(node)


class FailingDictConverter:
    tags = [failing_dict_tag_uri]
    types = [FailingDict]
    lazy = True

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.data

    def from_yaml_tree(self, node, tag, ctx):
        # always make reading a failing_dict tag fail
        raise Exception("FailingDict failed")


class FailingYieldDictConverter:
    tags = [failing_yield_dict_tag_uri]
    types = [FailingYieldDict]
    lazy = True

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.data

    def from_yaml_tree(self, node, tag, ctx):
        raise Exception("FailingYieldDict failed")
        yield {}


class TestExtension:
    extension_uri = "asdf://somewhere.org/extensions/minimum-1.0.0"
    converters = [MyDictConverter(), FailingDictConverter(), FailingYieldDictConverter()]
    tags = [test_dict_tag_uri, failing_dict_tag_uri, failing_yield_dict_tag_uri]


@pytest.fixture()
def enable_test_extension():
    with asdf.config_context() as cfg:
        cfg.add_extension(TestExtension())
        yield


def test_failed_conversion_warns(enable_test_extension):
    tree = {
        "test_dict": MyDict({"failing_dict": FailingDict({"a": 1})}),
        "failing_yield_dict": FailingYieldDict({"b": 2}),
    }
    asdf_str = asdf.dumps(tree)
    with asdf.config_context() as cfg:
        cfg.warn_on_failed_conversion = True
        with (
            pytest.warns(asdf.exceptions.AsdfConversionWarning, match="FailingDict failed"),
            pytest.warns(asdf.exceptions.AsdfConversionWarning, match="FailingYieldDict failed"),
        ):
            read_obj = asdf.loads(asdf_str)
        test_dict = read_obj["test_dict"]
        assert isinstance(test_dict, MyDict)
        failing_dict = read_obj["test_dict"].data["failing_dict"]
        assert isinstance(failing_dict, asdf.tagged.TaggedDict)
        assert failing_dict._tag == failing_dict_tag_uri
        assert failing_dict["a"] == 1
        failing_yield_dict = read_obj["failing_yield_dict"]
        assert isinstance(failing_yield_dict, asdf.tagged.TaggedDict)
        assert failing_yield_dict._tag == failing_yield_dict_tag_uri
        assert failing_yield_dict["b"] == 2


def test_lazy_failed_conversion_warns(enable_test_extension, tmp_path):
    test_path = tmp_path / "test.asdf"
    tree = {
        "test_dict": MyDict({"failing_dict": FailingDict({"a": 1})}),
        "failing_yield_dict": FailingYieldDict({"b": 2}),
    }
    asdf.dump(tree, test_path)
    with asdf.config_context() as cfg:
        cfg.warn_on_failed_conversion = True
        cfg.lazy_tree = True
        with asdf.open(test_path) as af:
            test_dict = af["test_dict"]
            assert isinstance(test_dict, MyDict)
            with pytest.warns(asdf.exceptions.AsdfConversionWarning, match="FailingDict failed"):
                failing_dict = af["test_dict"].data["failing_dict"]
            with pytest.warns(asdf.exceptions.AsdfConversionWarning, match="FailingYieldDict failed"):
                failing_yield_dict = af["failing_yield_dict"]
            assert isinstance(failing_dict, asdf.tagged.TaggedDict)
            assert failing_dict._tag == failing_dict_tag_uri
            assert failing_dict["a"] == 1
            assert isinstance(failing_yield_dict, asdf.tagged.TaggedDict)
            assert failing_yield_dict._tag == failing_yield_dict_tag_uri
            assert failing_yield_dict["b"] == 2
