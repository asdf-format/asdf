import copy
import datetime
import io
import os
import pathlib
import time
import warnings
import weakref

from packaging.version import Version

from . import _compression as mcompression
from . import _display as display
from . import _node_info as node_info
from . import _version as version
from . import constants, generic_io, lazy_nodes, reference, schema, treeutil, util, versioning, yamlutil
from ._block.manager import Manager as BlockManager
from ._helpers import validate_version
from .config import config_context, get_config
from .exceptions import (
    AsdfManifestURIMismatchWarning,
    AsdfPackageVersionWarning,
    AsdfWarning,
    DelimiterNotFoundError,
    ValidationError,
)
from .extension import Extension, ExtensionProxy, _serialization_context, get_cached_extension_manager
from .search import AsdfSearchResult
from .tags.core import AsdfObject, ExtensionMetadata, HistoryEntry, Software
from .util import NotSet


def _get_asdf_library_info():
    """
    Get information about asdf to include in the asdf_library entry
    in the Tree.
    """
    return Software(
        {
            "name": "asdf",
            "version": version.version,
            "homepage": "http://github.com/asdf-format/asdf",
            "author": "The ASDF Developers",
        },
    )


class AsdfFile:
    """
    The main class that represents an ASDF file object.
    """

    def __init__(
        self,
        tree=None,
        uri=None,
        extensions=None,
        version=None,
        ignore_unrecognized_tag=False,
        memmap=False,
        lazy_load=True,
        custom_schema=None,
    ):
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
            if possible and if created from `asdf.open`.

        extensions : object, optional
            Additional extensions to use when reading and writing the file.
            May be an `asdf.extension.Extension` or a `list` of extensions.

        version : str, optional
            The ASDF Standard version.  If not provided, defaults to the
            configured default version.  See `asdf.config.AsdfConfig.default_version`.

        ignore_unrecognized_tag : bool, optional
            When `True`, do not raise warnings for unrecognized tags. Set to
            `False` by default.

        memmap : bool, optional
            When `True`, when reading files, attempt to memmap underlying data
            arrays when possible. Defaults to ``False``.

        lazy_load : bool, optional
            When `True` and the underlying file handle is seekable, data
            arrays will only be loaded lazily: i.e. when they are accessed
            for the first time. In this case the underlying file must stay
            open during the lifetime of the tree. Setting to False causes
            all data arrays to be loaded up front, which means that they
            can be accessed even after the underlying file is closed.

        custom_schema : str, optional
            Path to a custom schema file that will be used for a secondary
            validation pass. This can be used to ensure that particular ASDF
            files follow custom conventions beyond those enforced by the
            standard.
        """
        self._fname = ""

        # make a new AsdfVersion instance here so files don't share the same instance
        self._file_format_version = versioning.AsdfVersion(versioning._FILE_FORMAT_VERSION)

        # Don't use the version setter here; it tries to access
        # the extensions, which haven't been assigned yet.
        if version is None:
            self._version = versioning.AsdfVersion(get_config().default_version)
        else:
            self._version = versioning.AsdfVersion(validate_version(version))

        self._user_extensions = self._process_user_extensions(extensions)
        self._plugin_extensions = self._process_plugin_extensions()
        self._extension_manager = None

        if custom_schema is not None:
            self._custom_schema = schema._load_schema_cached(custom_schema, None, True)
        else:
            self._custom_schema = None

        self._ignore_unrecognized_tag = ignore_unrecognized_tag

        # Context of a call to treeutil.walk_and_modify, needed in the AsdfFile
        # in case walk_and_modify is re-entered by extension code (via
        # custom_tree_to_tagged_tree or tagged_tree_to_custom_tree).
        self._tree_modification_context = treeutil._TreeModificationContext()

        # A cache of tagged objects and their converted custom objects used when
        # a file is read with "lazy_tree=True". Used by lazy_nodes.
        self._tagged_object_cache = lazy_nodes._TaggedObjectCache()

        self._fd = None
        self._closed = False
        self._external_asdf_by_uri = {}
        self._blocks = BlockManager(uri=uri, lazy_load=lazy_load, memmap=memmap)
        if tree is None:
            # Bypassing the tree property here, to avoid validating
            # an empty tree.
            self._tree = AsdfObject()
        elif isinstance(tree, AsdfFile):
            if self.extensions != tree.extensions:
                # TODO(eslavich): Why not?  What if that's the goal
                # of copying the file?
                msg = "Can not copy AsdfFile and change active extensions"
                raise ValueError(msg)
            self._blocks._uri = tree.uri
            # Set directly to self._tree (bypassing property), since
            # we can assume the other AsdfFile is already valid.
            # Call "walk_and_modify" here to use it's logic for
            # creating a "copy" of the other tree. This mimics what was previously
            # a call to find_references (which we longer do in AsdfFile.__init__)
            self._tree = treeutil.walk_and_modify(tree.tree, lambda o: o)
        else:
            self._tree = AsdfObject(tree)

        self._comments = []

    @property
    def version(self):
        """
        Get this AsdfFile's ASDF Standard version.

        Returns
        -------
        asdf.versioning.AsdfVersion
        """
        return self._version

    @version.setter
    def version(self, value):
        """
        Set this AsdfFile's ASDF Standard version.

        Parameters
        ----------
        value : str or asdf.versioning.AsdfVersion
        """
        self._version = versioning.AsdfVersion(validate_version(value))
        # The new version may not be compatible with the previous
        # set of extensions, so we need to check them again:
        self._user_extensions = self._process_user_extensions(self._user_extensions)
        self._plugin_extensions = self._process_plugin_extensions()
        self._extension_manager = None

    @property
    def version_string(self):
        """
        Get this AsdfFile's ASDF Standard version as a string.

        Returns
        -------
        str
        """
        return str(self._version)

    @property
    def extensions(self):
        """
        Get the list of user extensions that are enabled for
        use with this AsdfFile.

        Returns
        -------
        list of asdf.extension.ExtensionProxy
        """
        return self._user_extensions

    @extensions.setter
    def extensions(self, value):
        """
        Set the list of user extensions that are enabled for
        use with this AsdfFile.

        Parameters
        ----------
        value : list of asdf.extension.Extension
        """
        self._user_extensions = self._process_user_extensions(value)
        self._extension_manager = None

    @property
    def extension_manager(self):
        """
        Get the ExtensionManager for this AsdfFile.

        Returns
        -------
        asdf.extension.ExtensionManager
        """
        if self._extension_manager is None:
            self._extension_manager = get_cached_extension_manager(self._user_extensions + self._plugin_extensions)
        return self._extension_manager

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def _check_extensions(self, tree, strict=False):
        """
        Compare the user's installed extensions to metadata in the tree
        and warn when a) an extension is missing or b) an extension is
        present but the file was written with a later version of the
        extension's package.

        Parameters
        ----------
        tree : AsdfObject
            Fully converted tree of custom types.
        strict : bool, optional
            Set to `True` to convert warnings to exceptions.
        """
        if "history" not in tree or not isinstance(tree["history"], dict) or "extensions" not in tree["history"]:
            return

        for extension in tree["history"]["extensions"]:
            installed = None
            for ext in self._user_extensions + self._plugin_extensions:
                if (extension.extension_uri is not None and extension.extension_uri == ext.extension_uri) or (
                    extension.extension_uri is None and extension.extension_class in ext.legacy_class_names
                ):
                    installed = ext
                    break

            filename = f"'{self._fname}' " if self._fname else ""
            if extension.extension_uri is not None:
                extension_description = f"URI '{extension.extension_uri}'"
            else:
                extension_description = f"class '{extension.extension_class}'"
            if extension.software is not None:
                extension_description += (
                    f" (from package {extension.software['name']}=={extension.software['version']})"
                )

            if installed is None:
                msg = (
                    f"File {filename}was created with extension "
                    f"{extension_description}, which is not currently installed"
                )
                if strict:
                    raise RuntimeError(msg)

                warnings.warn(msg, AsdfPackageVersionWarning)

            elif extension.software:
                # Local extensions may not have a real version.  If the package name changed,
                # then the version sequence may have been reset.
                if installed.package_version is None or installed.package_name != extension.software["name"]:
                    continue
                # Compare version in file metadata with installed version
                if Version(installed.package_version) < Version(extension.software["version"]):
                    msg = (
                        f"File {filename}was created with extension {extension_description}, "
                        f"but older package ({installed.package_name}=={installed.package_version}) is installed."
                    )
                    if strict:
                        raise RuntimeError(msg)

                    warnings.warn(msg, AsdfPackageVersionWarning)

            # check version of manifest providing package (if one was recorded)
            if "manifest_software" in extension:
                package_name = extension["manifest_software"]["name"]
                package_version = Version(extension["manifest_software"]["version"])
                package_description = f"{package_name}=={package_version}"
                installed_version = None
                for mapping in get_config().resource_manager._resource_mappings:
                    if mapping.package_name == package_name:
                        installed_version = Version(mapping.package_version)
                        break
                msg = None
                if installed_version is None:
                    msg = (
                        f"File {filename}was created with package {package_description}, "
                        "which is currently not installed"
                    )
                elif installed_version < package_version:
                    msg = (
                        f"File {filename}was created with package {package_description}, "
                        f"but older package({package_name}=={installed_version}) is installed."
                    )
                if msg:
                    if strict:
                        raise RuntimeError(msg)
                    warnings.warn(msg, AsdfPackageVersionWarning)

    def _process_plugin_extensions(self):
        """
        Select installed extensions that are compatible with this
        file's ASDF Standard version.

        Returns
        -------
        list of asdf.extension.ExtensionProxy
        """
        return [e for e in get_config().extensions if self.version_string in e.asdf_standard_requirement]

    def _process_user_extensions(self, extensions):
        """
        Validate a list of extensions requested by the user
        add missing extensions registered with the current `AsdfConfig`.

        Parameters
        ----------
        extensions : object
            May be an `asdf.extension.Extension` or a `list` of extensions.

        Returns
        -------
        list of asdf.extension.ExtensionProxy
        """
        if extensions is None:
            extensions = []
        elif isinstance(extensions, (Extension, ExtensionProxy)):
            extensions = [extensions]

        if not isinstance(extensions, list):
            msg = "The extensions parameter must be an extension or list of extensions"
            raise TypeError(msg)

        extensions = [ExtensionProxy.maybe_wrap(e) for e in extensions]

        result = []
        for extension in extensions:
            if self.version_string not in extension.asdf_standard_requirement:
                warnings.warn(
                    f"Extension {extension} does not support ASDF Standard {self.version_string}.  "
                    "It has been disabled.",
                    AsdfWarning,
                )
            else:
                result.append(extension)

        return result

    def _update_extension_history(self, tree, serialization_context):
        """
        Update the extension metadata on this file's tree to reflect
        extensions used during serialization.

        Parameters
        ----------
        serialization_context : asdf.extension.SerializationContext
            The context that was used to serialize the tree.
        """
        if serialization_context.version < versioning.NEW_HISTORY_FORMAT_MIN_VERSION:
            return

        if "history" not in tree:
            tree["history"] = {"extensions": []}
        # Support clients who are still using the old history format
        elif isinstance(tree["history"], list):
            histlist = tree["history"]
            tree["history"] = {"entries": histlist, "extensions": []}
            warnings.warn(
                "The ASDF history format has changed in order to "
                "support metadata about extensions. History entries "
                "should now be stored under tree['history']['entries'].",
                AsdfWarning,
            )
        elif "extensions" not in tree["history"]:
            tree["history"]["extensions"] = []

        for extension in serialization_context._extensions_used:
            ext_name = extension.class_name
            ext_meta = ExtensionMetadata(extension_class=ext_name)
            if extension.package_name is not None:
                ext_meta["software"] = Software(name=extension.package_name, version=extension.package_version)
            if extension.extension_uri is not None:
                ext_meta["extension_uri"] = extension.extension_uri
            if extension.compressors:
                ext_meta["supported_compression"] = [comp.label.decode("ascii") for comp in extension.compressors]
            manifest = getattr(extension._delegate, "_manifest", None)
            if manifest is not None:
                # check if this extension was built from a manifest is a different package
                resource_mapping = get_config().resource_manager._mappings_by_uri.get(manifest["id"])
                # if an extension was registered with a manifest uri that does not match the id the
                # resource_mapping lookup will fail (resource_mapping will be None)
                if resource_mapping is None:
                    warnings.warn(
                        f"Extension ({extension.extension_uri}) uses a manifest with a uri that "
                        "does not match it's id. Please open an issue with the extension maintainer",
                        AsdfManifestURIMismatchWarning,
                    )
                elif resource_mapping.package_name != extension.package_name:
                    ext_meta["manifest_software"] = Software(
                        name=resource_mapping.package_name,
                        version=resource_mapping.package_version,
                    )

            for i, entry in enumerate(tree["history"]["extensions"]):
                # Update metadata about this extension if it already exists
                if (
                    entry.extension_uri is not None and entry.extension_uri == extension.extension_uri
                ) or entry.extension_class in extension.legacy_class_names:
                    tree["history"]["extensions"][i] = ext_meta
                    break
            else:
                tree["history"]["extensions"].append(ext_meta)

    @property
    def file_format_version(self):
        return self._file_format_version

    def close(self):
        """
        Close the file handles associated with the `asdf.AsdfFile`.
        """
        if self._fd and not self._closed:
            # This is ok to always do because GenericFile knows
            # whether it "owns" the file and should close it.
            self._fd.close()
            self._fd = None
            self._closed = True
            # as we're closing the file, also empty out the
            # tree so that references to array data can be released
            self._tree = AsdfObject()
            self._tagged_object_cache.clear()
        for external in self._external_asdf_by_uri.values():
            external.close()
        self._external_asdf_by_uri.clear()
        self._blocks.close()

    def copy(self):
        return self.__class__(
            copy.deepcopy(self._tree),
            self._blocks._uri,
            self._user_extensions,
        )

    __copy__ = __deepcopy__ = copy

    @property
    def uri(self):
        """
        Get the URI associated with the `AsdfFile`.

        In many cases, it is automatically determined from the file
        handle used to read or write the file.
        """
        return self._blocks._uri

    def resolve_uri(self, uri):
        """
        Resolve a (possibly relative) URI against the URI of this ASDF
        file.  May be overridden by base classes to change how URIs
        are resolved.  This does not apply any ``uri_mapping`` that was
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

    def open_external(self, uri, **kwargs):
        """
        Open an external ASDF file, from the given (possibly relative)
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
        if resolved_uri == "" or resolved_uri == self.uri:
            return self

        asdffile = self._external_asdf_by_uri.get(resolved_uri)
        if asdffile is None:
            asdffile = open_asdf(resolved_uri, mode="r", **kwargs)
            self._external_asdf_by_uri[resolved_uri] = asdffile
        return asdffile

    @property
    def tree(self):
        """
        Get/set the tree of data in the ASDF file.

        When set, the tree will be validated against the ASDF schema.
        """
        if self._closed:
            msg = "Cannot access data from closed ASDF file"
            raise OSError(msg)
        return self._tree

    @tree.setter
    def tree(self, tree):
        self._tree = AsdfObject(tree)

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

    def _validate(self, tree, reading=False):
        with self._blocks.options_context():
            # If we're validating on read then the tree
            # is already guaranteed to be in tagged form.
            tagged_tree = tree if reading else yamlutil.custom_tree_to_tagged_tree(tree, self)

            schema.validate(tagged_tree, self, reading=reading)

    def validate(self):
        """
        Validate the current state of the tree against the ASDF schema.
        """
        self._validate(self._tree)

    def make_reference(self, path=None):
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
        reference :
            A reference object.

        Examples
        --------
        For the given AsdfFile ``ff``, add an external reference to the data in
        an external file::

            >>> import asdf
            >>> flat = asdf.open("http://stsci.edu/reference_files/flat.asdf")  # doctest: +SKIP
            >>> ff.tree['flat_field'] = flat.make_reference(['data'])  # doctest: +SKIP
        """
        return reference.make_reference(self, [] if path is None else path)

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
        self._blocks._set_array_storage(arr, array_storage)

    def get_array_storage(self, arr):
        """
        Get the block type for the given array data.

        Parameters
        ----------
        arr : numpy.ndarray
        """
        return self._blocks._get_array_storage(arr)

    def set_array_compression(self, arr, compression, **compression_kwargs):
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

            - ``input``: Use the same compression as in the file read.
              If there is no prior file, acts as None.

        """
        self._blocks._set_array_compression(arr, compression, **compression_kwargs)

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
        return self._blocks._get_array_compression(arr)

    def get_array_compression_kwargs(self, arr):
        """ """
        return self._blocks._get_array_compression_kwargs(arr)

    def set_array_save_base(self, arr, save_base):
        """
        Set the ``save_base`` option for ``arr``. When ``arr`` is
        written to a file, if ``save_base`` is ``True`` the base array
        for ``arr`` will be saved.

        Note that similar to other array options this setting is linked
        to the base array if ``arr`` is a view.

        Parameters
        ----------
        arr : numpy.ndarray

        save_base : bool or None
            if ``None`` the ``default_array_save_base`` value from asdf
            config will be used
        """
        self._blocks._set_array_save_base(arr, save_base)

    def get_array_save_base(self, arr):
        """
        Returns the ``save_base`` option for ``arr``. When ``arr`` is
        written to a file, if ``save_base`` is ``True`` the base array
        for ``arr`` will be saved.

        Parameters
        ----------
        arr : numpy.ndarray

        Returns
        -------
        save_base : bool or None
        """
        return self._blocks._get_array_save_base(arr)

    @classmethod
    def _parse_header_line(cls, line):
        """
        Parses the header line in a ASDF file to obtain the ASDF version.
        """
        parts = line.split()
        if len(parts) != 2 or parts[0] != constants.ASDF_MAGIC:
            msg = "Does not appear to be a ASDF file."
            raise ValueError(msg)

        try:
            version = versioning.AsdfVersion(parts[1].decode("ascii"))
        except ValueError as err:
            msg = f"Unparsable version in ASDF file: {parts[1]}"
            raise ValueError(msg) from err

        if version != versioning._FILE_FORMAT_VERSION:
            msg = f"Unsupported ASDF file format version {version}"
            raise ValueError(msg)

        return version

    @classmethod
    def _read_comment_section(cls, fd):
        """
        Reads the comment section, between the header line and the
        Tree or first block.
        """
        content = fd.read_until(
            b"(%YAML)|(" + constants.BLOCK_MAGIC + b")",
            5,
            "start of content",
            include=False,
            exception=False,
        )

        comments = []

        lines = content.splitlines()
        for line in lines:
            if not line.startswith(b"#"):
                msg = "Invalid content between header and tree"
                raise ValueError(msg)
            comments.append(line[1:].strip())

        return comments

    @classmethod
    def _find_asdf_version_in_comments(cls, comments):
        for comment in comments:
            parts = comment.split()
            if len(parts) == 2 and parts[0] == constants.ASDF_STANDARD_COMMENT:
                try:
                    version = versioning.AsdfVersion(parts[1].decode("ascii"))
                except ValueError:
                    pass
                else:
                    return version

        return None

    @classmethod
    def _open_asdf(
        cls,
        self,
        fd,
        validate_checksums=False,
        extensions=None,
        lazy_tree=NotSet,
        _get_yaml_content=False,
        _force_raw_types=False,
        strict_extension_check=False,
        ignore_missing_extensions=False,
    ):
        """Attempt to populate AsdfFile data from file-like object"""

        if strict_extension_check and ignore_missing_extensions:
            msg = "'strict_extension_check' and 'ignore_missing_extensions' are incompatible options"
            raise ValueError(msg)

        with config_context() as cfg:
            # validate_checksums (unlike memmap and lazy_load) is provided
            # here instead of in __init__
            self._blocks._validate_checksums = validate_checksums
            self._mode = fd.mode
            self._fd = fd
            if self._fd._uri:
                self._blocks._uri = self._fd._uri
            # The filename is currently only used for tracing warning information
            self._fname = self._fd._uri if self._fd._uri else ""
            try:
                header_line = fd.read_until(b"\r?\n", 2, "newline", include=True)
            except DelimiterNotFoundError as e:
                msg = "Does not appear to be a ASDF file."
                raise ValueError(msg) from e
            self._file_format_version = cls._parse_header_line(header_line)

            self._comments = cls._read_comment_section(fd)

            version = cls._find_asdf_version_in_comments(self._comments)
            if version is not None:
                self.version = version
            else:
                # If no ASDF_STANDARD comment is found...
                self.version = versioning.AsdfVersion("1.0.0")

            # Now that version is set for good, we can add any additional
            # extensions, which may have narrow ASDF Standard version
            # requirements.
            if extensions:
                self.extensions = extensions

            yaml_token = fd.read(4)
            tree = None
            if yaml_token == b"%YAM":
                reader = fd.reader_until(
                    constants.YAML_END_MARKER_REGEX,
                    7,
                    "End of YAML marker",
                    include=True,
                    initial_content=yaml_token,
                )

                # For testing: just return the raw YAML content
                if _get_yaml_content:
                    yaml_content = reader.read()
                    fd.close()
                    return yaml_content

                # We parse the YAML content into basic data structures
                # now, but we don't do anything special with it until
                # after the blocks have been read
                tree = yamlutil.load_tree(reader)
                self._blocks.read(fd)
            elif yaml_token == constants.BLOCK_MAGIC:
                # this file has only blocks and we're already read the first block magic
                self._blocks.read(fd, after_magic=True)
            elif yaml_token != b"":
                msg = "ASDF file appears to contain garbage after header."
                raise OSError(msg)

            if tree is None:
                # At this point the tree should be tagged, but we want it to be
                # tagged with the core/asdf version appropriate to this file's
                # ASDF Standard version.  We're using custom_tree_to_tagged_tree
                # to select the correct tag for us.
                tree = yamlutil.custom_tree_to_tagged_tree(AsdfObject(), self)

            if self.version <= versioning.FILL_DEFAULTS_MAX_VERSION and get_config().legacy_fill_schema_defaults:
                schema.fill_defaults(tree, self, reading=True)

            if get_config().validate_on_read:
                try:
                    self._validate(tree, reading=True)
                except ValidationError:
                    self.close()
                    raise

            if lazy_tree is NotSet:
                lazy_tree = cfg.lazy_tree
            if lazy_tree and not _force_raw_types:
                obj = AsdfObject()
                obj.data = lazy_nodes.AsdfDictNode(tree, weakref.ref(self))
                tree = obj
            else:
                tree = yamlutil.tagged_tree_to_custom_tree(tree, self, _force_raw_types)

            if not (ignore_missing_extensions or _force_raw_types):
                self._check_extensions(tree, strict=strict_extension_check)

            self._tree = tree

            return self

    @classmethod
    def _open_impl(
        cls,
        self,
        fd,
        uri=None,
        mode="r",
        validate_checksums=False,
        extensions=None,
        lazy_tree=NotSet,
        _get_yaml_content=False,
        _force_raw_types=False,
        strict_extension_check=False,
        ignore_missing_extensions=False,
    ):
        """Attempt to open file-like object as an AsdfFile"""
        close_on_fail = isinstance(fd, (str, pathlib.Path))
        generic_file = generic_io.get_file(fd, mode=mode, uri=uri)
        try:
            return cls._open_asdf(
                self,
                generic_file,
                validate_checksums=validate_checksums,
                extensions=extensions,
                lazy_tree=lazy_tree,
                _get_yaml_content=_get_yaml_content,
                _force_raw_types=_force_raw_types,
                strict_extension_check=strict_extension_check,
                ignore_missing_extensions=ignore_missing_extensions,
            )
        except Exception:
            if close_on_fail:
                generic_file.close()
            raise

    def _write_tree(self, tree, fd, pad_blocks):
        fd.write(constants.ASDF_MAGIC)
        fd.write(b" ")
        fd.write(f"{self.file_format_version}".encode("ascii"))
        fd.write(b"\n")

        fd.write(b"#")
        fd.write(constants.ASDF_STANDARD_COMMENT)
        fd.write(b" ")
        fd.write(self.version_string.encode("ascii"))
        fd.write(b"\n")

        if len(tree):
            serialization_context = self._create_serialization_context(_serialization_context.BlockAccess.WRITE)

            for compression in self._blocks.get_output_compressions():
                # lookup extension
                compressor = mcompression._get_compressor_from_extensions(compression, return_extension=True)
                if compressor is not None:
                    # mark it as used
                    serialization_context._mark_extension_used(compressor[1])

            def _tree_finalizer(tagged_tree):
                """
                The list of extensions used is not known until after
                serialization, so we're using a hook provided by
                yamlutil.dump_tree to update extension metadata
                after the tree has been converted to tagged objects.
                """
                self._update_extension_history(tree, serialization_context)
                if "history" in tree:
                    tagged_tree["history"] = yamlutil.custom_tree_to_tagged_tree(
                        tree["history"],
                        self,
                        _serialization_context=serialization_context,
                    )
                else:
                    tagged_tree.pop("history", None)

            yamlutil.dump_tree(
                tree,
                fd,
                self,
                tree_finalizer=_tree_finalizer,
                _serialization_context=serialization_context,
            )

        if pad_blocks:
            padding = util.calculate_padding(fd.tell(), pad_blocks, fd.block_size)
            fd.fast_forward(padding)

    def _pre_write(self, fd):
        pass

    def _post_write(self, fd):
        pass

    def _serial_write(self, fd, pad_blocks, include_block_index):
        with self._blocks.write_context(fd):
            self._pre_write(fd)
            try:
                # prep a tree for a writing
                tree = copy.copy(self._tree)
                tree["asdf_library"] = _get_asdf_library_info()
                if "history" in self._tree:
                    tree["history"] = copy.deepcopy(self._tree["history"])

                self._write_tree(tree, fd, pad_blocks)
                self._blocks.write(pad_blocks, include_block_index)
            finally:
                self._post_write(fd)

    def update(
        self,
        all_array_storage=NotSet,
        all_array_compression=NotSet,
        compression_kwargs=NotSet,
        pad_blocks=False,
        include_block_index=True,
        version=None,
    ):
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

        compression_kwargs : dict, optional
            If provided, set this as the compression keyword arguments
            for all binary blocks in the file.

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
            Update the ASDF Standard version of this AsdfFile before
            writing.
        """

        with config_context() as config:
            if all_array_storage is not NotSet:
                config.all_array_storage = all_array_storage
            if all_array_compression is not NotSet:
                config.all_array_compression = all_array_compression
            if compression_kwargs is not NotSet:
                config.all_array_compression_kwargs = compression_kwargs

            fd = self._fd

            if fd is None:
                msg = "Can not update, since there is no associated file"
                raise ValueError(msg)

            if not fd.writable():
                msg = (
                    "Can not update, since associated file is read-only. Make "
                    "sure that the AsdfFile was opened with mode='rw' and the "
                    "underlying file handle is writable."
                )
                raise OSError(msg)

            if not fd.seekable():
                msg = "Can not update, since associated file is not seekable"
                raise OSError(msg)

            if version is not None:
                self.version = version

            # flush all pending memmap writes
            if fd.can_memmap():
                fd.flush_memmap()

            def rewrite():
                self._fd.seek(0)
                self._serial_write(self._fd, pad_blocks, include_block_index)
                self._fd.truncate()
                if self._fd.can_memmap():
                    self._fd.close_memmap()

            # if we have no read blocks, we can just call write_to as no internal blocks are reused
            if len(self._blocks.blocks) == 0:
                rewrite()
                return

            # if we have all external blocks, we can just call write_to as no internal blocks are reused
            if config.all_array_storage == "external":
                rewrite()
                return

            self._pre_write(fd)
            try:
                self._tree["asdf_library"] = _get_asdf_library_info()

                # prepare block manager for writing
                with self._blocks.write_context(self._fd, copy_options=False):
                    # write out tree to temporary buffer
                    tree_fd = generic_io.get_file(io.BytesIO(), mode="rw")
                    self._write_tree(self._tree, tree_fd, False)
                    new_tree_size = tree_fd.tell()

                    # update blocks
                    self._blocks.update(new_tree_size, pad_blocks, include_block_index)
                    end_of_file = self._fd.tell()

                # now write the tree
                self._fd.seek(0)
                tree_fd.seek(0)
                self._fd.write(tree_fd.read())
                self._fd.flush()

                # close memmap to trigger arrays to reload themselves
                self._fd.seek(end_of_file)
                self._fd.truncate()
                if self._fd.can_memmap():
                    self._fd.close_memmap()

            finally:
                self._post_write(fd)

    def write_to(
        self,
        fd,
        all_array_storage=NotSet,
        all_array_compression=NotSet,
        compression_kwargs=NotSet,
        pad_blocks=False,
        include_block_index=True,
        version=None,
    ):
        """
        Write the ASDF file to the given file-like object.

        `write_to` does not change the underlying file descriptor in
        the `asdf.AsdfFile` object, but merely copies the content to a new
        file.

        Parameters
        ----------
        fd : string or file-like object
            May be a string path to a file, or a Python file-like
            object.  If a string path, the file is automatically
            closed after writing.  If not a string path, it is the
            caller's responsibility to close the object.

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

        compression_kwargs : dict, optional
            If provided, set this as the compression keyword arguments
            for all binary blocks in the file.

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
            Update the ASDF Standard version of this AsdfFile before
            writing.
        """
        with config_context() as config:
            if all_array_storage is not NotSet:
                config.all_array_storage = all_array_storage
            if all_array_compression is not NotSet:
                config.all_array_compression = all_array_compression
            if compression_kwargs is not NotSet:
                config.all_array_compression_kwargs = compression_kwargs

            if version is not None:
                previous_version = self.version
                self.version = version

            try:
                with generic_io.get_file(fd, mode="w") as fd:
                    self._serial_write(fd, pad_blocks, include_block_index)
            finally:
                if version is not None:
                    self.version = previous_version

    def find_references(self):
        """
        Finds all external "JSON References" in the tree and converts
        them to ``reference.Reference`` objects.
        """
        # Set directly to self._tree, since it doesn't need to be re-validated.
        self._tree = reference.find_references(self._tree, self)

    def resolve_references(self):
        """
        Finds all external "JSON References" in the tree, loads the
        external content, and places it directly in the tree.  Saving
        a ASDF file after this operation means it will have no
        external references, and will be completely self-contained.
        """
        self._tree = reference.resolve_references(self._tree, self)

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
            ``asdf_library`` entry.

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

        time_ = datetime.datetime.fromtimestamp(
            int(os.environ.get("SOURCE_DATE_EPOCH", time.time())), datetime.timezone.utc
        )

        entry = HistoryEntry(
            {
                "description": description,
                "time": time_,
            },
        )

        if software is not None:
            entry["software"] = software

        if self.version >= versioning.NEW_HISTORY_FORMAT_MIN_VERSION:
            if "history" not in self.tree:
                self.tree["history"] = {"entries": []}
            elif "entries" not in self.tree["history"]:
                self.tree["history"]["entries"] = []

            self.tree["history"]["entries"].append(entry)

            try:
                self.validate()
            except Exception:
                self.tree["history"]["entries"].pop()
                raise
        else:
            if "history" not in self.tree:
                self.tree["history"] = []

            self.tree["history"].append(entry)

            try:
                self.validate()
            except Exception:
                self.tree["history"].pop()
                raise

    def get_history_entries(self):
        """
        Get a list of history entries from the file object.

        Returns
        -------
        entries : list
            A list of history entries.
        """

        if "history" not in self.tree:
            return []

        if isinstance(self.tree["history"], list):
            return self.tree["history"]

        if "entries" in self.tree["history"]:
            return self.tree["history"]["entries"]

        return []

    def schema_info(self, key="description", path=None, preserve_list=True, refresh_extension_manager=NotSet):
        """
        Get a nested dictionary of the schema information for a given key, relative to the path.

        This method will only return unambiguous info. If a property is subject to multiple
        subschemas or contains ambiguous entries (multiple titles) no result will be returned
        for that property.

        Parameters
        ----------
        key : str
            The key to look up.
            Default: "description"
        path : str or asdf.search.AsdfSearchResult
            A dot-separated path to the parameter to find the key information on or
            an `asdf.search.AsdfSearchResult` object.
            Default = None (full dictionary).
        preserve_list : bool
            If True, then lists are preserved. Otherwise, they are turned into dicts.
        refresh_extension_manager : bool
            If `True`, refresh the extension manager before looking up the
            key.  This is useful if you want to make sure that the schema
            data for a given key is up to date.
        """
        if refresh_extension_manager is not NotSet:
            warnings.warn("refresh_extension_manager is deprecated", DeprecationWarning)

        if isinstance(path, AsdfSearchResult):
            return path.schema_info(
                key,
                preserve_list=preserve_list,
                refresh_extension_manager=refresh_extension_manager,
            )

        return node_info.collect_schema_info(
            key,
            path,
            self.tree,
            preserve_list=preserve_list,
            refresh_extension_manager=refresh_extension_manager,
            extension_manager=self.extension_manager,
        )

    def info(
        self,
        max_rows=display.DEFAULT_MAX_ROWS,
        max_cols=display.DEFAULT_MAX_COLS,
        show_values=display.DEFAULT_SHOW_VALUES,
        refresh_extension_manager=NotSet,
    ):
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
        if refresh_extension_manager is not NotSet:
            warnings.warn("refresh_extension_manager is deprecated", DeprecationWarning)

        lines = display.render_tree(
            self.tree,
            max_rows=max_rows,
            max_cols=max_cols,
            show_values=show_values,
            identifier="root",
            refresh_extension_manager=refresh_extension_manager,
            extension_manager=self.extension_manager,
        )
        print("\n".join(lines))

    def search(self, key=NotSet, type_=NotSet, value=NotSet, filter_=None):
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

        type_ : NotSet, str, or builtins.type
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

        filter_ : callable
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
        result = AsdfSearchResult(["root"], self.tree)
        return result.search(key=key, type_=type_, value=value, filter_=filter_)

    # This function is called from within yamlutil methods to create
    # a context when one isn't explicitly passed in.
    def _create_serialization_context(self, operation=_serialization_context.BlockAccess.NONE):
        return _serialization_context.create(self, operation)


def open_asdf(
    fd,
    uri=None,
    mode=None,
    validate_checksums=False,
    extensions=None,
    ignore_unrecognized_tag=False,
    _force_raw_types=False,
    memmap=False,
    lazy_tree=NotSet,
    lazy_load=True,
    custom_schema=None,
    strict_extension_check=False,
    ignore_missing_extensions=False,
    _get_yaml_content=False,
):
    """
    Open an existing ASDF file.

    Parameters
    ----------
    fd : string or file-like object
        May be a string ``file`` or ``http`` URI, or a Python
        file-like object.

    uri : string, optional
        The URI of the file.  Only required if the URI can not be
        automatically determined from ``fd``.

    mode : string, optional
        The mode to open the file in.  Must be ``r`` (default) or
        ``rw``.

    validate_checksums : bool, optional
        If `True`, validate the blocks against their checksums.
        Requires reading the entire file, so disabled by default.

    extensions : object, optional
        Additional extensions to use when reading and writing the file.
        May be an `asdf.extension.Extension` or a `list` of extensions.

    ignore_unrecognized_tag : bool, optional
        When `True`, do not raise warnings for unrecognized tags. Set to
        `False` by default.

    memmap : bool, optional
        When `True`, when reading files, attempt to memmap underlying data
        arrays when possible. Defaults to ``False``.

    lazy_load : bool, optional
        When `True` and the underlying file handle is seekable, data
        arrays will only be loaded lazily: i.e. when they are accessed
        for the first time. In this case the underlying file must stay
        open during the lifetime of the tree. Setting to False causes
        all data arrays to be loaded up front, which means that they
        can be accessed even after the underlying file is closed.
        Note: even if ``lazy_load`` is `False`, ``memmap`` is still taken
        into account.

    lazy_tree : bool, optional
        When `True` the ASDF tree will not be converted to custom objects
        when the file is loaded. Instead, objects will be "lazily" converted
        only when they are accessed. Note that the tree will not contain dict
        and list instances for containers and instead return instances of classes
        defined in `asdf.lazy_nodes`. Since objects are converted when they
        are accessed, traversing the tree (like is done during `AsdfFile.info`
        and `AsdfFile.search`) will result in nodes being converted.

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

    if mode is not None and mode not in ["r", "rw"]:
        msg = f"Unrecognized asdf mode '{mode}'. Must be either 'r' or 'rw'"
        raise ValueError(msg)

    if mode is None:
        if isinstance(fd, io.IOBase):
            mode = "rw" if fd.writable() else "r"
        elif isinstance(fd, generic_io.GenericFile):
            mode = fd.mode
        else:
            # This is the safest assumption for the default fallback
            mode = "r"

    instance = AsdfFile(
        ignore_unrecognized_tag=ignore_unrecognized_tag,
        memmap=memmap,
        lazy_load=lazy_load,
        custom_schema=custom_schema,
    )

    return AsdfFile._open_impl(
        instance,
        fd,
        uri=uri,
        mode=mode,
        validate_checksums=validate_checksums,
        extensions=extensions,
        lazy_tree=lazy_tree,
        _get_yaml_content=_get_yaml_content,
        _force_raw_types=_force_raw_types,
        strict_extension_check=strict_extension_check,
        ignore_missing_extensions=ignore_missing_extensions,
    )
