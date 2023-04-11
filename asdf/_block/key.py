import weakref


class Key:
    _next = 0

    @classmethod
    def _next_key(cls):
        key = cls._next
        cls._next += 1
        return key

    def __init__(self, obj, key=None):
        if key is None:
            key = Key._next_key()
        self._key = key
        self._ref = weakref.ref(obj)

    def is_valid(self):
        r = self._ref()
        if r is None:
            return False
        del r
        return True

    def __hash__(self):
        return self._key

    def matches(self, obj):
        r = self._ref()
        if r is None:
            return False
        return r is obj
