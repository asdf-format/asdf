import pytest

from asdf._helpers import _IsSet, is_set


class Tracked(_IsSet):
    bar = None

    def __init__(self):
        # Intentionally not calling `super().__init__()` here to make sure `_IsSet` still works
        self._value = 1
        self.baz = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


def test_is_set():
    x = Tracked()
    y = Tracked()

    def is_set_iter(obj):
        yield from (is_set(obj, attr) for attr in ["value", "bar", "baz"])

    assert not any(is_set_iter(x))

    x.value = 2
    x.bar = 3
    x.baz = "foo"

    assert all(is_set_iter(x))
    assert not any(is_set_iter(y))


def test_is_set_attr_error():
    """Test that trying to access a non-existent property via `is_set` raises an `AttributeError`."""
    x = Tracked()
    with pytest.raises(AttributeError):
        is_set(x, "foo")


def test_is_set_type_error():
    with pytest.raises(TypeError):
        # pyrefly: ignore [bad-argument-type]
        is_set(object(), "foo")
