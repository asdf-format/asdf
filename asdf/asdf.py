# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-


import io
import os
import time
import copy
import datetime
import warnings
from pkg_resources import parse_version

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
from . import _display as display
from .exceptions import AsdfDeprecationWarning
from .extension import AsdfExtensionList, default_extensions
from .util import NotSet
from .search import AsdfSearchResult

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
                 ignore_implicit_conversion=False, copy_arrays=False,
                 lazy_load=True, custom_schema=None, _readonly=False):
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
            See `~asdf.types.AsdfExtension` for more information.

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

        ignore_implicit_conversion : bool
            When `True`, do not raise warnings when types in the tree are
            implicitly converted into a serializable object. The motivating
            case for this is currently `namedtuple`, which cannot be serialized
            as-is.

        copy_arrays : bool, optional
            When `False`, when reading files, attempt to memmap underlying data
            arrays when possible.

        lazy_load : bool, optional
            When `True` and the underlying file handle is seekable, data
            arrays will only be loaded lazily: i.e. when they are accessed
            for the first time. In this case the underlying file must stay
            open during the lifetime of the tree. Setting to False causes
            all data arrays to be loaded up front, which means that they
            can be accessed even after the underlying file is closed.
            Note: even if `lazy_load` is `False`, `copy_arrays` is still taken
            into account.

        custom_schema : str, optional
            Path to a custom schema file that will be used for a secondary
            validation pass. This can be used to ensure that particular ASDF
            files follow custom conventions beyond those enforced by the
            standard.

        """
        self._extensions = []
        self._extension_metadata = {}
        self._process_extensions(extensions)

        if custom_schema is not None:
            self._custom_schema = schema._load_schema_cached(custom_schema, self.resolver, True, False)
        else:
            self._custom_schema = None

        self._ignore_version_mismatch = ignore_version_mismatch
        self._ignore_unrecognized_tag = ignore_unrecognized_tag
        self._ignore_implicit_conversion = ignore_implicit_conversion

        self._file_format_version = None

        # Context of a call to treeutil.walk_and_modify, needed in the AsdfFile
        # in case walk_and_modify is re-entered by extension code (via
        # custom_tree_to_tagged_tree or tagged_tree_to_custom_tree).
        self._tree_modification_context = treeutil._TreeModificationContext()

        self._fd = None
        self._closed = False
        self._external_asdf_by_uri = {}
        self._blocks = block.BlockManager(
            self, copy_arrays=copy_arrays, lazy_load=lazy_load,
            readonly=_readonly)
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
                if parse_version(installed[1]) < parse_version(extension.software['version']):
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
        if self.version < versioning.NEW_HISTORY_FORMAT_MIN_VERSION:
            return

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
                ext_meta.software = Software(name=metadata[0], version=metadata[1])

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

    @property
    def resolver(self):
        return self._extensions.resolver

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
            asdffile = open_asdf(
                resolved_uri,
                mode='r', do_not_fill_defaults=do_not_fill_defaults)
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

    def keys(self):
        return self.tree.keys()

    def __getitem__(self, key):
        return self.tree[key]

    def __setitem__(self, key, value):
        self.tree[key] = value

    def __contains__(self, item):
        return item in self.tree

    @property
    def comments(self):
        """
        Get the comments after the header, before the tree.
        """
        return self._comments

    def _validate(self, tree, custom=True, reading=False):
        if reading:
            # If we're validating on read then the tree
            # is already guaranteed to be in tagged form.
            tagged_tree = tree
        else:
            tagged_tree = yamlutil.custom_tree_to_tagged_tree(
                tree, self)
        schema.validate(tagged_tree, self, reading=reading)
        # Perform secondary validation pass if requested
        if custom and self._custom_schema:
            schema.validate(tagged_tree, self, self._custom_schema,
                            reading=reading)

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
                   ignore_missing_extensions=False,
                   validate_on_read=True):
        """Attempt to populate AsdfFile data from file-like object"""

        if strict_extension_check and ignore_missing_extensions:
            raise ValueError(
                "'strict_extension_check' and 'ignore_missing_extensions' are "
                "incompatible options")

        self._mode = mode

        fd = generic_io.get_file(fd, mode=self._mode, uri=uri)
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
            schema.fill_defaults(tree, self, reading=True)

        if validate_on_read:
            try:
                self._validate(tree, reading=True)
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
                   ignore_missing_extensions=False,
                   validate_on_read=True):
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
                            ignore_unrecognized_tag=self._ignore_unrecognized_tag,
                            _extension_metadata=self._extension_metadata,
                            validate_on_read=validate_on_read)
            except ValueError:
                raise ValueError(
                    "Input object does not appear to be an ASDF file or a FITS with " +
                    "ASDF extension") from None
            except ImportError:
                raise ValueError(
                    "Input object does not appear to be an ASDF file. Cannot check " +
                    "if it is a FITS with ASDF extension because 'astropy' is not " +
                    "installed") from None
        return cls._open_asdf(self, fd, uri=uri, mode=mode,
                validate_checksums=validate_checksums,
                do_not_fill_defaults=do_not_fill_defaults,
                _get_yaml_content=_get_yaml_content,
                _force_raw_types=_force_raw_types,
                strict_extension_check=strict_extension_check,
                ignore_missing_extensions=ignore_missing_extensions,
                validate_on_read=validate_on_read)

    @classmethod
    def open(cls, fd, uri=None, mode='r',
             validate_checksums=False,
             extensions=None,
             do_not_fill_defaults=False,
             ignore_version_mismatch=True,
             ignore_unrecognized_tag=False,
             _force_raw_types=False,
             copy_arrays=False,
             lazy_load=True,
             custom_schema=None,
             strict_extension_check=False,
             ignore_missing_extensions=False):
        """
        Open an existing ASDF file.

        .. deprecated:: 2.2
            Use `asdf.open` instead.
        """

        warnings.warn(
            "The method AsdfFile.open has been deprecated and will be removed "
            "in asdf-3.0. Use the top-level asdf.open function instead.",
            AsdfDeprecationWarning)

        return open_asdf(
            fd, uri=uri, mode=mode,
            validate_checksums=validate_checksums,
            extensions=extensions,
            do_not_fill_defaults=do_not_fill_defaults,
            ignore_version_mismatch=ignore_version_mismatch,
            ignore_unrecognized_tag=ignore_unrecognized_tag,
            _force_raw_types=_force_raw_types,
            copy_arrays=copy_arrays, lazy_load=lazy_load,
            custom_schema=custom_schema,
            strict_extension_check=strict_extension_check,
            ignore_missing_extensions=ignore_missing_extensions,
            _compat=True)

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
        self._update_extension_history()

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

        # TODO: there has got to be a better way to do this...
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

        fd = self._fd

        if fd is None:
            raise ValueError(
                "Can not update, since there is no associated file")

        if not fd.writable():
            raise IOError(
                "Can not update, since associated file is read-only. Make "
                "sure that the AsdfFile was opened with mode='rw' and the "
                "underlying file handle is writable.")

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

        if version is not None:
            self.version = version

        with generic_io.get_file(fd, mode='w') as fd:
            # TODO: This is not ideal: we really should pass the URI through
            # explicitly to wherever it is required instead of making it an
            # attribute of the AsdfFile.
            if self._uri is None:
                self._uri = fd.uri
            self._pre_write(fd, all_array_storage, all_array_compression,
                            auto_inline)

            try:
                self._serial_write(fd, pad_blocks, include_block_index)
                fd.flush()
            finally:
                self._post_write(fd)

    def find_references(self):
        """
        Finds all external "JSON References" in the tree and converts
        them to `reference.Reference` objects.
        """
        # Set directly to self._tree, since it doesn't need to be re-validated.
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
        tree = treeutil.walk_and_modify(self.tree, walker,
            ignore_implicit_conversion=self._ignore_implicit_conversion)

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

        if self.version >= versioning.NEW_HISTORY_FORMAT_MIN_VERSION:
            if 'history' not in self.tree:
                self.tree['history'] = dict(entries=[])
            elif 'entries' not in self.tree['history']:
                self.tree['history']['entries'] = []

            self.tree['history']['entries'].append(entry)

            try:
                self.validate()
            except Exception:
                self.tree['history']['entries'].pop()
                raise
        else:
            if 'history' not in self.tree:
                self.tree['history'] = []

            self.tree['history'].append(entry)

            try:
                self.validate()
            except Exception:
                self.tree['history'].pop()
                raise

    def get_history_entries(self):
        """
        Get a list of history entries from the file object.

        Returns
        -------
        entries : list
            A list of history entries.
        """

        if 'history' not in self.tree:
            return []

        if isinstance(self.tree['history'], list):
            return self.tree['history']

        if 'entries' in self.tree['history']:
            return self.tree['history']['entries']

        return []

    def info(self, max_rows=display.DEFAULT_MAX_ROWS, max_cols=display.DEFAULT_MAX_COLS, show_values=display.DEFAULT_SHOW_VALUES):
        """
        Print a rendering of this file's tree to stdout.

        Parameters
        ----------
        max_rows : int, tuple, or None, optional
            Maximum number of lines to print.  Nodes that cannot be
            displayed will be elided with a message.
            If int, constrain total number of displayed lines.
            If tuple, constrain lines per node at the depth corresponding \
                to the tuple index.
            If None, display all lines.

        max_cols : int or None, optional
            Maximum length of line to print.  Nodes that cannot
            be fully displayed will be truncated with a message.
            If int, constrain length of displayed lines.
            If None, line length is unconstrained.

        show_values : bool, optional
            Set to False to disable display of primitive values in
            the rendered tree.
        """
        lines = display.render_tree(self.tree, max_rows=max_rows, max_cols=max_cols, show_values=show_values, identifier="root.tree")
        print("\n".join(lines))

    def search(self, key=NotSet, type=NotSet, value=NotSet, filter=None):
        """
        Search this file's tree.

        Parameters
        ----------
        key : NotSet, str, or any other object
            Search query that selects nodes by dict key or list index.
            If NotSet, the node key is unconstrained.
            If str, the input is searched among keys/indexes as a regular
            expression pattern.
            If any other object, node's key or index must equal the queried key.

        type : NotSet, str, or builtins.type
            Search query that selects nodes by type.
            If NotSet, the node type is unconstrained.
            If str, the input is searched among (fully qualified) node type
            names as a regular expression pattern.
            If builtins.type, the node must be an instance of the input.

        value : NotSet, str, or any other object
            Search query that selects nodes by value.
            If NotSet, the node value is unconstrained.
            If str, the input is searched among values as a regular
            expression pattern.
            If any other object, node's value must equal the queried value.

        filter : callable
            Callable that filters nodes by arbitrary criteria.
            The callable accepts one or two arguments:

            - the node
            - the node's list index or dict key (optional)

            and returns True to retain the node, or False to remove it from
            the search results.

        Returns
        -------
        asdf.search.AsdfSearchResult
            the result of the search
        """
        result = AsdfSearchResult(["root.tree"], self.tree)
        return result.search(key=key, type=type, value=value, filter=filter)


# Inherit docstring from dictionary
AsdfFile.keys.__doc__ = dict.keys.__doc__


def _check_and_set_mode(fileobj, asdf_mode):

    if asdf_mode is not None and asdf_mode not in ['r', 'rw']:
        msg = "Unrecognized asdf mode '{}'. Must be either 'r' or 'rw'"
        raise ValueError(msg.format(asdf_mode))

    if asdf_mode is None:
        if isinstance(fileobj, io.IOBase):
            return 'rw' if fileobj.writable() else 'r'

        if isinstance(fileobj, generic_io.GenericFile):
            return fileobj.mode

        # This is the safest assumption for the default fallback
        return 'r'

    return asdf_mode


def open_asdf(fd, uri=None, mode=None, validate_checksums=False,
              extensions=None, do_not_fill_defaults=False,
              ignore_version_mismatch=True, ignore_unrecognized_tag=False,
              _force_raw_types=False, copy_arrays=False, lazy_load=True,
              custom_schema=None, strict_extension_check=False,
              ignore_missing_extensions=False, validate_on_read=True,
              _compat=False):
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
        See `~asdf.types.AsdfExtension` for more information.

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

    lazy_load : bool, optional
        When `True` and the underlying file handle is seekable, data
        arrays will only be loaded lazily: i.e. when they are accessed
        for the first time. In this case the underlying file must stay
        open during the lifetime of the tree. Setting to False causes
        all data arrays to be loaded up front, which means that they
        can be accessed even after the underlying file is closed.
        Note: even if `lazy_load` is `False`, `copy_arrays` is still taken
        into account.

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

    validate_on_read : bool, optional
        When `True`, validate the newly opened file against tag and custom
        schemas.  Recommended unless the file is already known to be valid.

    Returns
    -------
    asdffile : AsdfFile
        The new AsdfFile object.
    """

    readonly = False

    # For now retain backwards compatibility with the old API behavior,
    # specifically when being called from AsdfFile.open
    if not _compat:
        mode = _check_and_set_mode(fd, mode)
        readonly = (mode == 'r' and not copy_arrays)

    instance = AsdfFile(extensions=extensions,
                   ignore_version_mismatch=ignore_version_mismatch,
                   ignore_unrecognized_tag=ignore_unrecognized_tag,
                   copy_arrays=copy_arrays, lazy_load=lazy_load,
                   custom_schema=custom_schema, _readonly=readonly)

    return AsdfFile._open_impl(instance,
        fd, uri=uri, mode=mode,
        validate_checksums=validate_checksums,
        do_not_fill_defaults=do_not_fill_defaults,
        _force_raw_types=_force_raw_types,
        strict_extension_check=strict_extension_check,
        ignore_missing_extensions=ignore_missing_extensions,
        validate_on_read=validate_on_read)


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
