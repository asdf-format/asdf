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


def _to_lazy_node(node, af_ref):
    """
    Convert an object to a AsdfNode subclass.
    If the object does not have a corresponding subclass
    it will be returned unchanged.
    """
    if isinstance(node, list):
        return AsdfListNode(node, af_ref)
    elif isinstance(node, collections.OrderedDict):
        return AsdfOrderedDictNode(node, af_ref)
    elif isinstance(node, dict):
        return AsdfDictNode(node, af_ref)
    return node


class AsdfNode:
    """
    The "lazy node" base class that handles object
    conversion and wrapping and contains a weak reference
    to the `asdf.AsdfFile` that triggered the creation of this
    node (when the "lazy tree" was loaded).
    """

    def __init__(self, data=None, af_ref=None):
        self._af_ref = af_ref
        self.data = data

    @property
    def tagged(self):
        """
        Return the tagged tree backing this node
        """
        return self.data

    def _convert_and_cache(self, value, key):
        """
        Convert ``value`` to either:

            - a custom object if ``value`` is `asdf.tagged.Tagged`
            - an `asdf.lazy_nodes.AsdfNode` subclass if ``value``
              is a ``list``, ``dict``, ``OrderedDict``
            - otherwise return ``value`` unmodified

        After conversion the result (``obj``) will be stored in this
        `asdf.lazy_nodes.AsdfNode` using the provided key and cached
        in the corresponding `asdf.AsdfFile` instance (so other
        references to ``value`` in the tree will return the same
        ``obj``).

        Parameters
        ----------
        value :
            The object to convert from a Tagged to custom object
            or wrap with an AsdfNode or return unmodified.

        key :
            The key under which the converted/wrapped object will
            be stored.


        Returns
        -------
        obj :
            The converted or wrapped (or the value if no conversion
            or wrapping is required).
        """
        # if the value has already been wrapped, return it
        if isinstance(value, AsdfNode):
            return value
        if not isinstance(value, tagged.Tagged) and type(value) not in _base_type_to_node_map:
            return value
        af = _resolve_af_ref(self._af_ref)
        value_id = id(value)
        # if the obj that will be returned from this value
        # is already cached, use the cached obj
        if value_id in af._tagged_object_cache:
            obj = af._tagged_object_cache[value_id][1]
            self[key] = obj
            return obj
        # for Tagged instances, convert them to their custom obj
        if isinstance(value, tagged.Tagged):
            extension_manager = af.extension_manager
            tag = value._tag
            if not extension_manager.handles_tag(tag):
                if not af._ignore_unrecognized_tag:
                    warnings.warn(
                        f"{tag} is not recognized, converting to raw Python data structure",
                        AsdfConversionWarning,
                    )
                obj = _to_lazy_node(value, self._af_ref)
            else:
                converter = extension_manager.get_converter_for_tag(tag)
                if inspect.isgeneratorfunction(converter._delegate.from_yaml_tree):
                    obj = yamlutil.tagged_tree_to_custom_tree(value, af)
                else:
                    data = _to_lazy_node(value.data, self._af_ref)
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
        else:
            # for non-tagged objects, wrap in an AsdfNode
            node_type = _base_type_to_node_map[type(value)]
            obj = node_type(value, self._af_ref)
        # cache the converted/wrapped obj with the AsdfFile so other
        # references to the same Tagged value will result in the
        # same obj
        af._tagged_object_cache[value_id] = (value, obj)
        self[key] = obj
        return obj


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
        return self._convert_and_cache(value, key)


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
        return self._convert_and_cache(super().__getitem__(key), key)


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


_base_type_to_node_map = {
    dict: AsdfDictNode,
    list: AsdfListNode,
    collections.OrderedDict: AsdfOrderedDictNode,
}
