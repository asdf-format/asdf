"""
Objects that act like dict, list, OrderedDict but allow
lazy conversion of tagged ASDF tree nodes to custom objects.
"""

import collections
import inspect
import warnings
import weakref

from . import tagged, treeutil, yamlutil
from .exceptions import AsdfConversionWarning, AsdfLazyReferenceError
from .extension._serialization_context import BlockAccess

__all__ = ["AsdfDictNode", "AsdfListNode", "AsdfOrderedDictNode"]


class _TaggedObjectCacheItem:
    """
    A tagged node and a (weakref) to the converted custom object
    """

    def __init__(self, tagged_node, custom_object):
        self.tagged_node = tagged_node
        try:
            self._custom_object_ref = weakref.ref(custom_object)
        except TypeError:
            # if a weakref is not possible, store the object
            self._custom_object_ref = lambda obj=custom_object: obj

    @property
    def custom_object(self):
        return self._custom_object_ref()


class _TaggedObjectCache:
    """
    A cache of tagged nodes and their corresponding custom objects.

    This is critical for trees that contain references/pointers to the
    same object at multiple locations in the tree.

    Only weakrefs are key to the custom objects to allow large items
    deleted from the tree to be garbage collected. This means that an
    item added to the cache may later fail to retrieve (if the weakref-ed
    custom object was deleted).
    """

    def __init__(self):
        # start with a clear cache
        self.clear()

    def clear(self):
        self._cache = {}

    def retrieve(self, tagged_node):
        """
        Check the cache for a previously converted object.

        Parameters
        ----------
        tagged_node : Tagged
            The tagged representation of the custom object

        Returns
        -------
        custom_object : None or the converted object
            The custom object previously converted from the tagged_node or
            ``None`` if the object hasn't been converted (or was previously
            deleted from the tree).
        """
        key = id(tagged_node)
        if key not in self._cache:
            return None
        item = self._cache[key]
        custom_object = item.custom_object
        if custom_object is None:
            del self._cache[key]
        return custom_object

    def store(self, tagged_node, custom_object):
        """
        Store a converted custom object in the cache.

        Parameters
        ----------
        tagged_node : Tagged
            The tagged representation of the custom object

        custom_object : converted object
            The custom object (a weakref to this object will be kept in the cache).
        """
        self._cache[id(tagged_node)] = _TaggedObjectCacheItem(tagged_node, custom_object)


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
    Convert an object to a _AsdfNode subclass.
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


class _AsdfNode:
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

    def __deepcopy__(self, memo):
        return treeutil.walk_and_modify(self, lambda n: n)

    def _convert_and_cache(self, value, key):
        """
        Convert ``value`` to either:

            - a custom object if ``value`` is `asdf.tagged.Tagged`
            - an ``asdf.lazy_nodes.AsdfListNode` if ``value`` is
              a ``list``
            - an ``asdf.lazy_nodes.AsdfDictNode` if ``value`` is
              a ``dict``
            - an ``asdf.lazy_nodes.AsdfOrderedDictNode` if ``value`` is
              a ``OrderedDict``
            - otherwise return ``value`` unmodified

        After conversion the result (``obj``) will be stored in this
        `asdf.lazy_nodes._AsdfNode` using the provided key and cached
        in the corresponding `asdf.AsdfFile` instance (so other
        references to ``value`` in the tree will return the same
        ``obj``).

        Parameters
        ----------
        value :
            The object to convert from a Tagged to custom object
            or wrap with an _AsdfNode or return unmodified.

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
        if isinstance(value, _AsdfNode):
            return value
        if not isinstance(value, tagged.Tagged) and type(value) not in _base_type_to_node_map:
            return value
        af = _resolve_af_ref(self._af_ref)
        # if the obj that will be returned from this value
        # is already cached, use the cached obj
        if (obj := af._tagged_object_cache.retrieve(value)) is not None:
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
                if not getattr(converter, "lazy", False) or inspect.isgeneratorfunction(
                    converter._delegate.from_yaml_tree
                ):
                    obj = yamlutil.tagged_tree_to_custom_tree(value, af)
                else:
                    data = _to_lazy_node(value.data, self._af_ref)
                    sctx = af._create_serialization_context(BlockAccess.READ)
                    obj = converter.from_yaml_tree(data, tag, sctx)
                    sctx.assign_object(obj)
                    sctx.assign_blocks()
                    sctx._mark_extension_used(converter.extension)
        else:
            # for non-tagged objects, wrap in an _AsdfNode
            node_type = _base_type_to_node_map[type(value)]
            obj = node_type(value, self._af_ref)
        # cache the converted/wrapped obj with the AsdfFile so other
        # references to the same Tagged value will result in the
        # same obj
        af._tagged_object_cache.store(value, obj)
        self[key] = obj
        return obj


class AsdfListNode(_AsdfNode, collections.UserList):
    """
    An class that acts like a ``list``. The items in this ``list``
    will start out as tagged nodes which will only be converted to
    custom objects the first time they are indexed (the custom object
    will then be cached for later reuse).

    If sliced, this will return a new instance of `AsdfListNode` for
    the sliced portion of the list.
    """

    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = []
        _AsdfNode.__init__(self, data, af_ref)
        collections.UserList.__init__(self, data)

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


class AsdfDictNode(_AsdfNode, collections.UserDict):
    """
    An class that acts like a ``dict``. The values for this
    ``dict`` will start out as tagged nodes which will only
    be converted to custom objects the first time the corresponding
    key is used (the custom object will then be cached for later
    reuse).
    """

    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = {}
        _AsdfNode.__init__(self, data, af_ref)
        collections.UserDict.__init__(self, data)

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


class AsdfOrderedDictNode(AsdfDictNode, collections.OrderedDict):
    """
    An class that acts like a ``collections.OrderedDict``. The values
    for this ``OrderedDict`` will start out as tagged nodes which will only
    be converted to custom objects the first time the corresponding
    key is used (the custom object will then be cached for later
    reuse).
    """

    def __init__(self, data=None, af_ref=None):
        if data is None:
            data = collections.OrderedDict()
        AsdfDictNode.__init__(self, data, af_ref)

    def __copy__(self):
        return AsdfOrderedDictNode(self.data.copy(), self._af_ref)


_base_type_to_node_map = {
    dict: AsdfDictNode,
    list: AsdfListNode,
    collections.OrderedDict: AsdfOrderedDictNode,
}
