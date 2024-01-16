"""
Objects that act like dict, list, OrderedDict but allow
lazy conversion of tagged ASDF tree nodes to custom objects.
"""
import collections
import inspect
import warnings
from types import GeneratorType

from . import tagged, yamlutil
from .exceptions import AsdfConversionWarning, AsdfLazyReferenceError
from .extension._serialization_context import BlockAccess

__all__ = ["AsdfNode", "AsdfDictNode", "AsdfListNode", "AsdfOrderedDictNode"]


def _resolve_af_ref(af_ref):
    msg = "Failed to resolve AsdfFile reference"
    if af_ref is None:
        raise AsdfLazyReferenceError(msg)
    af = af_ref()
    if af is None:
        raise AsdfLazyReferenceError(msg)
    return af


def _convert(value, af_ref):
    af = _resolve_af_ref(af_ref)
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
            # We can't quite do this for every instance (hence the
            # isgeneratorfunction check above). However it appears
            # to work for most instances (it was only failing for
            # the FractionWithInverse test which is covered by the
            # above code). The code here should only be hit if the
            # Converter.from_yaml_tree calls another function which
            # is a generator.
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
        """
        Return the tagged tree backing this node
        """
        return self.data


class AsdfListNode(AsdfNode, collections.UserList):
    """
    An `AsdfNode` subclass that acts like a ``list``.
    """

    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = []
        AsdfNode.__init__(self, data, af_ref)
        collections.UserList.__init__(self, data)

    @property
    def __class__(self):
        # this is necessary to allow this class to pass
        # an isinstance(list) check without inheriting from list.
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
            af = _resolve_af_ref(self._af_ref)
            value_id = id(value)
            if value_id in af._tagged_object_cache:
                value = af._tagged_object_cache[value_id][1]
            else:
                obj = AsdfListNode(value, self._af_ref)
                af._tagged_object_cache[value_id] = (value, obj)
                value = obj
            self[key] = value
        elif type(value) in (dict, collections.OrderedDict):
            af = _resolve_af_ref(self._af_ref)
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


class AsdfDictNode(AsdfNode, collections.UserDict):
    """
    An `AsdfNode` subclass that acts like a ``dict``.
    """

    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = {}
        AsdfNode.__init__(self, data, af_ref)
        collections.UserDict.__init__(self, data)

    @property
    def __class__(self):
        # this is necessary to allow this class to pass
        # an isinstance(dict) check without inheriting from dict.
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
            af = _resolve_af_ref(self._af_ref)
            value_id = id(value)
            if value_id in af._tagged_object_cache:
                value = af._tagged_object_cache[value_id][1]
            else:
                obj = AsdfListNode(value, self._af_ref)
                af._tagged_object_cache[value_id] = (value, obj)
                value = obj
            self[key] = value
        elif type(value) in (dict, collections.OrderedDict):
            af = _resolve_af_ref(self._af_ref)
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
    """
    An `AsdfNode` subclass that acts like a ``collections.OrderedDict``.
    """

    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = collections.OrderedDict()
        AsdfDictNode.__init__(self, data, af_ref)

    @property
    def __class__(self):
        return collections.OrderedDict

    def __copy__(self):
        return AsdfOrderedDictNode(self.data.copy(), self._af_ref)
