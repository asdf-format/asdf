from asdf.extension import Converter


class ReferenceConverter(Converter):
    tags = []
    types = ["asdf.reference.Reference"]

    def to_yaml_tree(self, obj, tag, ctx):
        from asdf.generic_io import relative_uri

        base_uri = None
        if ctx._blocks._write_fd is not None and ctx._blocks._write_fd.uri is not None:
            base_uri = ctx._blocks._write_fd.uri
        elif ctx.url is not None:
            base_uri = ctx.url
        uri = relative_uri(base_uri, obj._uri) if base_uri is not None else obj._uri
        return {"$ref": uri}

    def from_yaml_tree(self, node, tag, ctx):
        raise NotImplementedError()

    def select_tag(self, obj, tags, ctx):
        return None
