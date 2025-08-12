import warnings
from collections import OrderedDict
from types import GeneratorType

import numpy as np
import yaml

from . import config, schema, tagged, treeutil, util
from .constants import STSCI_SCHEMA_TAG_BASE, YAML_TAG_PREFIX
from .exceptions import AsdfConversionWarning, AsdfSerializationError
from .extension._serialization_context import BlockAccess
from .tags.core import AsdfObject
from .versioning import _YAML_VERSION, _yaml_base_loader

__all__ = ["custom_tree_to_tagged_tree", "tagged_tree_to_custom_tree"]


_yaml_base_dumper = yaml.CSafeDumper if getattr(yaml, "__with_libyaml__", None) else yaml.SafeDumper


YAML_OMAP_TAG = YAML_TAG_PREFIX + "omap"


# ----------------------------------------------------------------------
# Custom loader/dumpers


class AsdfDumper(_yaml_base_dumper):
    """
    A specialized YAML dumper that understands "tagged basic Python
    data types" as implemented in the `tagged` module.
    """

    def __init__(self, *args, **kwargs):
        kwargs["default_flow_style"] = None
        super().__init__(*args, **kwargs)

    def represent_data(self, data):
        node = super().represent_data(data)

        tag_name = getattr(data, "_tag", None)
        if tag_name is not None:
            node.tag = tag_name

        return node


_flow_style_map = {"flow": True, "block": False}


def represent_sequence(dumper, sequence):
    flow_style = _flow_style_map.get(sequence.flow_style, None)
    sequence = sequence.data
    return super(AsdfDumper, dumper).represent_sequence(None, sequence, flow_style)


def represent_mapping(dumper, mapping):
    flow_style = _flow_style_map.get(mapping.flow_style, None)
    node = super(AsdfDumper, dumper).represent_mapping(None, mapping.data, flow_style)

    if mapping.property_order:
        values = node.value
        new_mapping = {}
        for key, val in values:
            new_mapping[key.value] = (key, val)

        new_values = []
        for key in mapping.property_order:
            if key in mapping:
                new_values.append(new_mapping[key])

        property_order = set(mapping.property_order)
        for key, val in values:
            if key.value not in property_order:
                new_values.append((key, val))

        node.value = new_values

    return node


_style_map = {"inline": '"', "folded": ">", "literal": "|"}


def represent_scalar(dumper, value):
    style = _style_map.get(value.style, None)
    return super(AsdfDumper, dumper).represent_scalar(None, value.data, style)


def represent_ordered_mapping(dumper, tag, data):
    # TODO: Again, adjust for preferred flow style, and other stylistic details
    # NOTE: For block style this uses the compact omap notation, but for flow style
    # it does not.

    # TODO: Need to see if I can figure out a mechanism so that classes that
    # use this representer can specify which values should use flow style
    values = []
    node = yaml.SequenceNode(tag, values, flow_style=dumper.default_flow_style)
    if dumper.alias_key is not None:
        dumper.represented_objects[dumper.alias_key] = node
    for key, value in data.items():
        key_item = dumper.represent_data(key)
        value_item = dumper.represent_data(value)
        node_item = yaml.MappingNode(YAML_OMAP_TAG, [(key_item, value_item)], flow_style=False)
        values.append(node_item)
    return node


def represent_ordereddict(dumper, data):
    return represent_ordered_mapping(dumper, YAML_OMAP_TAG, data)


AsdfDumper.add_representer(tagged.TaggedList, represent_sequence)
AsdfDumper.add_representer(tagged.TaggedDict, represent_mapping)
AsdfDumper.add_representer(tagged.TaggedString, represent_scalar)
AsdfDumper.add_representer(OrderedDict, represent_ordereddict)

# ----------------------------------------------------------------------
# Handle numpy scalars


for scalar_type in util._iter_subclasses(np.floating):
    AsdfDumper.add_representer(scalar_type, lambda dumper, data: dumper.represent_float(float(data)))

for scalar_type in util._iter_subclasses(np.integer):
    AsdfDumper.add_representer(scalar_type, lambda dumper, data: dumper.represent_int(int(data)))


def represent_numpy_str(dumper, data):
    # The CSafeDumper implementation will raise an error if it
    # doesn't recognize data as a string.  The Python SafeDumper
    # has no problem with np.str_.
    return dumper.represent_str(str(data))


AsdfDumper.add_representer(np.str_, represent_numpy_str)
AsdfDumper.add_representer(np.bytes_, AsdfDumper.represent_binary)


class _IgnoreCustomTagsLoader(_yaml_base_loader):
    """
    A specialized YAML loader that ignores tags unknown to the
    base (safe) loader. This is used by `asdf.util.load_yaml`
    to read the ASDF tree as "basic" objects, ignoring the
    custom tags.
    """

    def construct_undefined(self, node):
        if isinstance(node, yaml.MappingNode):
            return self.construct_yaml_map(node)
        elif isinstance(node, yaml.SequenceNode):
            return self.construct_yaml_seq(node)
        elif isinstance(node, yaml.ScalarNode):
            return self.construct_scalar(node)
        return super().construct_undefined(node)


# pyyaml will invoke the constructor associated with None when a node's
# tag is not explicitly handled by another constructor.
_IgnoreCustomTagsLoader.add_constructor(None, _IgnoreCustomTagsLoader.construct_undefined)


class AsdfLoader(_yaml_base_loader):
    """
    A specialized YAML loader that can construct "tagged basic Python
    data types" as implemented in the `tagged` module.
    """

    def construct_undefined(self, node):
        if isinstance(node, yaml.MappingNode):
            return self._construct_tagged_mapping(node)

        if isinstance(node, yaml.SequenceNode):
            return self._construct_tagged_sequence(node)

        if isinstance(node, yaml.ScalarNode):
            return self._construct_tagged_scalar(node)

        return super().construct_undefined(node)

    def _construct_tagged_mapping(self, node):
        data = tagged.tag_object(node.tag, {})
        yield data
        data.update(self.construct_mapping(node))

    def _construct_tagged_sequence(self, node):
        data = tagged.tag_object(node.tag, [])
        yield data
        data.extend(self.construct_sequence(node))

    def _construct_tagged_scalar(self, node):
        return tagged.tag_object(node.tag, self.construct_scalar(node))

    # Custom omap deserializer that builds an OrderedDict instead
    # of a list of tuples.  Code is mostly identical to pyyaml's SafeConstructor.
    def construct_yaml_omap(self, node):
        omap = OrderedDict()
        yield omap
        if not isinstance(node, yaml.SequenceNode):
            msg = "while constructing an ordered map"
            raise yaml.constructor.ConstructorError(
                msg,
                node.start_mark,
                f"expected a sequence, but found {node.id}",
                node.start_mark,
            )
        for subnode in node.value:
            if not isinstance(subnode, yaml.MappingNode):
                msg = "while constructing an ordered map"
                raise yaml.constructor.ConstructorError(
                    msg,
                    node.start_mark,
                    f"expected a mapping of length 1, but found {subnode.id}",
                    subnode.start_mark,
                )
            if len(subnode.value) != 1:
                msg = "while constructing an ordered map"
                raise yaml.constructor.ConstructorError(
                    msg,
                    node.start_mark,
                    f"expected a single mapping item, but found {len(subnode.value)} items",
                    subnode.start_mark,
                )
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap[key] = value


# pyyaml will invoke the constructor associated with None when a node's
# tag is not explicitly handled by another constructor.
AsdfLoader.add_constructor(None, AsdfLoader.construct_undefined)
AsdfLoader.add_constructor(YAML_TAG_PREFIX + "omap", AsdfLoader.construct_yaml_omap)


def custom_tree_to_tagged_tree(tree, ctx, _serialization_context=None):
    """
    Convert a tree, possibly containing custom data types that aren't
    directly representable in YAML, to a tree of basic data types,
    annotated with tags.
    """
    if _serialization_context is None:
        _serialization_context = ctx._create_serialization_context(BlockAccess.WRITE)

    extension_manager = _serialization_context.extension_manager

    def _convert_obj(obj, converter):
        tag = converter.select_tag(obj, _serialization_context)
        # if select_tag returns None, converter.to_yaml_tree should return a new
        # object which will be handled by a different converter
        converters_used = set()
        while tag is None:
            converters_used.add(converter)
            obj = converter.to_yaml_tree(obj, tag, _serialization_context)
            try:
                converter = extension_manager.get_converter_for_type(type(obj))
            except KeyError:
                # no converter supports this type, return it as-is
                yield obj
                return
            if converter in converters_used:
                msg = "Conversion cycle detected"
                raise TypeError(msg)
            tag = converter.select_tag(obj, _serialization_context)
        _serialization_context.assign_object(obj)
        node = converter.to_yaml_tree(obj, tag, _serialization_context)
        _serialization_context.assign_blocks()

        if isinstance(node, GeneratorType):
            generator = node
            node = next(generator)
        else:
            generator = None

        if isinstance(node, dict):
            tagged_node = tagged.TaggedDict(node, tag)
        elif isinstance(node, list):
            tagged_node = tagged.TaggedList(node, tag)
        elif isinstance(node, str):
            tagged_node = tagged.TaggedString(node)
            tagged_node._tag = tag
        else:
            msg = f"Converter returned illegal node type: {util.get_class_name(node)}"
            raise TypeError(msg)

        _serialization_context._mark_extension_used(converter.extension)

        yield tagged_node
        if generator is not None:
            yield from generator

    cfg = config.get_config()
    convert_ndarray_subclasses = cfg.convert_unknown_ndarray_subclasses
    converters_cache = {}

    def _walker(obj):
        typ = type(obj)
        if typ in converters_cache:
            return converters_cache[typ](obj)
        if extension_manager.handles_type(typ):
            converter = extension_manager.get_converter_for_type(typ)
            converters_cache[typ] = lambda obj, _converter=converter: _convert_obj(obj, _converter)
            return _convert_obj(obj, converter)
        if convert_ndarray_subclasses and isinstance(obj, np.ndarray):
            warnings.warn(
                f"A ndarray subclass ({type(obj)}) was converted as a ndarray. "
                "This behavior will be removed from a future version of ASDF. "
                "See https://asdf.readthedocs.io/en/latest/asdf/config.html#convert-unknown-ndarray-subclasses",
                AsdfConversionWarning,
            )
            converter = extension_manager.get_converter_for_type(np.ndarray)
            converters_cache[typ] = lambda obj, _converter=converter: _convert_obj(obj, _converter)
            return _convert_obj(obj, converter)

        converters_cache[typ] = lambda obj: obj
        return obj

    return treeutil.walk_and_modify(
        tree,
        _walker,
        # Walk the tree in preorder, so that extensions can return
        # container nodes with unserialized children.
        postorder=False,
        _context=ctx._tree_modification_context,
    )


def tagged_tree_to_custom_tree(tree, ctx, force_raw_types=False, _serialization_context=None):
    """
    Convert a tree containing only basic data types, annotated with
    tags, to a tree containing custom data types.
    """
    if _serialization_context is None:
        _serialization_context = ctx._create_serialization_context(BlockAccess.READ)

    extension_manager = _serialization_context.extension_manager

    def _walker(node):
        if force_raw_types:
            return node

        tag = getattr(node, "_tag", None)
        if tag is None:
            return node

        if extension_manager.handles_tag(tag):
            converter = extension_manager.get_converter_for_tag(tag)
            obj = converter.from_yaml_tree(node.data, tag, _serialization_context)
            _serialization_context.assign_object(obj)
            _serialization_context.assign_blocks()
            _serialization_context._mark_extension_used(converter.extension)
            return obj

        if not ctx._ignore_unrecognized_tag:
            warnings.warn(
                f"{tag} is not recognized, converting to raw Python data structure",
                AsdfConversionWarning,
            )
        return node

    return treeutil.walk_and_modify(
        tree,
        _walker,
        # Walk the tree in postorder, so that extensions receive
        # container nodes with children already deserialized.
        postorder=True,
        _context=ctx._tree_modification_context,
    )


def load_tree(stream):
    """
    Load YAML, returning a tree of objects.

    Parameters
    ----------
    stream : readable file-like object
        Stream containing the raw YAML content.
    """
    # The following call to yaml.load is safe because we're
    # using a loader that inherits from pyyaml's SafeLoader.
    return yaml.load(stream, Loader=AsdfLoader)  # noqa: S506


def dump_tree(tree, fd, ctx, tree_finalizer=None, _serialization_context=None):
    """
    Dump a tree of objects, possibly containing custom types, to YAML.

    Parameters
    ----------
    tree : object
        Tree of objects, possibly containing custom data types.

    fd : asdf.generic_io.GenericFile
        A file object to dump the serialized YAML to.

    ctx : Context
        The writing context.

    tree_finalizer : callable, optional
        Callback that receives the tagged tree before it is validated
        and defaults are removed.  `asdf.AsdfFile` uses this to update
        extension metadata on the tagged tree before it is fully
        serialized to YAML.
    """
    # The _serialization_context parameter allows AsdfFile to track
    # what extensions were used when converting the tree's custom
    # types.  In 3.0, it will be passed as the `ctx` instead of the
    # AsdfFile itself.
    if type(tree) is not AsdfObject:
        msg = "Root node of ASDF tree must be of type AsdfObject"
        raise TypeError(msg)

    tags = {"!": STSCI_SCHEMA_TAG_BASE + "/"}
    tree = custom_tree_to_tagged_tree(tree, ctx, _serialization_context=_serialization_context)
    if tree_finalizer is not None:
        tree_finalizer(tree)
    schema.validate(tree, ctx)

    # add yaml %TAG definitions from extensions
    if _serialization_context:
        for ext in _serialization_context._extensions_used:
            for key, val in ext.yaml_tag_handles.items():
                if key not in tags:
                    tags[key] = val

    try:
        yaml.dump_all(
            [tree],
            stream=fd,
            Dumper=AsdfDumper,
            explicit_start=True,
            explicit_end=True,
            version=_YAML_VERSION,
            allow_unicode=True,
            encoding="utf-8",
            tags=tags,
        )
    except yaml.representer.RepresenterError as err:
        if len(err.args) < 2:
            raise err
        # inspect the exception arguments to determine what object failed
        obj = err.args[1]
        msg = (
            f"Object of type[{type(obj)}] is not serializable by asdf. "
            "Please convert the object to a supported type or implement "
            "a Converter for this type to allow the tree to be serialized."
        )
        raise AsdfSerializationError(msg, obj) from err
