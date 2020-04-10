# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

import warnings
from collections import OrderedDict

import numpy as np

import yaml

from . import schema
from . import tagged
from . import treeutil
from . import util
from .constants import YAML_TAG_PREFIX
from .versioning import split_tag_version
from .exceptions import AsdfConversionWarning


__all__ = ['custom_tree_to_tagged_tree', 'tagged_tree_to_custom_tree']


if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_dumper = yaml.CSafeDumper
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_dumper = yaml.SafeDumper
    _yaml_base_loader = yaml.SafeLoader


YAML_OMAP_TAG = YAML_TAG_PREFIX + 'omap'


# ----------------------------------------------------------------------
# Custom loader/dumpers


class AsdfDumper(_yaml_base_dumper):
    """
    A specialized YAML dumper that understands "tagged basic Python
    data types" as implemented in the `tagged` module.
    """

    def __init__(self, *args, **kwargs):
        kwargs['default_flow_style'] = None
        super().__init__(*args, **kwargs)

    def represent_data(self, data):
        node = super(AsdfDumper, self).represent_data(data)

        tag_name = getattr(data, '_tag', None)
        if tag_name is not None:
            node.tag = tag_name

        return node


_flow_style_map = {
    'flow': True,
    'block': False
}


def represent_sequence(dumper, sequence):
    flow_style = _flow_style_map.get(sequence.flow_style, None)
    sequence = sequence.data
    return super(AsdfDumper, dumper).represent_sequence(
        None, sequence, flow_style)


def represent_mapping(dumper, mapping):
    flow_style = _flow_style_map.get(mapping.flow_style, None)
    node = super(AsdfDumper, dumper).represent_mapping(
        None, mapping.data, flow_style)

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


_style_map = {
    'inline': '"',
    'folded': '>',
    'literal': '|'
}


def represent_scalar(dumper, value):
    style = _style_map.get(value.style, None)
    return super(AsdfDumper, dumper).represent_scalar(
        None, value.data, style)


def represent_ordered_mapping(dumper, tag, data):
    # TODO: Again, adjust for preferred flow style, and other stylistic details
    # NOTE: For block style this uses the compact omap notation, but for flow style
    # it does not.

    # TODO: Need to see if I can figure out a mechanism so that classes that
    # use this representer can specify which values should use flow style
    values = []
    node = yaml.SequenceNode(tag, values,
                             flow_style=dumper.default_flow_style)
    if dumper.alias_key is not None:
        dumper.represented_objects[dumper.alias_key] = node
    for key, value in data.items():
        key_item = dumper.represent_data(key)
        value_item = dumper.represent_data(value)
        node_item = yaml.MappingNode(YAML_OMAP_TAG,
                                     [(key_item, value_item)],
                                     flow_style=False)
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

for scalar_type in util.iter_subclasses(np.floating):
    AsdfDumper.add_representer(scalar_type, AsdfDumper.represent_float)

for scalar_type in util.iter_subclasses(np.integer):
    AsdfDumper.add_representer(scalar_type, AsdfDumper.represent_int)

def represent_numpy_str(dumper, data):
    # The CSafeDumper implementation will raise an error if it
    # doesn't recognize data as a string.  The Python SafeDumper
    # has no problem with np.str_.
    return dumper.represent_str(str(data))

AsdfDumper.add_representer(np.str_, represent_numpy_str)
AsdfDumper.add_representer(np.bytes_, AsdfDumper.represent_binary)


class AsdfLoader(_yaml_base_loader):
    """
    A specialized YAML loader that can construct "tagged basic Python
    data types" as implemented in the `tagged` module.
    """

    def construct_undefined(self, node):
        if isinstance(node, yaml.MappingNode):
            return self._construct_tagged_mapping(node)
        elif isinstance(node, yaml.SequenceNode):
            return self._construct_tagged_sequence(node)
        elif isinstance(node, yaml.ScalarNode):
            return self._construct_tagged_scalar(node)
        else:
            return super().construct_undefined(node)

    def _construct_tagged_mapping(self, node):
        data = tagged.tag_object(self._fix_tag(node), {})
        yield data
        data.update(self.construct_mapping(node))

    def _construct_tagged_sequence(self, node):
        data = tagged.tag_object(self._fix_tag(node), [])
        yield data
        data.extend(self.construct_sequence(node))

    def _construct_tagged_scalar(self, node):
        return tagged.tag_object(self._fix_tag(node), self.construct_scalar(node))

    # Custom omap deserializer that builds an OrderedDict instead
    # of a list of tuples.  Code is mostly identical to pyyaml's SafeConstructor.
    def construct_yaml_omap(self, node):
        omap = OrderedDict()
        yield omap
        if not isinstance(node, yaml.SequenceNode):
            raise yaml.ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        for subnode in node.value:
            if not isinstance(subnode, yaml.MappingNode):
                raise yaml.ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise yaml.ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node, value_node = subnode.value[0]
            key = self.construct_object(key_node)
            value = self.construct_object(value_node)
            omap[key] = value

    def _fix_tag(self, node):
        return self.ctx.type_index.fix_yaml_tag(
            self.ctx, node.tag, self.ignore_version_mismatch)


# pyyaml will invoke the constructor associated with None when a node's
# tag is not explicitly handled by another constructor.
AsdfLoader.add_constructor(None, AsdfLoader.construct_undefined)
AsdfLoader.add_constructor(YAML_TAG_PREFIX + "omap", AsdfLoader.construct_yaml_omap)


def custom_tree_to_tagged_tree(tree, ctx):
    """
    Convert a tree, possibly containing custom data types that aren't
    directly representable in YAML, to a tree of basic data types,
    annotated with tags.
    """
    def walker(node):
        tag = ctx.type_index.from_custom_type(type(node), ctx.version_string)
        if tag is not None:
            return tag.to_tree_tagged(node, ctx)
        return node

    return treeutil.walk_and_modify(
        tree,
        walker,
        ignore_implicit_conversion=ctx._ignore_implicit_conversion,
        # Walk the tree in preorder, so that extensions can return
        # container nodes with unserialized children.
        postorder=False,
        _context=ctx._tree_modification_context,
    )


def tagged_tree_to_custom_tree(tree, ctx, force_raw_types=False):
    """
    Convert a tree containing only basic data types, annotated with
    tags, to a tree containing custom data types.
    """
    def walker(node):
        if force_raw_types:
            return node

        tag_name = getattr(node, '_tag', None)
        if tag_name is None:
            return node

        tag_type = ctx.type_index.from_yaml_tag(ctx, tag_name)
        # This means the tag did not correspond to any type in our type index.
        if tag_type is None:
            if not ctx._ignore_unrecognized_tag:
                warnings.warn("{} is not recognized, converting to raw Python "
                    "data structure".format(tag_name), AsdfConversionWarning)
            return node

        real_tag = ctx.type_index.get_real_tag(tag_name)
        real_tag_name, real_tag_version = split_tag_version(real_tag)
        # This means that there is an explicit description of versions that are
        # compatible with the associated tag class implementation, but the
        # version we found does not fit that description.
        if tag_type.incompatible_version(real_tag_version):
            warnings.warn("Version {} of {} is not compatible with any "
                "existing tag implementations".format(
                    real_tag_version, real_tag_name),
                AsdfConversionWarning)
            return node

        # If a tag class does not explicitly list compatible versions, then all
        # versions of the corresponding schema are assumed to be compatible.
        # Therefore we need to check to make sure whether the conversion is
        # actually successful, and just return a raw Python data type if it is
        # not.
        try:
            return tag_type.from_tree_tagged(node, ctx)
        except TypeError as err:
            warnings.warn("Failed to convert {} to custom type (detail: {}). "
                "Using raw Python data structure instead".format(real_tag, err),
                AsdfConversionWarning)

        return node

    return treeutil.walk_and_modify(
        tree,
        walker,
        ignore_implicit_conversion=ctx._ignore_implicit_conversion,
        # Walk the tree in postorder, so that extensions receive
        # container nodes with children already deserialized.
        postorder=True,
        _context=ctx._tree_modification_context,
    )


def load_tree(stream, ctx, ignore_version_mismatch=False):
    """
    Load YAML, returning a tree of objects.

    Parameters
    ----------
    stream : readable file-like object
        Stream containing the raw YAML content.
    """
    class AsdfLoaderTmp(AsdfLoader):
        pass
    AsdfLoaderTmp.ctx = ctx
    AsdfLoaderTmp.ignore_version_mismatch = ignore_version_mismatch

    return yaml.load(stream, Loader=AsdfLoaderTmp)


def dump_tree(tree, fd, ctx):
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
    """
    class AsdfDumperTmp(AsdfDumper):
        pass
    AsdfDumperTmp.ctx = ctx

    tags = None
    tree_type = ctx.type_index.from_custom_type(type(tree))
    if tree_type is not None:
        tag_parts = tree_type.yaml_tag.split(':')
        last_part = tag_parts[-1]
        if '/' in last_part:
            last_part = last_part[0:last_part.index('/') + 1]
        else:
            last_part = ''
        yaml_tag = ':'.join(tag_parts[0:-1] + [last_part])
        tags = {'!': yaml_tag}

    tree = custom_tree_to_tagged_tree(tree, ctx)
    schema.validate(tree, ctx)
    schema.remove_defaults(tree, ctx)

    yaml_version = tuple(
        int(x) for x in ctx.version_map['YAML_VERSION'].split('.'))

    yaml.dump_all(
        [tree], stream=fd, Dumper=AsdfDumperTmp,
        explicit_start=True, explicit_end=True,
        version=yaml_version,
        allow_unicode=True, encoding='utf-8',
        tags=tags)
