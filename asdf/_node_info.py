import re
from collections import namedtuple

from .schema import load_schema
from .treeutil import get_children


def collect_schema_info(key, node, identifier="root", preserve_list=True, refresh_extension_manager=False):
    """
    Collect from the underlying schemas any of the info stored under key.
    """

    schema_info = NodeSchemaInfo.from_root_node(
        key, identifier, node, refresh_extension_manager=refresh_extension_manager
    )

    return schema_info.collect_info(preserve_list=preserve_list)


def _get_extension_manager(refresh_extension_manager):
    from .asdf import AsdfFile, get_config
    from .extension import ExtensionManager

    af = AsdfFile()
    if refresh_extension_manager:
        config = get_config()
        af._extension_manager = ExtensionManager(config.extensions)

    return af.extension_manager


SchemaInfo = namedtuple("SchemaInfo", ["info", "value"])


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

    def __init__(self, key, parent, identifier, node, depth, recursive=False, visible=True):
        self.key = key
        self.parent = parent
        self.identifier = identifier
        self.node = node
        self.depth = depth
        self.recursive = recursive
        self.visible = visible
        self.children = []
        self.schema = None

    @classmethod
    def traversable(cls, node):
        """
        This method determines if the node is an instance of a class that
        supports introspection by the info machinery. This determined by
        the presence of a __asdf_traverse__ method.
        """
        return hasattr(node, "__asdf_traverse__")

    @property
    def visible_children(self):
        return [c for c in self.children if c.visible]

    @property
    def parent_node(self):
        if self.parent is not None:
            return self.parent.node

    @property
    def info(self):
        if self.schema is not None:
            return self.schema.get(self.key, None)

    def get_schema_for_property(self, identifier):
        subschema = self.schema.get("properties", {}).get(identifier, None)
        if subschema is not None:
            return subschema

        subschema = self.schema.get("properties", {}).get("patternProperties", None)
        if subschema:
            for key in subschema:
                if re.search(key, identifier):
                    return subschema[key]
        return {}

    def set_schema_for_property(self, parent, identifier):
        """Extract a subschema from the parent for the identified property"""

        self.schema = parent.get_schema_for_property(identifier)

    def set_schema_from_node(self, node, extension_manager):
        """Pull a tagged schema for the node"""

        tag_def = extension_manager.get_tag_definition(node._tag)
        schema_uri = tag_def.schema_uris[0]
        schema = load_schema(schema_uri)

        self.schema = schema

    @classmethod
    def from_root_node(cls, key, root_identifier, root_node, schema=None, refresh_extension_manager=False):
        """
        Build a NodeSchemaInfo tree from the given ASDF root node.
        Intentionally processes the tree in breadth-first order so that recursively
        referenced nodes are displayed at their shallowest reference point.
        """
        extension_manager = _get_extension_manager(refresh_extension_manager)

        current_nodes = [(None, root_identifier, root_node)]
        seen = set()
        root_info = None
        current_depth = 0
        while True:
            next_nodes = []

            for parent, identifier, node in current_nodes:
                if (isinstance(node, dict) or isinstance(node, tuple) or cls.traversable(node)) and id(node) in seen:
                    info = NodeSchemaInfo(key, parent, identifier, node, current_depth, recursive=True)
                    parent.children.append(info)

                else:
                    info = NodeSchemaInfo(key, parent, identifier, node, current_depth)

                    if root_info is None:
                        root_info = info

                    if parent is not None:
                        if parent.schema is not None and not cls.traversable(node):
                            info.set_schema_for_property(parent, identifier)

                        parent.children.append(info)

                    seen.add(id(node))

                    if cls.traversable(node):
                        t_node = node.__asdf_traverse__()
                        info.set_schema_from_node(node, extension_manager)

                    else:
                        t_node = node

                    if parent is None:
                        info.schema = schema

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
        if preserve_list and (isinstance(self.node, list) or isinstance(self.node, tuple)) and self.info is None:
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
