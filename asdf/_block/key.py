"""
A hashable Key class that provides a means for tracking
the lifetime of objects to associate objects with
blocks, options and other parts of an asdf file.

This Key is meant to replace uses of id(obj) which in
previous code was used to store settings (like block
array storage). The use of id was problematic as
an object might be deallocated (if it is removed from
the tree and all other references freed) and a new
object of the same type might occupy the same location
in memory and result in the same id. This could result
in options originally associated with the first object
being incorrectly assigned to the new object.

At it's core, Key, uses a weak reference to the object
which can be checked to see if the object is still
in memory.

Instances of this class will be provided to extension
code (see ``SerializationContext.generate_block_key``)
as Converters will need to resupply these keys
on rewrites (updates) to allow asdf to reassociate
objects and blocks. To discourage modifications
of these Key instances all methods and attributes
are private.
"""

import weakref


class Key:
    _next = 0

    @classmethod
    def _next_key(cls):
        key = cls._next
        cls._next += 1
        return key

    def __init__(self, obj=None, _key=None):
        if _key is None:
            _key = Key._next_key()
        self._key = _key
        self._ref = None
        if obj is not None:
            self._assign_object(obj)

    def _is_valid(self):
        if self._ref is None:
            return False
        r = self._ref()
        if r is None:
            return False
        return True

    def __hash__(self):
        return self._key

    def _assign_object(self, obj):
        self._ref = weakref.ref(obj)

    def _matches_object(self, obj):
        if self._ref is None:
            return False
        r = self._ref()
        if r is None:
            return False
        return r is obj

    def __eq__(self, other):
        if not isinstance(other, Key):
            return NotImplemented
        if self._key != other._key:
            return False
        if not self._is_valid():
            return False
        return other._matches_object(self._ref())

    def __copy__(self):
        obj = self._ref if self._ref is None else self._ref()
        return type(self)(obj, self._key)
