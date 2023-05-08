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
    assert bk.matches(f)


def test_is_valid():
    f = Foo()
    bk = Key(f)
    assert bk.is_valid()
    del f
    assert not bk.is_valid()


def test_same_class():
    f = Foo()
    bk = Key(f)
    del f
    f2 = Foo()
    assert not bk.is_valid()
    assert not bk.matches(f2)
