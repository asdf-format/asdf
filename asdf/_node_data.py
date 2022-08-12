import re
from collections import namedtuple

from .schema import load_schema
from .treeutil import get_children


def collect_schema_data(key, node, identifier="root", preserve_list=True, refresh_extension_manager=False):
    """
    Collect from the underlying schemas any of the data stored under key.
    """

    schema_data = NodeSchemaData.from_root_node(
        key, identifier, node, refresh_extension_manager=refresh_extension_manager
    )

    return schema_data.collect_data(preserve_list=preserve_list)


SchemaData = namedtuple("SchemaData", ["data", "value"])


class NodeSchemaData:
    """
    Container for a node, and the values of data from a schema
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
        self.data = None
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

    def extract_schema_data(self, schema):
        self.schema = schema
        self.data = schema.get(self.key, None)

    @classmethod
    def from_root_node(cls, key, root_identifier, root_node, schema=None, refresh_extension_manager=False):
        """
        Build a NodeSchemaData tree from the given ASDF root node.
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
        root_data = None
        current_depth = 0
        while True:
            next_nodes = []

            for parent, identifier, node in current_nodes:
                if (isinstance(node, dict) or isinstance(node, tuple) or cls.traversable(node)) and id(node) in seen:
                    data = NodeSchemaData(key, parent, identifier, node, current_depth, recursive=True)
                    parent.children.append(data)

                else:
                    data = NodeSchemaData(key, parent, identifier, node, current_depth)

                    if root_data is None:
                        root_data = data

                    if parent is not None:
                        if parent.schema is not None and not cls.traversable(node):
                            # Extract subschema if it exists
                            subschema = parent.get_schema_for_property(identifier)
                            data.extract_schema_data(subschema)

                        parent.children.append(data)

                    seen.add(id(node))

                    if cls.traversable(node):
                        tnode = node.__asdf_traverse__()
                        # Look for a title for the attribute if it is a tagged object
                        tag = node._tag
                        tagdef = extmgr.get_tag_definition(tag)
                        schema_uri = tagdef.schema_uris[0]
                        schema = load_schema(schema_uri)
                        data.extract_schema_data(schema)

                    else:
                        tnode = node

                    if parent is None:
                        data.schema = schema

                    for child_identifier, child_node in get_children(tnode):
                        next_nodes.append((data, child_identifier, child_node))
                        # extract subschema if appropriate

            if len(next_nodes) == 0:
                break

            current_nodes = next_nodes
            current_depth += 1

        return root_data

    def collect_data(self, preserve_list=True):
        """
        Collect the data from the NodeSchemaData tree, and return it as nested dict.

        Parameters
        ----------

        preserve_list : bool
            If True, then lists are preserved. Otherwise, they are turned into dicts.
        """
        if preserve_list and (isinstance(self.node, list) or isinstance(self.node, tuple)) and self.data is None:
            data = [cdata for child in self.visible_children if len(cdata := child.collect_data(preserve_list)) > 0]
        else:
            data = {
                child.identifier: cdata
                for child in self.visible_children
                if len(cdata := child.collect_data(preserve_list)) > 0
            }

            if self.data is not None:
                data[self.key] = SchemaData(self.data, self.node)

        return data
