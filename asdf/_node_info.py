import re
from collections import namedtuple

from .schema import load_schema
from .treeutil import get_children, is_container
from .util import NotSet


def _filter_tree(info, filters):
    """
    Keep nodes in tree which pass the all of the filters.

    Mutates the tree.
    """
    filtered_children = []
    for child in info.children:
        if _filter_tree(child, filters):
            filtered_children.append(child)
    info.children = filtered_children

    return len(info.children) > 0 or all(f(info.node, info.identifier) for f in filters)


def _get_matching_schema_property(schema, property_name):
    """
    Extract a property subschema for a given property_name.
    This function does not descend into the schema (beyond
    looking for a "properties" key) and does not support
    schema combiners.

    Parameters
    ----------
    schema : dict
        A dictionary containing a JSONSCHEMA
    property_name : str
        The name of the property to extract

    Returns
    -------
    dict or None
        The property subschema at the provided name or
        ``None`` if the property doesn't exist.
    """
    if "properties" in schema:
        props = schema["properties"]
        if property_name in props:
            return props[property_name]
        if "patternProperties" in props:
            patterns = props["patternProperties"]
            for regex in patterns:
                if re.search(regex, property_name):
                    return patterns[regex]
    return None


def _get_subschema_for_property(schema, property_name):
    """
    Extract a property subschema for a given property_name.
    This function will attempt to consider schema combiners
    and will return None on an ambiguous result.

    Parameters
    ----------
    schema : dict
        A dictionary containing a JSONSCHEMA
    property_name : str
        The name of the property to extract

    Returns
    -------
    dict or None
        The property subschema at the provided name or
        ``None`` if the property doesn't exist or is
        ambiguous (has more than one subschema or is nested in a not).
    """
    # This does NOT handle $ref the expectation is that the schema
    # is loaded with resolve_references=True
    applicable = []

    # first check properties and patternProperties
    subschema = _get_matching_schema_property(schema, property_name)
    if subschema is not None:
        applicable.append(subschema)

    # next handle schema combiners
    if "not" in schema:
        subschema = _get_subschema_for_property(schema["not"], property_name)
        if subschema is not None:
            # We can't resolve a valid subschema under a "not" since
            # we'd have to know how to invert a schema
            return None

    for combiner in ("allOf", "oneOf", "anyOf"):
        for combined_schema in schema.get(combiner, []):
            subschema = _get_subschema_for_property(combined_schema, property_name)
            if subschema is not None:
                applicable.append(subschema)

    # only return the subschema if we found exactly 1 applicable
    if len(applicable) == 1:
        return applicable[0]
    return None


def _get_schema_key(schema, key):
    """
    Extract a subschema at a given key.
    This function will attempt to consider schema combiners
    (allOf, oneOf, anyOf) and will return None on an
    ambiguous result (where more than 1 match is found).

    Parameters
    ----------
    schema : dict
        A dictionary containing a JSONSCHEMA
    key : str
        The key under which the subschema is stored

    Returns
    -------
    dict or None
        The subschema at the provided key or
        ``None`` if the key doesn't exist or is ambiguous.
    """
    applicable = []
    if key in schema:
        applicable.append(schema[key])
    # Here we don't consider any subschema under "not" to avoid
    # false positives for keys like "type" etc.
    for combiner in ("allOf", "oneOf", "anyOf"):
        for combined_schema in schema.get(combiner, []):
            possible = _get_schema_key(combined_schema, key)
            if possible is not None:
                applicable.append(possible)

    # only return the property if we found exactly 1 applicable
    if len(applicable) == 1:
        return applicable[0]
    return None


def create_tree(key, node, identifier="root", filters=None, refresh_extension_manager=NotSet, extension_manager=None):
    """
    Create a `NodeSchemaInfo` tree which can be filtered from a base node.

    Parameters
    ----------
    key : str
        The key to look up.
    node : dict
        The asdf tree to search.
    filters : list of functions
        A list of functions that take a node and identifier and return True if the node should be included in the tree.
    preserve_list : bool
        If True, then lists are preserved. Otherwise, they are turned into dicts.
    refresh_extension_manager : bool
        DEPRECATED
        If `True`, refresh the extension manager before looking up the
        key.  This is useful if you want to make sure that the schema
        data for a given key is up to date.
    """
    filters = [] if filters is None else filters

    schema_info = NodeSchemaInfo.from_root_node(
        key,
        identifier,
        node,
        refresh_extension_manager=refresh_extension_manager,
        extension_manager=extension_manager,
    )

    if len(filters) > 0 and not _filter_tree(schema_info, filters):
        return None

    return schema_info


def collect_schema_info(
    key,
    path,
    node,
    identifier="root",
    filters=None,
    preserve_list=True,
    refresh_extension_manager=NotSet,
    extension_manager=None,
):
    """
    Collect from the underlying schemas any of the info stored under key, relative to the path

    Parameters
    ----------
    key : str
        The key to look up.
    path : str or None
        A dot-separated path to the parameter to find the key information on.
        If None return full dictionary.
    node : dict
        The asdf tree to search.
    filters : list of functions
        A list of functions that take a node and identifier and return True if the node should be included in the tree.
    preserve_list : bool
        If True, then lists are preserved. Otherwise, they are turned into dicts.
    refresh_extension_manager : bool
        DEPRECATED
        If `True`, refresh the extension manager before looking up the
        key.  This is useful if you want to make sure that the schema
        data for a given key is up to date.
    """

    schema_info = create_tree(
        key,
        node,
        identifier=identifier,
        filters=[] if filters is None else filters,
        refresh_extension_manager=refresh_extension_manager,
        extension_manager=extension_manager,
    )

    info = schema_info.collect_info(preserve_list=preserve_list)

    if path is not None:
        for path_key in path.split("."):
            info = info.get(path_key, None)

            if info is None:
                return None

    return info


def _get_extension_manager(refresh_extension_manager):
    from ._asdf import AsdfFile, get_config
    from .extension import ExtensionManager

    if refresh_extension_manager is NotSet:
        refresh_extension_manager = False

    af = AsdfFile()
    if refresh_extension_manager:
        config = get_config()
        af._extension_manager = ExtensionManager(config.extensions)

    return af.extension_manager


def _make_traversable(node, extension_manager):
    if hasattr(node, "__asdf_traverse__"):
        return node.__asdf_traverse__(), True, False
    node_type = type(node)
    if not extension_manager.handles_type(node_type):
        return node, False, False
    return extension_manager.get_converter_for_type(node_type).to_info(node), False, True


_SchemaInfo = namedtuple("SchemaInfo", ["info", "value"])


class SchemaInfo(_SchemaInfo):
    """
    A class to hold the schema info and the value of the node.

    Parameters
    ----------
    info : dict
        The schema info.
    value : object
        The value of the node.
    """

    def __repr__(self):
        return f"{self.info}"


class NodeSchemaInfo:
    """
    Container for keyed information collected from a schema about a node of an ASDF file tree.

        This contains node alongside the parent and child nodes of that node in the ASDF file tree.
        Effectively this means that each of these "node" objects represents the a subtree of the file tree
        rooted at the node in question alongside methods to access the underlying schemas for the portions
        of the ASDF file in question.

    This is used for a variety of general purposes, including:
    - Providing the long descriptions for nodes as described in the schema.
    - Assisting in traversing an ASDF file like trees, to search nodes.
    - Providing a way to pull static information about an ASDF file which has
      been stored within the schemas for that file.

    Parameters
    ----------
    key : str
        The key for the information to be collected from the underlying schema(s).

    parent : NodeSchemaInfo
        The parent node of this node. None if this is the root node.

    identifier : str
        The identifier for this node in the ASDF file tree.

    node : any
        The value of the node in the ASDF file tree.

    depth : int
        The depth of this node in the ASDF file tree.

    recursive : bool
        If this node has already been visited, then this is set to True. Default is False.

    visible : bool
        If this node will be made visible in the output. Default is True.

    children : list
        List of the NodeSchemaInfo objects for the children of this node. This is a leaf node if this is empty.

    schema : dict
        The portion of the underlying schema corresponding to the node.
    """

    def __init__(self, key, parent, identifier, node, depth, recursive=False, visible=True, extension_manager=None):
        self.key = key
        self.parent = parent
        self.identifier = identifier
        self.node = node
        self.depth = depth
        self.recursive = recursive
        self.visible = visible
        self.children = []
        self.schema = None
        self.extension_manager = extension_manager or _get_extension_manager()

    @property
    def visible_children(self):
        return [c for c in self.children if c.visible]

    @property
    def parent_node(self):
        if self.parent is not None:
            return self.parent.node

        return None

    @property
    def info(self):
        if self.schema is None:
            return None
        return _get_schema_key(self.schema, self.key)

    def get_schema_for_property(self, identifier):
        return _get_subschema_for_property(self.schema, identifier) or {}

    def set_schema_for_property(self, parent, identifier):
        """Extract a subschema from the parent for the identified property"""

        self.schema = parent.get_schema_for_property(identifier)

    def set_schema_from_node(self, node, extension_manager):
        """Pull a tagged schema for the node"""

        tag_def = extension_manager.get_tag_definition(node._tag)
        schema_uri = tag_def.schema_uris[0]
        schema = load_schema(schema_uri, resolve_references=True)

        self.schema = schema

    @classmethod
    def from_root_node(
        cls, key, root_identifier, root_node, schema=None, refresh_extension_manager=NotSet, extension_manager=None
    ):
        """
        Build a NodeSchemaInfo tree from the given ASDF root node.
        Intentionally processes the tree in breadth-first order so that recursively
        referenced nodes are displayed at their shallowest reference point.
        """
        extension_manager = extension_manager or _get_extension_manager(refresh_extension_manager)

        current_nodes = [(None, root_identifier, root_node)]
        seen = set()
        root_info = None
        current_depth = 0
        while True:
            next_nodes = []

            for parent, identifier, node in current_nodes:
                # node is the item in the tree
                # We might sometimes not want to use that node directly
                # but instead using a different node for traversal.
                t_node, traversable, from_converter = _make_traversable(node, extension_manager)
                if (is_container(node) or traversable) and id(node) in seen:
                    info = NodeSchemaInfo(
                        key,
                        parent,
                        identifier,
                        node,
                        current_depth,
                        recursive=True,
                        extension_manager=extension_manager,
                    )
                    parent.children.append(info)

                else:
                    info = NodeSchemaInfo(
                        key, parent, identifier, node, current_depth, extension_manager=extension_manager
                    )

                    # If this is the first node keep a reference so we can return it.
                    if root_info is None:
                        root_info = info

                    if parent is None:
                        info.schema = schema

                    if parent is not None:
                        if parent.schema is not None:
                            # descend within the schema of the parent
                            info.set_schema_for_property(parent, identifier)

                        # track that this node is a child of the parent
                        parent.children.append(info)

                    # Track which nodes have been seen to avoid an infinite
                    # loop and to find recursive references
                    # This is tree wide but should be per-branch.
                    seen.add(id(node))

                    # if the node has __asdf_traverse__ and a _tag attribute
                    # that is a valid tag, load it's schema
                    if traversable:
                        if hasattr(node, "_tag") and isinstance(node._tag, str):
                            try:
                                info.set_schema_from_node(node, extension_manager)
                            except KeyError:
                                # if _tag is not a valid tag, no schema will be found
                                # and a KeyError will be raised. We don't raise the KeyError
                                # (or another exception) here as the node (object) might
                                # be using _tag for a non-ASDF purpose.
                                pass

                    # add children to queue
                    for child_identifier, child_node in get_children(t_node):
                        next_nodes.append((info, child_identifier, child_node))

            if len(next_nodes) == 0:
                break

            current_nodes = next_nodes
            current_depth += 1

        return root_info

    def collect_info(self, preserve_list=True):
        """
        Collect the information from the NodeSchemaInfo tree, and return it as nested dict.

        Parameters
        ----------

        preserve_list : bool
            If True, then lists are preserved. Otherwise, they are turned into dicts.
        """
        if preserve_list and isinstance(self.node, (list, tuple)) and self.info is None:
            info = [c_info for child in self.visible_children if len(c_info := child.collect_info(preserve_list)) > 0]
        else:
            info = {
                child.identifier: c_info
                for child in self.visible_children
                if len(c_info := child.collect_info(preserve_list)) > 0
            }

            if self.info is not None:
                info[self.key] = SchemaInfo(self.info, self.node)

        return info
