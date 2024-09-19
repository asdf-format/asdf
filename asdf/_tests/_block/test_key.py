import copy
import gc

from asdf._block.key import Key


# a blank class for testing
class Foo:
    pass


def test_unique_per_object():
    seen = set()
    for _i in range(10):
        bk = Key(Foo())
        assert bk not in seen
        seen.add(bk)


def test_unique_same_object():
    seen = set()
    f = Foo()
    for _i in range(10):
        bk = Key(f)
        assert bk not in seen
        seen.add(bk)


def test_matches_obj():
    f = Foo()
    bk = Key(f)
    assert bk._matches_object(f)


def test_undefined_no_match():
    bk = Key()
    assert not bk._matches_object(Foo())


def test_is_valid():
    f = Foo()
    bk = Key(f)
    assert bk._is_valid()
    del f
    gc.collect(2)
    assert not bk._is_valid()


def test_same_class():
    f = Foo()
    bk = Key(f)
    del f
    gc.collect(2)
    f2 = Foo()
    assert not bk._is_valid()
    assert not bk._matches_object(f2)


def test_undefined():
    k = Key()
    assert not k._is_valid()


def test_equal():
    key_value = 42
    f = Foo()
    k1 = Key(f, key_value)
    k2 = Key(f, key_value)
    assert k1 == k2


def test_key_mismatch_not_equal():
    f = Foo()
    k1 = Key(f)
    k2 = Key(f)
    assert k1 != k2


def test_obj_not_equal():
    f = Foo()
    k = Key(f)
    assert k != f


def test_undefined_not_equal():
    key_value = 42
    k1 = Key(_key=key_value)
    k2 = Key(_key=key_value)
    assert k1 != k2


def test_deleted_object_not_equal():
    key_value = 42
    f = Foo()
    k1 = Key(f, key_value)
    k2 = Key(f, key_value)
    del f
    gc.collect(2)
    assert k1 != k2


def test_copy():
    f = Foo()
    k1 = Key(f)
    k2 = copy.copy(k1)
    assert k1 == k2


def test_copy_undefined_not_equal():
    k1 = Key()
    k2 = copy.copy(k1)
    assert k1 != k2


def test_copy_deleted_object_not_equal():
    f = Foo()
    k1 = Key(f)
    k2 = copy.copy(k1)
    del f
    gc.collect(2)
    assert k1 != k2
