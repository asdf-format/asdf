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


SchemaInfo = namedtuple("SchemaInfo", ["info", "value"])


class NodeSchemaInfo:
    """
    Container for a node, and the values of information from a schema
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
        self.info = None
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
        if self.parent is None:
            return None
        else:
            return self.parent.node

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

    def extract_schema_info(self, schema):
        self.schema = schema
        self.info = schema.get(self.key, None)

    @classmethod
    def from_root_node(cls, key, root_identifier, root_node, schema=None, refresh_extension_manager=False):
        """
        Build a NodeSchemaInfo tree from the given ASDF root node.
        Intentionally processes the tree in breadth-first order so that recursively
        referenced nodes are displayed at their shallowest reference point.
        """
        from .asdf import AsdfFile, get_config
        from .extension import ExtensionManager

        af = AsdfFile()
        if refresh_extension_manager:
            config = get_config()
            af._extension_manager = ExtensionManager(config.extensions)
        extmgr = af.extension_manager

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
                            # Extract subschema if it exists
                            subschema = parent.get_schema_for_property(identifier)
                            info.extract_schema_info(subschema)

                        parent.children.append(info)

                    seen.add(id(node))

                    if cls.traversable(node):
                        tnode = node.__asdf_traverse__()
                        # Look for a title for the attribute if it is a tagged object
                        tag = node._tag
                        tagdef = extmgr.get_tag_definition(tag)
                        schema_uri = tagdef.schema_uris[0]
                        schema = load_schema(schema_uri)
                        info.extract_schema_info(schema)

                    else:
                        tnode = node

                    if parent is None:
                        info.schema = schema

                    for child_identifier, child_node in get_children(tnode):
                        next_nodes.append((info, child_identifier, child_node))
                        # extract subschema if appropriate

            if len(next_nodes) == 0:
                break

            current_nodes = next_nodes
            current_depth += 1

        return root_info

    def collect_info(self, preserve_list=True):
        """
        Collect the information from the NodeSchemaData tree, and return it as nested dict.

        Parameters
        ----------

        preserve_list : bool
            If True, then lists are preserved. Otherwise, they are turned into dicts.
        """
        if preserve_list and (isinstance(self.node, list) or isinstance(self.node, tuple)) and self.info is None:
            info = [cinfo for child in self.visible_children if len(cinfo := child.collect_info(preserve_list)) > 0]
        else:
            info = {
                child.identifier: cinfo
                for child in self.visible_children
                if len(cinfo := child.collect_info(preserve_list)) > 0
            }

            if self.info is not None:
                info[self.key] = SchemaInfo(self.info, self.node)

        return info
