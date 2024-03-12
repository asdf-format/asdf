import collections
import collections.abc
import copy
import warnings
from types import GeneratorType

from . import tagged
from .exceptions import AsdfConversionWarning
from .extension._serialization_context import BlockAccess


def _convert(value, af_ref):
    if af_ref is None:
        raise Exception("no ASDF for you!")
    af = af_ref()
    if af is None:
        raise Exception("no ASDF for you!")
    value_id = id(value)
    if value_id in af._tagged_object_cache:
        return af._tagged_object_cache[value_id][1]
    extension_manager = af.extension_manager
    sctx = af._create_serialization_context(BlockAccess.READ)
    tag = value._tag
    if not extension_manager.handles_tag(tag):
        if not af._ignore_unrecognized_tag:
            warnings.warn(
                f"{tag} is not recognized, converting to raw Python data structure",
                AsdfConversionWarning,
            )
        if isinstance(value, list):
            obj = AsdfListNode(value, af_ref)
        elif isinstance(value, collections.OrderedDict):
            obj = AsdfOrderedDictNode(value, af_ref)
        elif isinstance(value, dict):
            obj = AsdfDictNode(value, af_ref)
        else:
            obj = value
        af._tagged_object_cache[value_id] = (value, obj)
        return obj
    converter = extension_manager.get_converter_for_tag(tag)
    data = value.data
    if isinstance(data, dict):
        data = AsdfDictNode(data, af_ref)
    elif isinstance(data, collections.OrderedDict):
        data = AsdfOrderedDictNode(data, af_ref)
    elif isinstance(data, list):
        data = AsdfListNode(data, af_ref)
    obj = converter.from_yaml_tree(data, tag, sctx)
    if isinstance(obj, GeneratorType):
        # TODO we can't quite do this for every instance
        generator = obj
        obj = next(generator)
        for _ in generator:
            pass
    sctx.assign_object(obj)
    sctx.assign_blocks()
    sctx._mark_extension_used(converter.extension)
    af._tagged_object_cache[value_id] = (value, obj)
    return obj


class AsdfNode:
    def __init__(self, data=None, af_ref=None):
        self._af_ref = af_ref
        self.data = data

    @property
    def tagged(self):
        return self.data

    def copy(self):
        return self.__class__(copy.copy(self.data), self._af_ref)

    def __asdf_traverse__(self):
        return self.data


class AsdfListNode(AsdfNode, collections.abc.MutableSequence):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = []
        AsdfNode.__init__(self, data, af_ref)

    def __setitem__(self, index, value):
        self.data.__setitem__(index, value)

    def __delitem__(self, index):
        self.data.__delitem__(index)

    def __len__(self):
        return self.data.__len__()

    def insert(self, index, value):
        self.data.insert(index, value)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, collections.abc.Sequence):
            return False
        return list(self) == list(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, key):
        # key might be an int or slice
        value = self.data.__getitem__(key)
        if isinstance(key, slice):
            return AsdfListNode(value, self._af_ref)
        if isinstance(value, tagged.Tagged):
            value = _convert(value, self._af_ref)
            self[key] = value
        elif isinstance(value, AsdfNode):
            pass
        elif type(value) == list:  # noqa: E721
            if not self._af_ref:
                raise Exception("no ASDF for you!")
            af = self._af_ref()
            if not af:
                raise Exception("no ASDF for you!")
            value_id = id(value)
            if value_id in af._tagged_object_cache:
                value = af._tagged_object_cache[value_id][1]
            else:
                obj = AsdfListNode(value, self._af_ref)
                af._tagged_object_cache[value_id] = (value, obj)
                value = obj
            self[key] = value
        elif type(value) in (dict, collections.OrderedDict):
            if not self._af_ref:
                raise Exception("no ASDF for you!")
            af = self._af_ref()
            if not af:
                raise Exception("no ASDF for you!")
            value_id = id(value)
            if value_id in af._tagged_object_cache:
                value = af._tagged_object_cache[value_id][1]
            else:
                if type(value) == collections.OrderedDict:
                    obj = AsdfOrderedDictNode(value, self._af_ref)
                else:
                    obj = AsdfDictNode(value, self._af_ref)
                af._tagged_object_cache[value_id] = (value, obj)
                value = obj
            self[key] = value
        return value


class AsdfDictNode(AsdfNode, collections.abc.MutableMapping):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = {}
        AsdfNode.__init__(self, data, af_ref)

    def __setitem__(self, index, value):
        self.data.__setitem__(index, value)

    def __delitem__(self, index):
        self.data.__delitem__(index)

    def __len__(self):
        return self.data.__len__()

    def __iter__(self):
        return self.data.__iter__()

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, collections.abc.Mapping):
            return False
        return dict(self) == dict(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, key):
        value = self.data.__getitem__(key)
        if isinstance(value, tagged.Tagged):
            value = _convert(value, self._af_ref)
            self[key] = value
        elif isinstance(value, AsdfNode):
            pass
        elif type(value) == list:  # noqa: E721
            if not self._af_ref:
                raise Exception("no ASDF for you!")
            af = self._af_ref()
            if not af:
                raise Exception("no ASDF for you!")
            value_id = id(value)
            if value_id in af._tagged_object_cache:
                value = af._tagged_object_cache[value_id][1]
            else:
                obj = AsdfListNode(value, self._af_ref)
                af._tagged_object_cache[value_id] = (value, obj)
                value = obj
            self[key] = value
        elif type(value) in (dict, collections.OrderedDict):
            if not self._af_ref:
                raise Exception("no ASDF for you!")
            af = self._af_ref()
            if not af:
                raise Exception("no ASDF for you!")
            value_id = id(value)
            if value_id in af._tagged_object_cache:
                value = af._tagged_object_cache[value_id][1]
            else:
                if type(value) == collections.OrderedDict:
                    obj = AsdfOrderedDictNode(value, self._af_ref)
                else:
                    obj = AsdfDictNode(value, self._af_ref)
                af._tagged_object_cache[value_id] = (value, obj)
                value = obj
            self[key] = value
        return value


class AsdfOrderedDictNode(AsdfDictNode, collections.OrderedDict):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = collections.OrderedDict()
        AsdfDictNode.__init__(self, data, af_ref)
