from io import BytesIO

from asdf._asdf import AsdfFile, open_asdf
from asdf.util import NotSet

__all__ = ["dump", "dumps", "load", "loads"]


def dump(
    tree,
    fp,
    *,
    version=None,
    extensions=None,
    all_array_storage=NotSet,
    all_array_compression=NotSet,
    compression_kwargs=NotSet,
    pad_blocks=False,
    custom_schema=None,
):
    AsdfFile(tree, custom_schema=custom_schema, extensions=extensions).write_to(
        fp,
        version=version,
        all_array_storage=all_array_storage,
        all_array_compression=all_array_compression,
        compression_kwargs=compression_kwargs,
        pad_blocks=pad_blocks,
    )


def dumps(
    tree,
    *,
    version=None,
    extensions=None,
    all_array_storage=NotSet,
    all_array_compression=NotSet,
    compression_kwargs=NotSet,
    pad_blocks=False,
    custom_schema=None,
):
    buff = BytesIO()
    dump(
        tree,
        buff,
        version=version,
        extensions=extensions,
        all_array_storage=all_array_storage,
        all_array_compression=all_array_compression,
        compression_kwargs=compression_kwargs,
        pad_blocks=pad_blocks,
        custom_schema=custom_schema,
    )
    return buff.getvalue()


def load(fp, *, uri=None, validate_checksums=False, extensions=None, custom_schema=None):
    with open_asdf(
        fp,
        lazy_load=False,
        memmap=False,
        lazy_tree=False,
        uri=uri,
        validate_checksums=validate_checksums,
        extensions=extensions,
        custom_schema=custom_schema,
    ) as af:
        return af.tree


def loads(fp, *, uri=None, validate_checksums=False, extensions=None, custom_schema=None):
    return load(
        BytesIO(fp), uri=uri, validate_checksums=validate_checksums, extensions=extensions, custom_schema=custom_schema
    )
