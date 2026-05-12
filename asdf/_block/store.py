from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .key import Key

if TYPE_CHECKING:
    from collections.abc import Iterator


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
        self._by_id: dict[int, dict[Key, Any]] = {}

    def lookup_by_object(self, obj: Any, default: Any | None = None) -> Any | None:
        if isinstance(obj, Key):
            # if obj is a Key, look up the object
            obj_id = id(obj._ref())  # pyrefly: ignore [not-callable]
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

    def assign_object(self, obj: Any, value: Any) -> None:
        if isinstance(obj, Key):
            if not obj._is_valid():
                msg = "Invalid key used for assign_object"
                raise ValueError(msg)
            obj_id = id(obj._ref())  # pyrefly: ignore [not-callable]
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

        # if no match was found, add using the key
        self._by_id[obj_id][obj_key] = value

    def keys_for_value(self, value: Any) -> Iterator[Key]:
        for oid, by_key in self._by_id.items():
            for key, stored_value in by_key.items():
                if stored_value == value and key._is_valid():
                    yield key

    def _cleanup(self, object_id: int | None = None) -> None:
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
