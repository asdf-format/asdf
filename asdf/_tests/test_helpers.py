import pytest

from asdf import _types as types
from asdf._tests._helpers import assert_roundtrip_tree
from asdf.exceptions import AsdfConversionWarning, AsdfDeprecationWarning, AsdfWarning


def test_conversion_error(tmp_path):
    with pytest.warns(AsdfDeprecationWarning, match=".*subclasses the deprecated CustomType.*"):

        class FooType(types.CustomType):
            name = "foo"

            def __init__(self, a, b):
                self.a = a
                self.b = b

            @classmethod
            def from_tree(cls, tree, ctx):
                msg = "This allows us to test the failure"
                raise TypeError(msg)

            @classmethod
            def to_tree(cls, node, ctx):
                return {"a": node.a, "b": node.b}

            def __eq__(self, other):
                return self.a == other.a and self.b == other.b

    class FooExtension:
        @property
        def types(self):
            return [FooType]

        @property
        def tag_mapping(self):
            return []

        @property
        def url_mapping(self):
            return []

    foo = FooType(10, "hello")
    tree = {"foo": foo}

    with pytest.raises(
        AsdfConversionWarning,
        match=r"Failed to convert .* to custom type .* Using raw Python data structure instead",
    ), pytest.warns(AsdfWarning, match=r"Unable to locate schema file"):
        assert_roundtrip_tree(tree, tmp_path, extensions=FooExtension())
