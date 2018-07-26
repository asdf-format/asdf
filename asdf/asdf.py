# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io
import os
import time
import re
import copy
import datetime
import warnings
import importlib
from distutils.version import LooseVersion

import numpy as np
from jsonschema import ValidationError

from . import block
from . import constants
from . import generic_io
from . import reference
from . import schema
from . import treeutil
from . import util
from . import version
from . import versioning
from . import yamlutil
from .exceptions import AsdfDeprecationWarning
from .extension import AsdfExtensionList, default_extensions

from .tags.core import AsdfObject, Software, HistoryEntry, ExtensionMetadata


def get_asdf_library_info():
    """
    Get information about asdf to include in the asdf_library entry
    in the Tree.
    """
    return Software({
        'name': 'asdf',
        'version': version.version,
        'homepage': 'http://github.com/spacetelescope/asdf',
        'author': 'Space Telescope Science Institute'
    })


class AsdfFile(versioning.VersionedMixin):
    """
    The main class that represents an ASDF file object.
    """
    def __init__(self, tree=None, uri=None, extensions=None, version=None,
        ignore_version_mismatch=True, ignore_unrecognized_tag=False,
        copy_arrays=False, custom_schema=None):
        """
        Parameters
        ----------
        tree : dict or AsdfFile, optional
            The main tree data in the ASDF file.  Must conform to the
            ASDF schema.

        uri : str, optional
            The URI for this ASDF file.  Used to resolve relative
            references against.  If not provided, will be
            automatically determined from the associated file object,
            if possible and if created from `AsdfFile.open`.

        extensions : list of AsdfExtension
            A list of extensions to use when reading and writing ASDF files.
            See `~asdf.asdftypes.AsdfExtension` for more information.

        version : str, optional
            The ASDF version to use when writing out.  If not
            provided, it will write out in the latest version
            supported by asdf.

        ignore_version_mismatch : bool, optional
            When `True`, do not raise warnings for mismatched schema versions.
            Set to `True` by default.

        ignore_unrecognized_tag : bool, optional
            When `True`, do not raise warnings for unrecognized tags. Set to
            `False` by default.

        copy_arrays : bool, optional
            When `False`, when reading files, attempt to memmap underlying data
            arrays when possible.

        custom_schema : str, optional
            Path to a custom schema file that will be used for a secondary
            validation pass. This can be used to ensure that particular ASDF
            files follow custom conventions beyond those enforced by the
            standard.
        """

        if custom_schema is not None:
            self._custom_schema = schema.load_custom_schema(custom_schema)
            schema.check_schema(self._custom_schema)
        else:
            self._custom_schema = None

        self._extensions = []
        self._extension_metadata = {}

        self._process_extensions(extensions)
        self._ignore_version_mismatch = ignore_version_mismatch
        self._ignore_unrecognized_tag = ignore_unrecognized_tag

        self._file_format_version = None

        self._fd = None
        self._closed = False
        self._external_asdf_by_uri = {}
        self._blocks = block.BlockManager(self, copy_arrays=copy_arrays)
        self._uri = None
        if tree is None:
            self.tree = {}
        elif isinstance(tree, AsdfFile):
            if self._extensions != tree._extensions:
                raise ValueError(
                    "Can not copy AsdfFile and change active extensions")
            self._uri = tree.uri
            # Set directly to self._tree (bypassing property), since
            # we can assume the other AsdfFile is already valid.
            self._tree = tree.tree
            self.run_modifying_hook('copy_to_new_asdf', validate=False)
            self.find_references()
        else:
            self.tree = tree
            self.find_references()
        if uri is not None:
            self._uri = uri

        self._comments = []

        if version is not None:
            self.version = version

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _check_extensions(self, tree, strict=False):
        if 'history' not in tree or not isinstance(tree['history'], dict) or \
                'extensions' not in tree['history']:
            return

        for extension in tree['history']['extensions']:
            filename = "'{}' ".format(self._fname) if self._fname else ''
            if extension.extension_class not in self._extension_metadata:
                msg = "File {}was created with extension '{}', which is " \
                    "not currently installed"
                if extension.software:
                    msg += " (from package {}-{})".format(
                        extension.software['name'],
                        extension.software['version'])
                fmt_msg = msg.format(filename, extension.extension_class)
                if strict:
                    raise RuntimeError(fmt_msg)
                else:
                    warnings.warn(fmt_msg)

            elif extension.software:
                installed = self._extension_metadata[extension.extension_class]
                # Local extensions may not have a real version
                if not installed[1]:
                    continue
                # Compare version in file metadata with installed version
                if LooseVersion(installed[1]) < LooseVersion(extension.software['version']):
                    msg = "File {}was created with extension '{}' from " \
                    "package {}-{}, but older version {}-{} is installed"
                    fmt_msg = msg.format(
                        filename, extension.extension_class,
                        extension.software['name'],
                        extension.software['version'],
                        installed[0], installed[1])
                    if strict:
                        raise RuntimeError(fmt_msg)
                    else:
                        warnings.warn(fmt_msg)

    def _process_extensions(self, extensions):
        if extensions is None or extensions == []:
            self._extensions = default_extensions.extension_list
            self._extension_metadata = default_extensions.package_metadata
            return

        if isinstance(extensions, AsdfExtensionList):
            self._extensions = extensions
            return

        if not isinstance(extensions, list):
            extensions = [extensions]

        # Process metadata about custom extensions
        for extension in extensions:
            ext_name = util.get_class_name(extension)
            self._extension_metadata[ext_name] = ('', '')

        extensions = default_extensions.extensions + extensions
        self._extensions = AsdfExtensionList(extensions)
        self._extension_metadata.update(default_extensions.package_metadata)

    def _update_extension_history(self):

        if 'history' not in self.tree:
            self.tree['history'] = dict(extensions=[])
        # Support clients who are still using the old history format
        elif isinstance(self.tree['history'], list):
            histlist = self.tree['history']
            self.tree['history'] = dict(entries=histlist, extensions=[])
            warnings.warn("The ASDF history format has changed in order to "
                          "support metadata about extensions. History entries "
                          "should now be stored under tree['history']['entries'].")
        elif 'extensions' not in self.tree['history']:
            self.tree['history']['extensions'] = []

        for extension in self.type_index.get_extensions_used():
            ext_name = util.get_class_name(extension)
            ext_meta = ExtensionMetadata(extension_class=ext_name)
            metadata = self._extension_metadata.get(ext_name)
            if metadata is not None:
                ext_meta.software = dict(name=metadata[0], version=metadata[1])

            for i, entry in enumerate(self.tree['history']['extensions']):
                # Update metadata about this extension if it already exists
                if entry.extension_class == ext_meta.extension_class:
                    self.tree['history']['extensions'][i] = ext_meta
                    break
            else:
                self.tree['history']['extensions'].append(ext_meta)

    @property
    def file_format_version(self):
        if self._file_format_version is None:
            return versioning.AsdfVersion(self.version_map['FILE_FORMAT'])
        else:
            return self._file_format_version

    def close(self):
        """
        Close the file handles associated with the `AsdfFile`.
        """
        if self._fd and not self._closed:
            # This is ok to always do because GenericFile knows
            # whether it "owns" the file and should close it.
            self._fd.close()
            self._fd = None
            self._closed = True
        for external in self._external_asdf_by_uri.values():
            external.close()
        self._external_asdf_by_uri.clear()
        self._blocks.close()

    def copy(self):
        return self.__class__(
            copy.deepcopy(self._tree),
            self._uri,
            self._extensions
        )

    __copy__ = __deepcopy__ = copy

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
        warnings.warn(
            "The 'tag_to_schema_resolver' property is deprecated. Use "
            "'tag_mapping' instead.",
            AsdfDeprecationWarning)
        return self._extensions.tag_mapping

    @property
    def tag_mapping(self):
        return self._extensions.tag_mapping

    @property
    def url_mapping(self):
        return self._extensions.url_mapping

    def resolver(self, uri):
        return self.url_mapping(self.tag_mapping(uri))

    @property
    def type_index(self):
        return self._extensions.type_index

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

    def open_external(self, uri, do_not_fill_defaults=False):
        """
        Open an external ASDF file, from the given (possibly relative)
        URI.  There is a cache (internal to this ASDF file) that ensures
        each external ASDF file is loaded only once.

        Parameters
        ----------
        uri : str
            An absolute or relative URI to resolve against the URI of
            this ASDF file.

        do_not_fill_defaults : bool, optional
            When `True`, do not fill in missing default values.

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
            asdffile = self.open(
                resolved_uri,
                do_not_fill_defaults=do_not_fill_defaults)
            self._external_asdf_by_uri[resolved_uri] = asdffile
        return asdffile

    @property
    def tree(self):
        """
        Get/set the tree of data in the ASDF file.

        When set, the tree will be validated against the ASDF schema.
        """
        if self._closed:
            raise OSError("Cannot access data from closed ASDF file")
        return self._tree

    @tree.setter
    def tree(self, tree):
        asdf_object = AsdfObject(tree)
        # Only perform custom validation if the tree is not empty
        self._validate(asdf_object, custom=bool(tree))
        self._tree = asdf_object

    def __getitem__(self, key):
        return self._tree[key]

    def __setitem__(self, key, value):
        self._tree[key] = value

    @property
    def comments(self):
        """
        Get the comments after the header, before the tree.
        """
        return self._comments

    def _validate(self, tree, custom=True):
        tagged_tree = yamlutil.custom_tree_to_tagged_tree(
            tree, self)
        schema.validate(tagged_tree, self)
        # Perform secondary validation pass if requested
        if custom and self._custom_schema:
            schema.validate(tagged_tree, self, self._custom_schema)

    def validate(self):
        """
        Validate the current state of the tree against the ASDF schema.
        """
        self._validate(self._tree)

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

            >>> import asdf
            >>> flat = asdf.open("http://stsci.edu/reference_files/flat.asdf")  # doctest: +SKIP
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
        block = self.blocks[arr]
        self.blocks.set_array_storage(block, array_storage)

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

        compression : str or None
            Must be one of:

            - ``''`` or `None`: no compression

            - ``zlib``: Use zlib compression

            - ``bzp2``: Use bzip2 compression

            - ``lz4``: Use lz4 compression

            - ``''`` or `None`: no compression

            - ``input``: Use the same compression as in the file read.
              If there is no prior file, acts as None.

        """
        self.blocks[arr].output_compression = compression

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
        return self.blocks[arr].output_compression

    @classmethod
    def _parse_header_line(cls, line):
        """
        Parses the header line in a ASDF file to obtain the ASDF version.
        """
        parts = line.split()
        if len(parts) != 2 or parts[0] != constants.ASDF_MAGIC:
            raise ValueError("Does not appear to be a ASDF file.")

        try:
            version = versioning.AsdfVersion(parts[1].decode('ascii'))
        except ValueError:
            raise ValueError(
                "Unparseable version in ASDF file: {0}".format(parts[1]))

        return version

    @classmethod
    def _parse_comment_section(cls, content):
        """
        Parses the comment section, between the header line and the
        Tree or first block.
        """
        comments = []

        lines = content.splitlines()
        for line in lines:
            if not line.startswith(b'#'):
                raise ValueError("Invalid content between header and tree")
            comments.append(line[1:].strip())

        return comments

    @classmethod
    def _find_asdf_version_in_comments(cls, comments):
        for comment in comments:
            parts = comment.split()
            if len(parts) == 2 and parts[0] == constants.ASDF_STANDARD_COMMENT:
                try:
                    version = versioning.AsdfVersion(parts[1].decode('ascii'))
                except ValueError:
                    pass
                else:
                    return version

        return None

    @classmethod
    def _open_asdf(cls, self, fd, uri=None, mode='r',
                   validate_checksums=False,
                   do_not_fill_defaults=False,
                   _get_yaml_content=False,
                   _force_raw_types=False,
                   strict_extension_check=False,
                   ignore_missing_extensions=False):
        """Attempt to populate AsdfFile data from file-like object"""

        if strict_extension_check and ignore_missing_extensions:
            raise ValueError(
                "'strict_extension_check' and 'ignore_missing_extensions' are "
                "incompatible options")

        fd = generic_io.get_file(fd, mode=mode, uri=uri)
        self._fd = fd
        # The filename is currently only used for tracing warning information
        self._fname = self._fd._uri if self._fd._uri else ''
        header_line = fd.read_until(b'\r?\n', 2, "newline", include=True)
        self._file_format_version = cls._parse_header_line(header_line)
        self.version = self._file_format_version

        comment_section = fd.read_until(
            b'(%YAML)|(' + constants.BLOCK_MAGIC + b')', 5,
            "start of content", include=False, exception=False)
        self._comments = cls._parse_comment_section(comment_section)

        version = cls._find_asdf_version_in_comments(self._comments)
        if version is not None:
            self.version = version

        yaml_token = fd.read(4)
        tree = {}
        has_blocks = False
        if yaml_token == b'%YAM':
            reader = fd.reader_until(
                constants.YAML_END_MARKER_REGEX, 7, 'End of YAML marker',
                include=True, initial_content=yaml_token)

            # For testing: just return the raw YAML content
            if _get_yaml_content:
                yaml_content = reader.read()
                fd.close()
                return yaml_content

            # We parse the YAML content into basic data structures
            # now, but we don't do anything special with it until
            # after the blocks have been read
            tree = yamlutil.load_tree(reader, self, self._ignore_version_mismatch)
            has_blocks = fd.seek_until(constants.BLOCK_MAGIC, 4, include=True)
        elif yaml_token == constants.BLOCK_MAGIC:
            has_blocks = True
        elif yaml_token != b'':
            raise IOError("ASDF file appears to contain garbage after header.")

        if has_blocks:
            self._blocks.read_internal_blocks(
                fd, past_magic=True, validate_checksums=validate_checksums)
            self._blocks.read_block_index(fd, self)

        tree = reference.find_references(tree, self)
        if not do_not_fill_defaults:
            schema.fill_defaults(tree, self)

        try:
            self._validate(tree)
        except ValidationError:
            self.close()
            raise

        tree = yamlutil.tagged_tree_to_custom_tree(tree, self, _force_raw_types)

        if not (ignore_missing_extensions or _force_raw_types):
            self._check_extensions(tree, strict=strict_extension_check)

        self._tree = tree
        self.run_hook('post_read')

        return self

    @classmethod
    def _open_impl(cls, self, fd, uri=None, mode='r',
                   validate_checksums=False,
                   do_not_fill_defaults=False,
                   _get_yaml_content=False,
                   _force_raw_types=False,
                   strict_extension_check=False,
                   ignore_missing_extensions=False):
        """Attempt to open file-like object as either AsdfFile or AsdfInFits"""
        if not is_asdf_file(fd):
            try:
                # TODO: this feels a bit circular, try to clean up. Also
                # this introduces another dependency on astropy which may
                # not be desireable.
                from . import fits_embed
                return fits_embed.AsdfInFits._open_impl(fd, uri=uri,
                            validate_checksums=validate_checksums,
                            ignore_version_mismatch=self._ignore_version_mismatch,
                            extensions=self._extensions,
                            strict_extension_check=strict_extension_check,
                            ignore_missing_extensions=ignore_missing_extensions,
                            _extension_metadata=self._extension_metadata)
            except ValueError:
                pass
            raise ValueError(
                "Input object does not appear to be ASDF file or FITS with " +
                "ASDF extension")
        return cls._open_asdf(self, fd, uri=uri, mode=mode,
                validate_checksums=validate_checksums,
                do_not_fill_defaults=do_not_fill_defaults,
                _get_yaml_content=_get_yaml_content,
                _force_raw_types=_force_raw_types,
                strict_extension_check=strict_extension_check,
                ignore_missing_extensions=ignore_missing_extensions)

    @classmethod
    def open(cls, fd, uri=None, mode='r',
             validate_checksums=False,
             extensions=None,
             do_not_fill_defaults=False,
             ignore_version_mismatch=True,
             ignore_unrecognized_tag=False,
             _force_raw_types=False,
             copy_arrays=False,
             custom_schema=None,
             strict_extension_check=False,
             ignore_missing_extensions=False):
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

        extensions : list of AsdfExtension
            A list of extensions to use when reading and writing ASDF files.
            See `~asdf.asdftypes.AsdfExtension` for more information.

        do_not_fill_defaults : bool, optional
            When `True`, do not fill in missing default values.

        ignore_version_mismatch : bool, optional
            When `True`, do not raise warnings for mismatched schema versions.
            Set to `True` by default.

        ignore_unrecognized_tag : bool, optional
            When `True`, do not raise warnings for unrecognized tags. Set to
            `False` by default.

        copy_arrays : bool, optional
            When `False`, when reading files, attempt to memmap underlying data
            arrays when possible.

        custom_schema : str, optional
            Path to a custom schema file that will be used for a secondary
            validation pass. This can be used to ensure that particular ASDF
            files follow custom conventions beyond those enforced by the
            standard.

        strict_extension_check : bool, optional
            When `True`, if the given ASDF file contains metadata about the
            extensions used to create it, and if those extensions are not
            installed, opening the file will fail. When `False`, opening a file
            under such conditions will cause only a warning. Defaults to
            `False`.

        ignore_missing_extensions : bool, optional
            When `True`, do not raise warnings when a file is read that
            contains metadata about extensions that are not available. Defaults
            to `False`.

        Returns
        -------
        asdffile : AsdfFile
            The new AsdfFile object.
        """
        self = cls(extensions=extensions,
                   ignore_version_mismatch=ignore_version_mismatch,
                   ignore_unrecognized_tag=ignore_unrecognized_tag,
                   copy_arrays=copy_arrays, custom_schema=custom_schema)

        return cls._open_impl(
            self, fd, uri=uri, mode=mode,
            validate_checksums=validate_checksums,
            do_not_fill_defaults=do_not_fill_defaults,
            _force_raw_types=_force_raw_types,
            strict_extension_check=strict_extension_check,
            ignore_missing_extensions=ignore_missing_extensions)

    def _write_tree(self, tree, fd, pad_blocks):
        fd.write(constants.ASDF_MAGIC)
        fd.write(b' ')
        fd.write(self.version_map['FILE_FORMAT'].encode('ascii'))
        fd.write(b'\n')

        fd.write(b'#')
        fd.write(constants.ASDF_STANDARD_COMMENT)
        fd.write(b' ')
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
        if all_array_storage not in (None, 'internal', 'external', 'inline'):
            raise ValueError(
                "Invalid value for all_array_storage: '{0}'".format(
                    all_array_storage))
        self._all_array_storage = all_array_storage

        self._all_array_compression = all_array_compression

        if auto_inline in (True, False):
            raise ValueError(
                "Invalid value for auto_inline: '{0}'".format(auto_inline))
        if auto_inline is not None:
            try:
                self._auto_inline = int(auto_inline)
            except ValueError:
                raise ValueError(
                    "Invalid value for auto_inline: '{0}'".format(auto_inline))
        else:
            self._auto_inline = None

        if len(self._tree):
            self.run_hook('pre_write')

        # This is where we'd do some more sophisticated block
        # reorganization, if necessary
        self._blocks.finalize(self)

        self._tree['asdf_library'] = get_asdf_library_info()

    def _serial_write(self, fd, pad_blocks, include_block_index):
        self._write_tree(self._tree, fd, pad_blocks)
        self.blocks.write_internal_blocks_serial(fd, pad_blocks)
        self.blocks.write_external_blocks(fd.uri, pad_blocks)
        if include_block_index:
            self.blocks.write_block_index(fd, self)

    def _random_write(self, fd, pad_blocks, include_block_index):
        self._write_tree(self._tree, fd, False)
        self.blocks.write_internal_blocks_random_access(fd)
        self.blocks.write_external_blocks(fd.uri, pad_blocks)
        if include_block_index:
            self.blocks.write_block_index(fd, self)
        fd.truncate()

    def _post_write(self, fd):
        if len(self._tree):
            self.run_hook('post_write')

        if hasattr(self, '_all_array_storage'):
            del self._all_array_storage
        if hasattr(self, '_all_array_compression'):
            del self._all_array_compression
        if hasattr(self, '_auto_inline'):
            del self._auto_inline

    def update(self, all_array_storage=None, all_array_compression='input',
               auto_inline=None, pad_blocks=False, include_block_index=True,
               version=None):
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

            - ``''`` or `None`: No compression.

            - ``zlib``: Use zlib compression.

            - ``bzp2``: Use bzip2 compression.

            - ``lz4``: Use lz4 compression.

            - ``input``: Use the same compression as in the file read.
              If there is no prior file, acts as None

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

        include_block_index : bool, optional
            If `False`, don't include a block index at the end of the
            file.  (Default: `True`)  A block index is never written
            if the file has a streamed block.

        version : str, optional
            The ASDF version to write out.  If not provided, it will
            write out in the latest version supported by asdf.
        """

        self._update_extension_history()

        fd = self._fd

        if fd is None:
            raise ValueError(
                "Can not update, since there is no associated file")

        if not fd.writable():
            raise IOError(
                "Can not update, since associated file is read-only")

        if version is not None:
            self.version = version

        if all_array_storage == 'external':
            # If the file is fully exploded, there's no benefit to
            # update, so just use write_to()
            self.write_to(fd, all_array_storage=all_array_storage)
            fd.truncate()
            return

        if not fd.seekable():
            raise IOError(
                "Can not update, since associated file is not seekable")

        self.blocks.finish_reading_internal_blocks()

        self._pre_write(fd, all_array_storage, all_array_compression,
                        auto_inline)

        try:
            fd.seek(0)

            if not self.blocks.has_blocks_with_offset():
                # If we don't have any blocks that are being reused, just
                # write out in a serial fashion.
                self._serial_write(fd, pad_blocks, include_block_index)
                fd.truncate()
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

            for node in treeutil.iter_tree(self._tree):
                if (isinstance(node, (np.ndarray, NDArrayType)) and
                    self.blocks[node].array_storage == 'internal'):
                    array_ref_count[0] += 1

            serialized_tree_size = (
                tree_serialized.tell() +
                constants.MAX_BLOCKS_DIGITS * array_ref_count[0])

            if not block.calculate_updated_layout(
                    self.blocks, serialized_tree_size,
                    pad_blocks, fd.block_size):
                # If we don't have any blocks that are being reused, just
                # write out in a serial fashion.
                self._serial_write(fd, pad_blocks, include_block_index)
                fd.truncate()
                return

            fd.seek(0)
            self._random_write(fd, pad_blocks, include_block_index)
            fd.flush()
        finally:
            self._post_write(fd)

    def write_to(self, fd, all_array_storage=None, all_array_compression='input',
                 auto_inline=None, pad_blocks=False, include_block_index=True,
                 version=None):
        """
        Write the ASDF file to the given file-like object.

        `write_to` does not change the underlying file descriptor in
        the `AsdfFile` object, but merely copies the content to a new
        file.

        Parameters
        ----------
        fd : string or file-like object
            May be a string path to a file, or a Python file-like
            object.  If a string path, the file is automatically
            closed after writing.  If not a string path,

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

            - ``''`` or `None`: No compression.

            - ``zlib``: Use zlib compression.

            - ``bzp2``: Use bzip2 compression.

            - ``lz4``: Use lz4 compression.

            - ``input``: Use the same compression as in the file read.
              If there is no prior file, acts as None.

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

        include_block_index : bool, optional
            If `False`, don't include a block index at the end of the
            file.  (Default: `True`)  A block index is never written
            if the file has a streamed block.

        version : str, optional
            The ASDF version to write out.  If not provided, it will
            write out in the latest version supported by asdf.
        """

        self._update_extension_history()

        original_fd = self._fd

        if version is not None:
            self.version = version

        try:
            with generic_io.get_file(fd, mode='w') as fd:
                self._fd = fd
                self._pre_write(fd, all_array_storage, all_array_compression,
                                auto_inline)

                try:
                    self._serial_write(fd, pad_blocks, include_block_index)
                    fd.flush()
                finally:
                    self._post_write(fd)
        finally:
            self._fd = original_fd

    def find_references(self):
        """
        Finds all external "JSON References" in the tree and converts
        them to `reference.Reference` objects.
        """
        # Set directly to self._tree, since it doesn't need to be
        # re-validated.
        self._tree = reference.find_references(self._tree, self)

    def resolve_references(self, do_not_fill_defaults=False):
        """
        Finds all external "JSON References" in the tree, loads the
        external content, and places it directly in the tree.  Saving
        a ASDF file after this operation means it will have no
        external references, and will be completely self-contained.
        """
        # Set to the property self.tree so the resulting "complete"
        # tree will be validated.
        self.tree = reference.resolve_references(self._tree, self)

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
        type_index = self.type_index

        if not type_index.has_hook(hookname):
            return

        for node in treeutil.iter_tree(self._tree):
            hook = type_index.get_hook_for_type(hookname, type(node),
                                                self.version_string)
            if hook is not None:
                hook(node, self)

    def run_modifying_hook(self, hookname, validate=True):
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

        validate : bool
            When `True` (default) validate the resulting tree.
        """
        type_index = self.type_index

        if not type_index.has_hook(hookname):
            return

        def walker(node):
            hook = type_index.get_hook_for_type(hookname, type(node),
                                                self.version_string)
            if hook is not None:
                return hook(node, self)
            return node
        tree = treeutil.walk_and_modify(self.tree, walker)

        if validate:
            self._validate(tree)
        self._tree = tree
        return self._tree

    def resolve_and_inline(self):
        """
        Resolves all external references and inlines all data.  This
        produces something that, when saved, is a 100% valid YAML
        file.
        """
        self.blocks.finish_reading_internal_blocks()
        self.resolve_references()
        for b in list(self.blocks.blocks):
            self.blocks.set_array_storage(b, 'inline')

    def fill_defaults(self):
        """
        Fill in any values that are missing in the tree using default
        values from the schema.
        """
        tree = yamlutil.custom_tree_to_tagged_tree(self._tree, self)
        schema.fill_defaults(tree, self)
        self._tree = yamlutil.tagged_tree_to_custom_tree(tree, self)

    def remove_defaults(self):
        """
        Remove any values in the tree that are the same as the default
        values in the schema
        """
        tree = yamlutil.custom_tree_to_tagged_tree(self._tree, self)
        schema.remove_defaults(tree, self)
        self._tree = yamlutil.tagged_tree_to_custom_tree(tree, self)

    def add_history_entry(self, description, software=None):
        """
        Add an entry to the history list.

        Parameters
        ----------
        description : str
            A description of the change.

        software : dict or list of dict
            A description of the software used.  It should not include
            asdf itself, as that is automatically notated in the
            `asdf_library` entry.

            Each dict must have the following keys:

            - ``name``: The name of the software
            - ``author``: The author or institution that produced the software
            - ``homepage``: A URI to the homepage of the software
            - ``version``: The version of the software
        """
        if isinstance(software, list):
            software = [Software(x) for x in software]
        elif software is not None:
            software = Software(software)

        time_ = datetime.datetime.utcfromtimestamp(
            int(os.environ.get('SOURCE_DATE_EPOCH', time.time())),
        )

        entry = HistoryEntry({
            'description': description,
            'time': time_,
        })

        if software is not None:
            entry['software'] = software

        if 'history' not in self.tree:
            self.tree['history'] = dict(entries=[])

        self.tree['history']['entries'].append(entry)

        try:
            self.validate()
        except:
            self.tree['history']['entries'].pop()
            raise


def is_asdf_file(fd):
    """
    Determine if fd is an ASDF file.

    Reads the first five bytes and looks for the ``#ASDF`` string.

    Parameters
    ----------
    fd : str, `~asdf.generic_io.GenericFile`

    """
    if isinstance(fd, generic_io.InputStream):
        # If it's an InputStream let ASDF deal with it.
        return True

    to_close = False
    if isinstance(fd, AsdfFile):
        return True
    elif isinstance(fd, generic_io.GenericFile):
        pass
    else:
        try:
            fd = generic_io.get_file(fd, mode='r', uri=None)
            if not isinstance(fd, io.IOBase):
                to_close = True
        except ValueError:
            return False
    asdf_magic = fd.read(5)
    if fd.seekable():
        fd.seek(0)
    if to_close:
        fd.close()
    if asdf_magic == constants.ASDF_MAGIC:
        return True
    return False
