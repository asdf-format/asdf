from .key import Key


class Store:
    def __init__(self):
        # store contains 2 layers of lookup: id(obj), Key
        self._by_id = {}

    def get(self, obj, default=None):
        if isinstance(obj, Key):
            obj_id = id(obj._ref())
            obj_key = obj
        else:
            obj_id = id(obj)
            obj_key = None

        # if id is unknown, return default
        if obj_id not in self._by_id:
            return default

        # first, lookup by id: O(1)
        by_key = self._by_id[obj_id]

        # if we have a key, use it
        if obj_key:
            return by_key.get(obj_key, default)

        # look for a matching key: O(N)
        for key, value in by_key.items():
            if key.matches(obj):
                return value

        # no match, return default
        return default

    def set(self, obj, value):
        if isinstance(obj, Key):
            obj_id = id(obj._ref())
            obj_key = obj
        else:
            obj_id = id(obj)
            obj_key = None

        # if the id is unknown, just set it
        if obj_id not in self._by_id:
            if obj_key is None:
                obj_key = Key(obj)
            self._by_id[obj_id] = {obj_key: value}
            return

        # if id is known
        by_key = self._by_id[obj_id]

        # look for a matching matching key
        if obj_key is None:
            for key in by_key:
                if key.matches(obj):
                    by_key[key] = value
                    return
            # we didn't find a matching key, so make one
            obj_key = Key(obj)
        else:
            # we already have a key, check if it's already in the store
            if obj_key in by_key:
                by_key[obj_key] = value
                return

        # if no match was found, add using the key
        self._by_id[obj_id][obj_key] = value

    def _cleanup(self, object_id=None):
        if object_id is None:
            for oid in set(self._by_id):
                self._cleanup(oid)
            return
        by_key = self._by_id[object_id]
        keys_to_remove = [k for k in by_key if not k.is_valid()]
        for key in keys_to_remove:
            del by_key[key]
        if not len(by_key):
            del self._by_id[object_id]
