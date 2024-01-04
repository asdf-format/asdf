import collections

from . import tagged
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
    converter = extension_manager.get_converter_for_tag(tag)
    data = value.data
    if isinstance(data, dict):
        data = AsdfDictNode(data, af_ref)
    elif isinstance(data, list):
        data = AsdfListNode(data, af_ref)
    obj = converter.from_yaml_tree(data, tag, sctx)
    # TODO generator?
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


class AsdfListNode(AsdfNode, collections.UserList, list):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = []
        super().__init__(data, af_ref)

    def __getitem__(self, key):
        # key might be an int or slice
        value = super().__getitem__(key)
        if isinstance(key, slice):
            return AsdfListNode(value)
        if isinstance(value, tagged.Tagged):
            value = _convert(value, self._af_ref)
            self[key] = value
        elif isinstance(value, AsdfNode):
            pass
        elif isinstance(value, list):
            value = AsdfListNode(value, self._af_ref)
            self[key] = value
        elif isinstance(value, dict):
            value = AsdfDictNode(value, self._af_ref)
            self[key] = value
        return value


# dict is required here so TaggedDict doesn't convert this to a dict
class AsdfDictNode(AsdfNode, collections.UserDict, dict):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = {}
        super().__init__(data, af_ref)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if isinstance(value, tagged.Tagged):
            value = _convert(value, self._af_ref)
            self[key] = value
        elif isinstance(value, AsdfNode):
            pass
        elif isinstance(value, list):
            value = AsdfListNode(value, self._af_ref)
            self[key] = value
        elif isinstance(value, dict):
            value = AsdfDictNode(value, self._af_ref)
            self[key] = value
        return value
