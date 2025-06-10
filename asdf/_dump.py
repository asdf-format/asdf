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
    """
    Write a tree to an ASDF file.

    Parameters
    ----------
    tree : object
        The tree to dump.

    fp : str or file-like object
        A file-like object to write the ASDF data to.

    version : str, optional
        Version of the ASDF Standard to use.  If not specified, the default
        version will be used.

    extensions : object, optional
        Additional extensions to use when reading and writing the file.
        May be an `asdf.extension.Extension` or a `list` of extensions.

    all_array_storage : string, optional
        If provided, override the array storage type of all blocks.

    all_array_compression : string, optional
        If provided, override the array compression type of all blocks.

    compression_kwargs : dict, optional
        If provided, override the compression parameters of all blocks.

    pad_blocks : bool, optional
        If provided, pad all blocks to the nearest multiple of the block size.

    custom_schema : str, optional
        Path to a custom schema file that will be used for a secondary
        validation pass. This can be used to ensure that particular ASDF
        files follow custom conventions beyond those enforced by the
        standard.
    """
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
    """
    Write tree to a string.

    Parameters
    ----------
    tree : object
        The tree to dump.

    version : str, optional
        Version of the ASDF Standard to use.  If not specified, the default
        version will be used.

    extensions : object, optional
        Additional extensions to use when reading and writing the file.
        May be an `asdf.extension.Extension` or a `list` of extensions.

    all_array_storage : string, optional
        If provided, override the array storage type of all blocks.

    all_array_compression : string, optional
        If provided, override the array compression type of all blocks.

    compression_kwargs : dict, optional
        If provided, override the compression parameters of all blocks.

    pad_blocks : bool, optional
        If provided, pad all blocks to the nearest multiple of the block size.

    custom_schema : str, optional
        Path to a custom schema file that will be used for a secondary
        validation pass. This can be used to ensure that particular ASDF
        files follow custom conventions beyond those enforced by the
        standard.

    Returns
    -------
    str
        The ASDF data as a string.
    """
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
    """
    Load the ASDF tree from a file-like object.

    Parameters
    ----------
    fp : str or file-like object
        A file-like object to read the ASDF data from.

    uri : str, optional
        The URI for this ASDF file.  Used to resolve relative
        references against.  If not provided, will be
        automatically determined from the associated file object,
        if possible and if created from `asdf.open`.

    validate_checksums : bool, optional
        If `True`, validate the blocks against their checksums.

    extensions : object, optional
        Additional extensions to use when reading and writing the file.
        May be an `asdf.extension.Extension` or a `list` of extensions.

    custom_schema : str, optional
        Path to a custom schema file that will be used for a secondary
        validation pass. This can be used to ensure that particular ASDF
        files follow custom conventions beyond those enforced by the
        standard.

    Returns
    -------
    object:
        The ASDF tree.
    """
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


def loads(asdf_string, *, uri=None, validate_checksums=False, extensions=None, custom_schema=None):
    """
    Load the ASDF tree from a string..

    Parameters
    ----------
    asdf_string : str
        A string containing ASDF data.

    uri : str, optional
        The URI for this ASDF file.  Used to resolve relative
        references against.  If not provided, will be
        automatically determined from the associated file object,
        if possible and if created from `asdf.open`.

    validate_checksums : bool, optional
        If `True`, validate the blocks against their checksums.

    extensions : object, optional
        Additional extensions to use when reading and writing the file.
        May be an `asdf.extension.Extension` or a `list` of extensions.

    custom_schema : str, optional
        Path to a custom schema file that will be used for a secondary
        validation pass. This can be used to ensure that particular ASDF
        files follow custom conventions beyond those enforced by the
        standard.

    Returns
    -------
    object:
        The ASDF tree.
    """

    return load(
        BytesIO(asdf_string),
        uri=uri,
        validate_checksums=validate_checksums,
        extensions=extensions,
        custom_schema=custom_schema,
    )
