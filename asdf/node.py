from collections.abc import MutableMapping, MutableSequence


class AsdfNode:
    pass


class AsdfDictNode(AsdfNode, MutableMapping):
    def __init__(self, data=None):
        if data is None:
            self._data = {}
        elif isinstance(data, dict):
            self._data = data
        else:
            raise TypeError(f"Unhandled class: {data.__class__.__name__}")

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        value = self._data[key]
        if isinstance(value, dict):
            return AsdfDictNode(value)
        elif isinstance(value, list):
            return AsdfListNode(value)
        else:
            return value

    def __setitem__(self, key, value):
        if isinstance(value, AsdfNode):
            self._data[key] = value._data
        else:
            self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return str(self._data)

    def __eq__(self, other):
        if isinstance(other, AsdfNode):
            other = other._data
        return self._data == other

    def __hash__(self):
        return hash(self._data)


class AsdfListNode(AsdfNode, MutableSequence):
    def __init__(self, data=None):
        if data is None:
            self._data = []
        elif isinstance(data, list):
            self._data = data
        else:
            raise TypeError(f"Unhandled class: {data.__class__.__name__}")

    def __getitem__(self, index):
        value = self._data[index]
        if isinstance(value, dict):
            return AsdfDictNode(value)
        elif isinstance(value, list):
            return AsdfListNode(value)
        else:
            return value

    def __setitem__(self, index, value):
        if isinstance(value, AsdfNode):
            self._data[index] = value._data
        else:
            self._data[index] = value

    def __delitem__(self, index):
        del self._data[index]

    def __len__(self):
        return len(self._data)

    def insert(self, index, value):
        self._data.insert(index, value)

    def __str__(self):
        return str(self._data)

    def __eq__(self, other):
        if isinstance(other, AsdfNode):
            other = other._data

        return self._data == other

    def __hash__(self):
        return hash(self._data)
