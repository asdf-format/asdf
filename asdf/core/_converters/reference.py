from asdf.extension import Converter


class ReferenceConverter(Converter):
    tags = ["*"]
    types = ["asdf.reference.Reference"]

    def to_yaml_tree(self, obj, tag, ctx):
        from asdf.generic_io import relative_uri

        uri = relative_uri(ctx.url, obj._uri) if ctx.url is not None else obj._uri
        return {"$ref": uri}

    def from_yaml_tree(self, node, tag, ctx):
        pass

    def select_tag(self, obj, tag, ctx):
        return "tag:yaml.org,2002:map"
