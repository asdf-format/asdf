import collections.abc

from .key import Key


class Store:
    """
    A key-value store that uses ``asdf._block.key.Key``
    to allow use of keys that:
        - are not hashable (so any object can be used)
        - when the key is garbage collected, the value
          will be unretrievable
    """

    def __init__(self):
        # store contains 2 layers of lookup: id(obj), Key
        self._by_id = {}

    def lookup_by_object(self, obj, default=None):
        if isinstance(obj, Key):
            # if obj is a Key, look up the object
            obj_id = id(obj._ref())
            # and use the Key
            obj_key = obj
        else:
            obj_id = id(obj)
            obj_key = None

        # if id is unknown, return default
        if obj_id not in self._by_id:
            return default

        # first, lookup by id: O(1)
        by_key = self._by_id[obj_id]

        # if we have a key
        if obj_key:
            # use the key to get an existing value
            # or default if this Key is unknown
            return by_key.get(obj_key, default)

        # we have seen this id(obj) before
        # look for a matching key: O(N)
        for key, value in by_key.items():
            if key._matches_object(obj):
                return value

        # no match, return default
        return default

    def assign_object(self, obj, value):
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
                if key._matches_object(obj):
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
        keys_to_remove = [k for k in by_key if not k._is_valid()]
        for key in keys_to_remove:
            del by_key[key]
        if not len(by_key):
            del self._by_id[object_id]


class LinearStore(Store, collections.abc.Sequence):
    """
    A collections.abc.Sequence that can also be accessed
    like a Store (by using any object as a key).
    """

    def __init__(self, init=None):
        super().__init__()
        if init is None:
            init = []
        self._items = init

    def lookup_by_object(self, obj):
        index = super().lookup_by_object(obj)
        if index is None:
            return None
        return self[index]

    def assign_object(self, obj, value):
        index = self._items.index(value)
        super().assign_object(obj, index)

    def assign_object_by_index(self, obj, index):
        super().assign_object(obj, index)

    def __getitem__(self, index):
        return self._items.__getitem__(index)

    def __len__(self):
        return self._items.__len__()
