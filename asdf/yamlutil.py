# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import numpy as np

import six

import yaml

from . compat.odict import OrderedDict
from . constants import YAML_TAG_PREFIX
from . import schema
from . import tagged
from . import treeutil
from . import util


if getattr(yaml, '__with_libyaml__', None):  # pragma: no cover
    _yaml_base_dumper = yaml.CSafeDumper
    _yaml_base_loader = yaml.CSafeLoader
else:  # pragma: no cover
    _yaml_base_dumper = yaml.SafeDumper
    _yaml_base_loader = yaml.SafeLoader


# ----------------------------------------------------------------------
# Custom loader/dumpers


_yaml_base_type_map = {
    yaml.MappingNode:
        lambda node, loader: loader.construct_mapping(node, deep=True),
    yaml.SequenceNode:
        lambda node, loader: loader.construct_sequence(node, deep=True),
    yaml.ScalarNode:
        lambda node, loader: loader.construct_scalar(node)
}


def _yaml_to_base_type(node, loader):
    """
    Converts a PyYAML node type to a basic Python data type.

    Parameters
    ----------
    node : yaml.Node
        The node is converted to a basic Python type using the following:
        - MappingNode -> dict
        - SequenceNode -> list
        - ScalarNode -> str, int, float etc.

    loader : yaml.Loader

    Returns
    -------
    basic : object
        Basic Python data type.
    """
    def unknown_type_exception(node, loader):
        raise TypeError("Don't know how to implicitly construct '{0}'".format(
            type(node)))

    return _yaml_base_type_map.get(
        type(node), unknown_type_exception)(node, loader)


class AsdfDumper(_yaml_base_dumper):
    """
    A specialized YAML dumper that understands "tagged basic Python
    data types" as implemented in the `tagged` module.
    """
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


AsdfDumper.add_representer(tagged.TaggedList, represent_sequence)
AsdfDumper.add_representer(tagged.TaggedDict, represent_mapping)
AsdfDumper.add_representer(tagged.TaggedString, represent_scalar)


class AsdfLoader(_yaml_base_loader):
    """
    A specialized YAML loader that can construct "tagged basic Python
    data types" as implemented in the `tagged` module.
    """
    def construct_object(self, node, deep=False):
        tag = node.tag
        if node.tag in self.yaml_constructors:
            return super(AsdfLoader, self).construct_object(node, deep=False)
        data = _yaml_to_base_type(node, self)
        tag = self.ctx.type_index.fix_yaml_tag(tag)
        data = tagged.tag_object(tag, data)
        return data


# ----------------------------------------------------------------------
# Handle omap (ordered mappings)

YAML_OMAP_TAG = YAML_TAG_PREFIX + 'omap'


# Add support for loading YAML !!omap objects as OrderedDicts and dumping
# OrderedDict in the omap format as well.
def ordereddict_constructor(loader, node):
    try:
        omap = loader.construct_yaml_omap(node)
        return OrderedDict(*omap)
    except yaml.constructor.ConstructorError:
        return list(*loader.construct_yaml_seq(node))


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


AsdfLoader.add_constructor(YAML_OMAP_TAG, ordereddict_constructor)
AsdfDumper.add_representer(OrderedDict, represent_ordereddict)


# ----------------------------------------------------------------------
# Handle numpy scalars

for scalar_type in util.iter_subclasses(np.floating):
    AsdfDumper.add_representer(scalar_type, AsdfDumper.represent_float)

for scalar_type in util.iter_subclasses(np.integer):
    AsdfDumper.add_representer(scalar_type, AsdfDumper.represent_int)


# ----------------------------------------------------------------------
# Unicode fix on Python 2

if six.PY2:
    # This dumps Python unicode strings as regular YAML strings rather
    # than !!python/unicode. See http://pyyaml.org/ticket/11
    def _unicode_representer(dumper, value):
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)
    AsdfDumper.add_representer(unicode, _unicode_representer)

    AsdfLoader.add_constructor('tag:yaml.org,2002:str',
                               AsdfLoader.construct_scalar)


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

    return treeutil.walk_and_modify(tree, walker)


def tagged_tree_to_custom_tree(tree, ctx):
    """
    Convert a tree containing only basic data types, annotated with
    tags, to a tree containing custom data types.
    """
    def walker(node):
        tag_name = getattr(node, '_tag', None)
        if tag_name is not None:
            tag_type = ctx.type_index.from_yaml_tag(tag_name)
            if tag_type is not None:
                return tag_type.from_tree_tagged(node, ctx)
        return node

    return treeutil.walk_and_modify(tree, walker)


def load_tree(stream, ctx):
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
    if hasattr(tree, 'yaml_tag'):
        tag = tree.yaml_tag
        tag = tag[:tag.index('/core/asdf') + 1]
        if tag.strip():
            tags = {'!': tag}

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
