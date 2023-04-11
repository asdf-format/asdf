from asdf._block.key import Key
from asdf._block.store import Store


# a blank class for testing
class Foo:
    pass


def test_store_by_obj():
    f = Foo()
    v = 42
    s = Store()
    s.set(f, v)
    assert s.get(f) == v


def test_get_missing_by_obj():
    f = Foo()
    s = Store()
    assert s.get(f) is None


def test_store_by_key():
    f = Foo()
    v = 42
    s = Store()
    k = Key(f)
    s.set(k, v)
    assert s.get(k) == v


def test_get_by_key():
    f = Foo()
    v = 42
    s = Store()
    k = Key(f)
    s.set(k, v)
    assert s.get(f) == v


def test_get_missing_key():
    f = Foo()
    s = Store()
    k = Key(f)
    assert s.get(k) is None


def test_get_missing_key_same_obj():
    f = Foo()
    v = 42
    s = Store()
    k = Key(f)
    s.set(k, v)
    k2 = Key(f)
    assert s.get(k2) is None


def test_get_existing_default():
    f = Foo()
    v = 42
    s = Store()
    s.set(f, v)
    assert s.get(f, 26) == v


def test_get_missing_default():
    f = Foo()
    v = 42
    s = Store()
    assert s.get(f, v) == v


def test_set_same_object():
    f = Foo()
    v = 42
    s = Store()
    s.set(f, 26)
    s.set(f, v)
    assert s.get(f) == v


def test_set_same_key():
    f = Foo()
    s = Store()
    k = Key(f)
    v = 42
    s.set(k, 26)
    s.set(k, v)
    assert s.get(k) == v


def test_get_memory_reused():
    f = Foo()
    s = Store()
    v = 42
    s.set(f, v)
    fid = id(f)
    del f
    for _ in range(100):
        f = Foo()
        if id(f) == fid:
            break
    else:
        raise AssertionError("Failed to trigger memory reuse")
    assert s.get(f) is None


def test_set_memory_reused():
    f = Foo()
    s = Store()
    v = 42
    s.set(f, v)
    fid = id(f)
    del f
    for _ in range(100):
        f = Foo()
        if id(f) == fid:
            break
    else:
        raise AssertionError("Failed to trigger memory reuse")
    nv = 26
    s.set(f, nv)
    assert s.get(f) is nv


def test_cleanup():
    f = Foo()
    s = Store()
    k = Key(f)
    s.set(s, 42)
    s.set(k, 26)
    del f
    s._cleanup()
    assert s.get(k, None) is None
