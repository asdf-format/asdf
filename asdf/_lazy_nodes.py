import collections
import inspect
import warnings
from types import GeneratorType

from . import tagged, yamlutil
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
    if inspect.isgeneratorfunction(converter._delegate.from_yaml_tree):
        obj = yamlutil.tagged_tree_to_custom_tree(value, af)
    else:
        data = value.data
        if isinstance(data, dict):
            data = AsdfDictNode(data, af_ref)
        elif isinstance(data, collections.OrderedDict):
            data = AsdfOrderedDictNode(data, af_ref)
        elif isinstance(data, list):
            data = AsdfListNode(data, af_ref)
        sctx = af._create_serialization_context(BlockAccess.READ)
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


class AsdfListNode(AsdfNode, collections.UserList):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = []
        AsdfNode.__init__(self, data, af_ref)
        collections.UserList.__init__(self, data)

    @property
    def __class__(self):
        return list

    def __copy__(self):
        return AsdfListNode(self.data.copy(), self._af_ref)

    def __eq__(self, other):
        if self is other:
            return True
        return list(self) == list(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, key):
        # key might be an int or slice
        value = super().__getitem__(key)
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


# dict is required here so TaggedDict doesn't convert this to a dict
# and so that json.dumps will work for this node TODO add test
class AsdfDictNode(AsdfNode, collections.UserDict):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = {}
        AsdfNode.__init__(self, data, af_ref)
        collections.UserDict.__init__(self, data)

    @property
    def __class__(self):
        return dict

    def __copy__(self):
        return AsdfDictNode(self.data.copy(), self._af_ref)

    def __eq__(self, other):
        if self is other:
            return True
        return dict(self) == dict(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, key):
        value = super().__getitem__(key)
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


class AsdfOrderedDictNode(AsdfDictNode):
    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = collections.OrderedDict()
        AsdfDictNode.__init__(self, data, af_ref)

    @property
    def __class__(self):
        return collections.OrderedDict

    def __copy__(self):
        return AsdfOrderedDictNode(self.data.copy(), self._af_ref)
