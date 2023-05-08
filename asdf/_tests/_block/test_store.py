from unittest.mock import patch

import pytest

from asdf._block.key import Key
from asdf._block.store import LinearStore, Store


# a blank class for testing
class Foo:
    pass


def test_store_by_obj():
    f = Foo()
    v = 42
    s = Store()
    s.assign_object(f, v)
    assert s.lookup_by_object(f) == v


def test_get_missing_by_obj():
    f = Foo()
    s = Store()
    assert s.lookup_by_object(f) is None


def test_store_by_key():
    f = Foo()
    v = 42
    s = Store()
    k = Key(f)
    s.assign_object(k, v)
    assert s.lookup_by_object(k) == v


def test_get_by_key():
    f = Foo()
    v = 42
    s = Store()
    k = Key(f)
    s.assign_object(k, v)
    assert s.lookup_by_object(f) == v


def test_get_missing_key():
    f = Foo()
    s = Store()
    k = Key(f)
    assert s.lookup_by_object(k) is None


def test_get_missing_key_same_obj():
    f = Foo()
    v = 42
    s = Store()
    k = Key(f)
    s.assign_object(k, v)
    k2 = Key(f)
    assert s.lookup_by_object(k2) is None


def test_get_existing_default():
    f = Foo()
    v = 42
    s = Store()
    s.assign_object(f, v)
    assert s.lookup_by_object(f, 26) == v


def test_get_missing_default():
    f = Foo()
    v = 42
    s = Store()
    assert s.lookup_by_object(f, v) == v


def test_set_same_object():
    f = Foo()
    v = 42
    s = Store()
    s.assign_object(f, 26)
    s.assign_object(f, v)
    assert s.lookup_by_object(f) == v


def test_set_same_key():
    f = Foo()
    s = Store()
    k = Key(f)
    v = 42
    s.assign_object(k, 26)
    s.assign_object(k, v)
    assert s.lookup_by_object(k) == v


def test_get_memory_reused():
    f = Foo()
    s = Store()
    v = 42
    s.assign_object(f, v)
    fid = id(f)
    del f
    f2 = Foo()

    def mock_id(obj):
        if obj is f2:
            return fid
        return id(obj)

    with patch("asdf._block.store.id", mock_id):
        assert s.lookup_by_object(f2) is None


def test_set_memory_reused():
    f = Foo()
    s = Store()
    v = 42
    s.assign_object(f, v)
    fid = id(f)
    del f
    f2 = Foo()

    def mock_id(obj):
        if obj is f2:
            return fid
        return id(obj)

    with patch("asdf._block.store.id", mock_id):
        nv = 26
        s.assign_object(f2, nv)
        assert s.lookup_by_object(f2) is nv


def test_cleanup():
    f = Foo()
    s = Store()
    k = Key(f)
    s.assign_object(s, 42)
    s.assign_object(k, 26)
    del f
    s._cleanup()
    assert s.lookup_by_object(k, None) is None


def test_linear_store():
    foos = [Foo(), Foo(), Foo()]
    values = ["a", "b", "c"]
    s = LinearStore(values)
    assert len(s) == len(values)
    for f, v in zip(foos, values):
        s.assign_object(f, v)
    for f, v in zip(foos, values):
        assert s.lookup_by_object(f) == v


def test_linear_store_missing_value():
    s = LinearStore()
    with pytest.raises(ValueError, match=".*is not in list.*"):
        s.assign_object(Foo(), "missing")


def test_linear_store_lookup_unknown_object():
    s = LinearStore()
    assert s.lookup_by_object(Foo()) is None
