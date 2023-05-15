import pytest

from asdf._block.callback import DataCallback
from asdf._block.store import LinearStore


def test_default_attribute():
    class Data:
        def __init__(self, value):
            self.data = value

    blks = LinearStore([Data("a"), Data("b")])
    cbs = [DataCallback(0, blks), DataCallback(1, blks)]

    assert cbs[0]() == "a"
    assert cbs[1]() == "b"


def test_attribute_access():
    class Foo:
        def __init__(self, attr, value):
            setattr(self, attr, value)

    blks = LinearStore([Foo("a", "foo"), Foo("a", "bar")])
    cb = DataCallback(0, blks)

    assert cb(_attr="a") == "foo"


def test_weakref():
    class Data:
        def __init__(self, value):
            self.data = value

    blks = LinearStore([Data("a"), Data("b")])
    cb = DataCallback(0, blks)
    del blks

    with pytest.raises(OSError, match="Attempt to read block data from missing block"):
        cb()


def test_reassign():
    class Data:
        def __init__(self, value):
            self.data = value

    blks = LinearStore([Data("a"), Data("b")])
    cb = DataCallback(0, blks)

    assert cb() == "a"

    blks2 = LinearStore([Data("c"), Data("d")])
    cb._reassign(1, blks2)

    assert cb() == "d"
