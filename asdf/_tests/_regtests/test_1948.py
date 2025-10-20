import pytest

import asdf

foo_tag_uri = "asdf://somewhere.org/tags/foo-1.0.0"
bar_tag_uri = "asdf://somewhere.org/tags/bar-1.0.0"


class Foo:
    def __init__(self, data):
        self.data = data


class Bar(Foo):
    pass


class FooConverter:
    tags = [foo_tag_uri]
    types = [Foo]
    lazy = True

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.data

    def from_yaml_tree(self, node, tag, ctx):
        return Foo(node)


class BarConverter:
    tags = [bar_tag_uri]
    types = [Bar]
    lazy = True

    def to_yaml_tree(self, obj, tag, ctx):
        return obj.data

    def from_yaml_tree(self, node, tag, ctx):
        # always make reading a bar tag fail
        raise Exception("No bar")


class FooBarExtension:
    extension_uri = "asdf://somewhere.org/extensions/minimum-1.0.0"
    converters = [FooConverter(), BarConverter()]
    tags = [foo_tag_uri, bar_tag_uri]


@pytest.fixture()
def foobar_extension():
    with asdf.config_context() as cfg:
        cfg.add_extension(FooBarExtension())
        yield


def test_failed_conversion_warns(foobar_extension):
    """
    Test that warn_on_failed_conversion works as expected
    for both lazy and non-lazy trees.

    Broken out into a regtest since there is significant
    test setup.

    https://github.com/asdf-format/asdf/issues/1948
    """
    tree = {"foo": Foo({"bar": Bar({"a": 1})})}
    asdf_str = asdf.dumps(tree)
    with asdf.config_context() as cfg:
        cfg.warn_on_failed_conversion = True
        with pytest.warns(UserWarning, match="No bar"):
            read_obj = asdf.loads(asdf_str)
        foo = read_obj["foo"]
        assert isinstance(foo, Foo)
        bar = read_obj["foo"].data["bar"]
        assert isinstance(bar, asdf.tagged.TaggedDict)
        assert bar._tag == bar_tag_uri
        assert bar["a"] == 1


def test_lazy_failed_conversion_warns(foobar_extension, tmp_path):
    test_path = tmp_path / "test.asdf"
    tree = {"foo": Foo({"bar": Bar({"a": 1})})}
    asdf.dump(tree, test_path)
    with asdf.config_context() as cfg:
        cfg.warn_on_failed_conversion = True
        cfg.lazy_tree = True
        with asdf.open(test_path) as af:
            foo = af["foo"]
            assert isinstance(foo, Foo)
            with pytest.warns(UserWarning, match="No bar"):
                bar = af["foo"].data["bar"]
            assert isinstance(bar, asdf.tagged.TaggedDict)
            assert bar._tag == bar_tag_uri
            assert bar["a"] == 1
