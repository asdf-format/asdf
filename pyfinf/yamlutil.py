# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

from astropy.extern import six
from astropy.utils.compat.odict import OrderedDict

import yaml

from . constants import YAML_TAG_PREFIX
from . import finftypes
from . import tagged
from . import treeutil


# ----------------------------------------------------------------------
# Custom loader/dumpers

def yaml_to_base_type(node, loader):
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
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    elif isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    else:
        raise TypeError("Don't know how to implicitly construct '{0}'".format(
            type(node)))


class FinfDumper(yaml.SafeDumper):
    """
    A specialized YAML dumper that understands "tagged basic Python
    data types" as implemented in the `tagged` module.
    """
    def represent_data(self, data):
        tag_name = tagged.get_tag(data)
        if tag_name is not None:
            node = yaml.SafeDumper.represent_data(self, data.data)
            node.tag = tag_name
        else:
            node = yaml.SafeDumper.represent_data(self, data)
        return node


class FinfLoader(yaml.SafeLoader):
    """
    A specialized YAML loader that can construct "tagged basic Python
    data types" as implemented in the `tagged` module.
    """
    def construct_object(self, node, deep=False):
        tag = node.tag
        if node.tag in self.yaml_constructors:
            return yaml.SafeLoader.construct_object(self, node, deep=False)
        data = yaml_to_base_type(node, self)
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


FinfLoader.add_constructor(YAML_OMAP_TAG, ordereddict_constructor)
FinfDumper.add_representer(OrderedDict, represent_ordereddict)


# ----------------------------------------------------------------------
# Unicode fix on Python 2

if six.PY2:
    # This dumps Python unicode strings as regular YAML strings rather
    # than !!python/unicode. See http://pyyaml.org/ticket/11
    def _unicode_representer(dumper, value):
        return dumper.represent_scalar("tag:yaml.org,2002:str", value)
    FinfDumper.add_representer(unicode, _unicode_representer)

    FinfLoader.add_constructor('tag:yaml.org,2002:str',
                               FinfLoader.construct_scalar)


# ----------------------------------------------------------------------
# Context

class Context(object):
    """
    The context class maintains useful state during the parsing or
    writing of YAML.
    """
    def __init__(self, finffile, type_index=None, options={}):
        """
        Parameters
        ----------
        finffile : FinfFile instance
            Required so that objects in the tree can access the blocks
            in the finffile.

        type_index : FinfTypeIndex or subclass, optional
            Can be overridden to change the selection of types/tags
            that are available when parsing the YAML.
        """
        self._finffile = finffile
        if finffile is not None:
            self._versionspec = finffile.versionspec
        if type_index is None:
            type_index = finftypes.FinfTypeIndex
        self._type_index = type_index
        self._options = options

    def __getitem__(self, attr):
        return self._options[attr]

    def get(self, attr, default=None):
        return self._options.get(attr, default)

    @property
    def finffile(self):
        return self._finffile

    @property
    def versionspec(self):
        return self._versionspec

    def to_tree(self, tree):
        """
        Recursively convert the tree, possibly containing custom data
        types, to a tree containing only tagged basic data types, and
        return the result.
        """
        return custom_tree_to_tagged_tree(tree, self)

    def run_hook(self, tree, hookname):
        """
        Run a "hook" for each custom type found in the tree.

        Parameters
        ----------
        tree : object
            A tree of objects, possibly containing custom data types.

        hookname : str
            The name of the hook.  If a `FinfType` is found with a method
            with this name, it will be called for every instance of the
            corresponding custom type in the tree.
        """
        return run_hook(tree, hookname, self)

    @property
    def type_index(self):
        """
        Get the type index, which can be used to find type converters
        by name or associated custom type.
        """
        return self._type_index


def custom_tree_to_tagged_tree(tree, ctx):
    """
    Convert a tree, possibly containing custom data types that aren't
    directly representable in YAML, to a tree of basic data types,
    annotated with tags.
    """
    if not isinstance(ctx, Context):
        ctx = Context(ctx)

    def walker(node):
        tag = ctx.type_index.get_finftype_from_custom_type(type(node))
        if tag is not None:
            node = tag.to_tree(node, ctx)
            node = tagged.tag_object(tag.yaml_tag, node)
            return node
        return node

    return tagged.walk_and_modify_with_tags(tree, walker)


def tagged_tree_to_custom_tree(tree, ctx):
    """
    Convert a tree containing only basic data types, annotated with
    tags, to a tree containing custom data types.
    """
    if not isinstance(ctx, Context):
        ctx = Context(ctx)

    def walker(node):
        tag_name = tagged.get_tag(node)
        if tag_name is not None:
            tag_type = ctx.type_index.get_finftype_from_yaml_tag(tag_name)
            if tag_type is not None:
                return tag_type.from_tree(node.data, ctx)
        return node

    return tagged.walk_and_modify_with_tags(tree, walker)


def validate_tagged_tree(tree, ctx):
    """
    Validate a tree of tagged basic data types against any relevant
    schemas, both at the root level and anywhere a tag is found with a
    matching schema.
    """
    if not isinstance(ctx, Context):
        ctx = Context(ctx)

    def walker(node):
        tag_name = tagged.get_tag(node)
        if tag_name is not None:
            tag = ctx.type_index.get_finftype_from_yaml_tag(tag_name)
            if tag is not None:
                tag.validate(node)
    return treeutil.walk(tree, walker)


def validate(tree, ctx):
    """
    Validate a tree, possibly containing custom data types, against
    any relevant schemas, both at the root level and anywhere else a
    tag is found with a matching schema.
    """
    tagged_tree = custom_tree_to_tagged_tree(tree, ctx)
    validate_tagged_tree(tagged_tree, ctx)


def run_hook(tree, hookname, ctx):
    """
    Run a "hook" for each custom type found in the tree.

    Parameters
    ----------
    tree : object
        A tree of objects, possibly containing custom data types.

    hookname : str
        The name of the hook.  If a `FinfType` is found with a method
        with this name, it will be called for every instance of the
        corresponding custom type in the tree.

    ctx : Context
        The YAML parsing context.
    """
    def walker(node):
        tag = ctx.type_index.get_finftype_from_custom_type(type(node))
        if tag is not None:
            hook = getattr(tag, hookname, None)
            if hook is not None:
                hook(node, ctx)
    return treeutil.walk(tree, walker)


def load_tree(yaml_content, ctx):
    """
    Load YAML, returning a tree of objects and custom types.

    Parameters
    ----------
    yaml_content : bytes
        The raw serialized YAML content.

    ctx : Context
        The parsing context.
    """
    if not isinstance(ctx, Context):
        ctx = Context(ctx)

    class FinfLoaderTmp(FinfLoader):
        pass
    FinfLoaderTmp.ctx = ctx

    tree = yaml.load(yaml_content, Loader=FinfLoaderTmp)
    validate_tagged_tree(tree, ctx)
    tree = tagged_tree_to_custom_tree(tree, ctx)
    return tree


def dump_tree(tree, fd, ctx):
    """
    Dump a tree of objects, possibly containing custom types, to YAML.

    Parameters
    ----------
    tree : object
        Tree of objects, possibly containing custom data types.

    fd : pyfinf.generic_io.GenericFile
        A file object to dump the serialized YAML to.

    ctx : Context
        The writing context.
    """
    if not isinstance(ctx, Context):
        ctx = Context(ctx)

    class FinfDumperTmp(FinfDumper):
        pass
    FinfDumperTmp.ctx = ctx

    tag = tree.yaml_tag
    tag = tag[:tag.index('/finf') + 1]
    tree = custom_tree_to_tagged_tree(tree, ctx)
    validate_tagged_tree(tree, ctx)

    yaml.dump_all(
        [tree], stream=fd, Dumper=FinfDumperTmp,
        explicit_start=True, explicit_end=True,
        version=ctx.versionspec.yaml_version,
        allow_unicode=True,
        encoding='utf-8',
        tags={'!': tag})
