# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import io
import re

import numpy as np

from . import asdftypes
from . import block
from . import constants
from . import generic_io
from . import reference
from . import resolver
from . import util
from . import treeutil
from . import versioning
from . import yamlutil

from .tags.core.asdf import AsdfObject


class AsdfFile(versioning.VersionedMixin):
    """
    The main class that represents a ASDF file.
    """
    def __init__(self, tree=None, uri=None,
                 tag_to_schema_resolver=None,
                 url_mapping=None,
                 type_index=None):
        """
        Parameters
        ----------
        tree : dict or AsdfFile, optional
            The main tree data in the ASDF file.  Must conform to the
            ASDF schema.

        uri : str, optional
            The URI for this ASDF file.  Used to resolve relative
            references against.  If not provided, will automatically
            determined from the associated file object, if possible
            and if created from `AsdfFile.read`.

        Other Parameters
        ----------------
        tag_to_schema_resolver : callable, optional
            A callback used to convert tag names into schema
            URIs.  The callable must take a string and return a string
            or `None`.  If not provided, the default
            `astropy.resolvers.TagToSchemaResolver` will be used.

        url_mapping : callable, optional
            A callback function used to map URIs to other URIs.  The
            callable must take a string and return a string or `None`.
            This is useful, for example, when a remote resource has a
            mirror on the local filesystem that you wish to use.

        type_index : pyasdf.asdftypes.AsdfTypeIndex, optional
            A type index object used to lookup custom ASDF types.  It
            must have two methods:

            - `from_custom_type`: Given an object, return the
              corresponding `pyasdf.asdftypes.AsdfType` subclass.

            - `from_yaml_tag`: Given a YAML tag as a string, return the
              corresponding `pyasdf.asdftypes.AsdfType` subclass.
        """
        if tag_to_schema_resolver is None:
            tag_to_schema_resolver = resolver.TAG_TO_SCHEMA_RESOLVER
        self._tag_to_schema_resolver = tag_to_schema_resolver

        if url_mapping is None:
            url_mapping = resolver.URL_MAPPING
        self._url_mapping = url_mapping

        if type_index is None:
            type_index = asdftypes.AsdfTypeIndex()
        self._type_index = type_index

        self._fd = None
        self._external_asdf_by_uri = {}
        self._blocks = block.BlockManager(self)
        if tree is None:
            self.tree = {}
            self._uri = uri
        elif isinstance(tree, AsdfFile):
            self._uri = tree.uri
            self._tree = tree.tree
            self.run_modifying_hook('copy_to_new_asdf')
            self.find_references()
            self._uri = uri
        else:
            self.tree = tree
            self._uri = uri
            self.find_references()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """
        Close the file handles associated with the `AsdfFile`.
        """
        if self._fd:
            # This is ok to always do because GenericFile knows
            # whether it "owns" the file and should close it.
            self._fd.close()
            self._fd = None
        for external in self._external_asdf_by_uri.values():
            external.close()
        self._external_asdf_by_uri.clear()

    @property
    def uri(self):
        """
        Get the URI associated with the `AsdfFile`.

        In many cases, it is automatically determined from the file
        handle used to read or write the file.
        """
        if self._uri is not None:
            return self._uri
        if self._fd is not None:
            return self._fd._uri
        return None

    @property
    def tag_to_schema_resolver(self):
        return self._tag_to_schema_resolver

    @property
    def url_mapping(self):
        return self._url_mapping

    @property
    def type_index(self):
        return self._type_index

    def resolve_uri(self, uri):
        """
        Resolve a (possibly relative) URI against the URI of this ASDF
        file.  May be overridden by base classes to change how URIs
        are resolved.  This does not apply any `uri_mapping` that was
        passed to the constructor.

        Parameters
        ----------
        uri : str
            An absolute or relative URI to resolve against the URI of
            this ASDF file.

        Returns
        -------
        uri : str
            The resolved URI.
        """
        return generic_io.resolve_uri(self.uri, uri)

    def read_external(self, uri):
        """
        Load an external ASDF file, from the given (possibly relative)
        URI.  There is a cache (internal to this ASDF file) that ensures
        each external ASDF file is loaded only once.

        Parameters
        ----------
        uri : str
            An absolute or relative URI to resolve against the URI of
            this ASDF file.

        Returns
        -------
        asdffile : AsdfFile
            The external ASDF file.
        """
        # For a cache key, we want to ignore the "fragment" part.
        base_uri = util.get_base_uri(uri)
        resolved_uri = self.resolve_uri(base_uri)

        # A uri like "#" should resolve back to ourself.  In that case,
        # just return `self`.
        if resolved_uri == '' or resolved_uri == self.uri:
            return self

        asdffile = self._external_asdf_by_uri.get(resolved_uri)
        if asdffile is None:
            asdffile = self.read(resolved_uri)
            self._external_asdf_by_uri[resolved_uri] = asdffile
        return asdffile

    @property
    def tree(self):
        """
        Get the tree of data in the ASDF file.

        When set, the tree will be validated against the ASDF schema.
        """
        return self._tree

    @tree.setter
    def tree(self, tree):
        yamlutil.validate(tree, self)

        self._tree = AsdfObject(tree)

    def make_reference(self, path=[]):
        """
        Make a new reference to a part of this file's tree, that can be
        assigned as a reference to another tree.

        Parameters
        ----------
        path : list of str and int, optional
            The parts of the path pointing to an item in this tree.
            If omitted, points to the root of the tree.

        Returns
        -------
        reference : reference.Reference
            A reference object.

        Examples
        --------
        For the given AsdfFile ``ff``, add an external reference to the data in
        an external file::

            >>> import pyasdf
            >>> flat = pyasdf.open("http://stsci.edu/reference_files/flat.asdf")  # doctest: +SKIP
            >>> ff.tree['flat_field'] = flat.make_reference(['data'])  # doctest: +SKIP
        """
        return reference.make_reference(self, path)

    @property
    def blocks(self):
        """
        Get the block manager associated with the `AsdfFile`.
        """
        return self._blocks

    def set_array_storage(self, arr, array_storage):
        """
        Set the block type to use for the given array data.

        Parameters
        ----------
        arr : numpy.ndarray
            The array to set.  If multiple views of the array are in
            the tree, only the most recent block type setting will be
            used, since all views share a single block.

        array_storage : str
            Must be one of:

            - ``internal``: The default.  The array data will be
              stored in a binary block in the same ASDF file.

            - ``external``: Store the data in a binary block in a
              separate ASDF file.

            - ``inline``: Store the data as YAML inline in the tree.
        """
        self.blocks[arr].array_storage = array_storage

    def get_array_storage(self, arr):
        """
        Get the block type for the given array data.

        Parameters
        ----------
        arr : numpy.ndarray
        """
        return self.blocks[arr].array_storage

    def set_array_compression(self, arr, compression):
        """
        Set the compression to use for the given array data.

        Parameters
        ----------
        arr : numpy.ndarray
            The array to set.  If multiple views of the array are in
            the tree, only the most recent compression setting will be
            used, since all views share a single block.

        array_compression : str or None
            Must be one of:

            - ``zlib``: Use zlib compression

            - ``''`` or `None`: no compression
        """
        self.blocks[arr].compression = compression

    def get_array_compression(self, arr):
        """
        Get the compression type for the given array data.

        Parameters
        ----------
        arr : numpy.ndarray

        Returns
        -------
        compression : str or None
        """
        return self.blocks[arr].compression

    @classmethod
    def _parse_header_line(cls, line):
        """
        Parses the header line in a ASDF file to obtain the ASDF version.
        """
        regex = (constants.ASDF_MAGIC +
                 b'(?P<major>[0-9]+)\.(?P<minor>[0-9]+)\.(?P<micro>[0-9]+)')
        match = re.match(regex, line)
        if match is None:
            raise ValueError("Does not appear to be a ASDF file.")
        return (int(match.group("major")),
                int(match.group("minor")),
                int(match.group("micro")))

    @classmethod
    def read(cls, fd, uri=None, mode='r',
             validate_checksums=False,
             tag_to_schema_resolver=None,
             url_mapping=None,
             type_index=None,
             _get_yaml_content=False):
        """
        Open an existing ASDF file.

        Parameters
        ----------
        fd : string or file-like object
            May be a string ``file`` or ``http`` URI, or a Python
            file-like object.

        uri : string, optional
            The URI of the file.  Only required if the URI can not be
            automatically determined from `fd`.

        mode : string, optional
            The mode to open the file in.  Must be ``r`` (default) or
            ``rw``.

        validate_checksums : bool, optional
            If `True`, validate the blocks against their checksums.
            Requires reading the entire file, so disabled by default.

        Other Parameters
        ----------------
        **kwargs : extra parameters
            See `pyasdf.AsdfFile` for a description of the other
            parameters.

        Returns
        -------
        asdffile : AsdfFile
            The new AsdfFile object.
        """
        fd = generic_io.get_file(fd, mode=mode, uri=uri)

        self = cls(
            tag_to_schema_resolver=tag_to_schema_resolver,
            url_mapping=url_mapping,
            type_index=type_index)
        self._fd = fd

        try:
            header_line = fd.read_until(b'\r?\n', "newline", include=True)
        except ValueError:
            raise ValueError("Does not appear to be a ASDF file.")
        self.version = cls._parse_header_line(header_line)

        yaml_token = fd.read(4)
        yaml_content = b''
        has_blocks = False
        if yaml_token == b'%YAM':
            # The yaml content is read now, but we parse it after finding
            # all of the blocks, so that arrays can be resolved to their
            # blocks immediately.
            yaml_content = yaml_token + fd.read_until(
                constants.YAML_END_MARKER_REGEX, 'End of YAML marker',
                include=True)
            has_blocks = fd.seek_until(constants.BLOCK_MAGIC, include=True)
        elif yaml_token == constants.BLOCK_MAGIC:
            has_blocks = True
        elif yaml_token != b'':
            raise IOError("ASDF file appears to contain garbage after header.")

        # For testing: just return the raw YAML content
        if _get_yaml_content:
            fd.close()
            return yaml_content

        if has_blocks:
            self._blocks.read_internal_blocks(
                fd, past_magic=True, validate_checksums=validate_checksums)

        if len(yaml_content):
            tree = yamlutil.load_tree(yaml_content, self)
            self.run_hook('post_read')
            self._tree = tree
        else:
            self._tree = {}

        return self

    def _write_tree(self, tree, fd, pad_blocks):
        fd.write(constants.ASDF_MAGIC)
        fd.write(self.version_string.encode('ascii'))
        fd.write(b'\n')

        if len(tree):
            yamlutil.dump_tree(tree, fd, self)

        if pad_blocks:
            padding = util.calculate_padding(
                fd.tell(), pad_blocks, fd.block_size)
            fd.fast_forward(padding)

    def _pre_write(self, fd, all_array_storage, all_array_compression,
                   auto_inline):
        self._all_array_storage = all_array_storage
        self._all_array_compression = all_array_compression
        self._auto_inline = auto_inline

        if len(self._tree):
            self.run_hook('pre_write')

        # This is where we'd do some more sophisticated block
        # reorganization, if necessary
        self._blocks.finalize(self)

    def _serial_write(self, fd, pad_blocks):
        self._write_tree(self._tree, fd, pad_blocks)
        self.blocks.write_internal_blocks_serial(fd, pad_blocks)
        self.blocks.write_external_blocks(fd.uri, pad_blocks)

    def _random_write(self, fd, pad_blocks):
        self._write_tree(self._tree, fd, False)
        self.blocks.write_internal_blocks_random_access(fd)
        self.blocks.write_external_blocks(fd.uri, pad_blocks)

    def _post_write(self, fd):
        if len(self._tree):
            self.run_hook('post_write')

        if hasattr(self, '_all_array_storage'):
            del self._all_array_storage
        if hasattr(self, '_all_array_compression'):
            del self._all_array_compression
        if hasattr(self, '_auto_inline'):
            del self._auto_inline

    def update(self, all_array_storage=None, all_array_compression=None,
               auto_inline=None, pad_blocks=False):
        """
        Update the file on disk in place.

        Parameters
        ----------
        all_array_storage : string, optional
            If provided, override the array storage type of all blocks
            in the file immediately before writing.  Must be one of:

            - ``internal``: The default.  The array data will be
              stored in a binary block in the same ASDF file.

            - ``external``: Store the data in a binary block in a
              separate ASDF file.

            - ``inline``: Store the data as YAML inline in the tree.

        all_array_compression : string, optional
            If provided, set the compression type on all binary blocks
            in the file.  Must be one of:

            - ``''``: No compression.

            - ``zlib``: Use zlib compression.

        auto_inline : int, optional
            When the number of elements in an array is less than this
            threshold, store the array as inline YAML, rather than a
            binary block.  This only works on arrays that do not share
            data with other arrays.  Default is 0.

        pad_blocks : float or bool, optional
            Add extra space between blocks to allow for updating of
            the file.  If `False` (default), add no padding (always
            return 0).  If `True`, add a default amount of padding of
            10% If a float, it is a factor to multiple content_size by
            to get the new total size.
        """
        fd = self._fd

        if fd is None:
            raise ValueError(
                "Can not update, since there is no associated file")
        if not fd.writable():
            raise IOError(
                "Can not update, since associated file is read-only")
        if all_array_storage == 'external':
            # If the file is fully exploded, there's no benefit to
            # update, so just use write_to()
            self.write_to(fd, all_array_storage=all_array_storage)
            fd.truncate(fd.tell())
            return
        if not fd.seekable():
            raise IOError(
                "Can not update, since associated file is not seekable")

        self._pre_write(fd, all_array_storage, all_array_compression,
                        auto_inline)

        try:
            fd.seek(0)

            if not self.blocks.has_blocks_with_offset():
                # If we don't have any blocks that are being reused, just
                # write out in a serial fashion.
                self._serial_write(fd, pad_blocks)
                fd.truncate(fd.tell())
                return

            # Estimate how big the tree will be on disk by writing the
            # YAML out in memory.  Since the block indices aren't yet
            # known, we have to count the number of block references and
            # add enough space to accommodate the largest block number
            # possible there.
            tree_serialized = io.BytesIO()
            self._write_tree(self._tree, tree_serialized, pad_blocks=False)
            array_ref_count = [0]
            from .tags.core.ndarray import NDArrayType

            def count_external_array_references(node):
                if (isinstance(node, (np.ndarray, NDArrayType)) and
                    self.blocks[node].array_storage == 'internal'):
                    array_ref_count[0] += 1
            treeutil.walk(self._tree, count_external_array_references)

            serialized_tree_size = (
                tree_serialized.tell() +
                constants.MAX_BLOCKS_DIGITS * array_ref_count[0])

            if not block.calculate_updated_layout(
                    self.blocks, serialized_tree_size,
                    pad_blocks, fd.block_size):
                # If we don't have any blocks that are being reused, just
                # write out in a serial fashion.
                self._serial_write(fd, pad_blocks)
                fd.truncate(fd.tell())
                return

            fd.seek(0)
            self._random_write(fd, pad_blocks)
            fd.flush()
        finally:
            self._post_write(fd)

    def write_to(self, fd, all_array_storage=None, all_array_compression=None,
                 auto_inline=None, pad_blocks=False):
        """
        Write the ASDF file to the given file-like object.

        Parameters
        ----------
        fd : string or file-like object
            May be a string path to a file, or a Python file-like
            object.

        all_array_storage : string, optional
            If provided, override the array storage type of all blocks
            in the file immediately before writing.  Must be one of:

            - ``internal``: The default.  The array data will be
              stored in a binary block in the same ASDF file.

            - ``external``: Store the data in a binary block in a
              separate ASDF file.

            - ``inline``: Store the data as YAML inline in the tree.

        all_array_compression : string, optional
            If provided, set the compression type on all binary blocks
            in the file.  Must be one of:

            - ``''``: No compression.

            - ``zlib``: Use zlib compression.

        auto_inline : int, optional
            When the number of elements in an array is less than this
            threshold, store the array as inline YAML, rather than a
            binary block.  This only works on arrays that do not share
            data with other arrays.  Default is 0.

        pad_blocks : float or bool, optional
            Add extra space between blocks to allow for updating of
            the file.  If `False` (default), add no padding (always
            return 0).  If `True`, add a default amount of padding of
            10% If a float, it is a factor to multiple content_size by
            to get the new total size.
        """
        original_fd = self._fd

        self._fd = fd = generic_io.get_file(fd, mode='w')

        self._pre_write(fd, all_array_storage, all_array_compression,
                        auto_inline)

        try:
            self._serial_write(fd, pad_blocks)
            fd.flush()
        finally:
            self._post_write(fd)

        if original_fd is not None:
            original_fd.close()

        return self

    def write_to_stream(self, data):
        """
        Append additional data to the end of the `AsdfFile` for
        stream-writing.

        See `pyasdf.Stream`.
        """
        if self.blocks.streamed_block is None:
            raise ValueError("AsdfFile has no streamed block to write to")
        self._fd.write(data)

    def find_references(self):
        """
        Finds all external "JSON References" in the tree and converts
        them to `reference.Reference` objects.
        """
        self.tree = reference.find_references(self.tree, self)

    def resolve_references(self):
        """
        Finds all external "JSON References" in the tree, loads the
        external content, and places it directly in the tree.  Saving
        a ASDF file after this operation means it will have no
        external references, and will be completely self-contained.
        """
        tree = reference.resolve_references(self.tree, self)
        self.tree = tree

    def run_hook(self, hookname):
        """
        Run a "hook" for each custom type found in the tree.

        Parameters
        ----------
        hookname : str
            The name of the hook.  If a `AsdfType` is found with a method
            with this name, it will be called for every instance of the
            corresponding custom type in the tree.
        """
        def walker(node):
            tag = self.type_index.from_custom_type(type(node))
            if tag is not None:
                hook = getattr(tag, hookname, None)
                if hook is not None:
                    hook(node, self)
        return treeutil.walk(self.tree, walker)

    def run_modifying_hook(self, hookname):
        """
        Run a "hook" for each custom type found in the tree.  The hook
        is free to return a different object in order to modify the
        tree.

        Parameters
        ----------
        hookname : str
            The name of the hook.  If a `AsdfType` is found with a method
            with this name, it will be called for every instance of the
            corresponding custom type in the tree.
        """
        def walker(node):
            tag = self.type_index.from_custom_type(type(node))
            if tag is not None:
                hook = getattr(tag, hookname, None)
                if hook is not None:
                    return hook(node, self)
            return node
        self.tree = treeutil.walk_and_modify(self.tree, walker)
        return self.tree

    def resolve_and_inline(self):
        """
        Resolves all external references and inlines all data.  This
        produces something that, when saved, is a 100% valid YAML
        file.
        """
        self.resolve_references()
        for b in self.blocks.blocks:
            b.array_storage = 'inline'
