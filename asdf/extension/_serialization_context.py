import contextlib

from asdf._helpers import validate_version
from asdf.extension import ExtensionProxy


class SerializationContext:
    """
    Container for parameters of the current (de)serialization.

    This class should not be instantiated directly and instead
    will be created by the AsdfFile object and provided to extension
    classes (like Converters) via method arguments.
    """

    def __init__(self, version, extension_manager, url, blocks):
        self._version = validate_version(version)
        self._extension_manager = extension_manager
        self._url = url
        self._blocks = blocks

        self.__extensions_used = set()

    @property
    def url(self):
        """
        The URL (if any) of the file being read or written.

        Used to compute relative locations of external files referenced by this
        ASDF file. The URL will not exist in some cases (e.g. when the file is
        written to an `io.BytesIO`).

        Returns
        -------
        str or None
        """
        return self._url

    @property
    def version(self):
        """
        Get the ASDF Standard version.

        Returns
        -------
        str
        """
        return self._version

    @property
    def extension_manager(self):
        """
        Get the ExtensionManager for enabled extensions.

        Returns
        -------
        asdf.extension.ExtensionManager
        """
        return self._extension_manager

    def _mark_extension_used(self, extension):
        """
        Note that an extension was used when reading or writing the file.

        Parameters
        ----------
        extension : asdf.extension.Extension
        """
        self.__extensions_used.add(ExtensionProxy.maybe_wrap(extension))

    @property
    def _extensions_used(self):
        """
        Get the set of extensions that were used when reading or writing the file.

        Returns
        -------
        set of asdf.extension.Extension
        """
        return self.__extensions_used

    @contextlib.contextmanager
    def _deserialization(self):
        self._obj = None
        self._blk = None
        self._cb = None
        yield self
        if self._blk is not None:
            self._blocks.blocks.assign_object(self._obj, self._blk)
            self._blocks._data_callbacks.assign_object(self._obj, self._cb)

    @contextlib.contextmanager
    def _serialization(self, obj):
        self._obj = obj
        yield self

    def get_block_data_callback(self, index, key=None):
        """
        Generate a callable that when called will read data
        from a block at the provided index

        Parameters
        ----------
        index : int
            Block index

        key : BlockKey
            TODO

        Returns
        -------
        callback : callable
            A callable that when called (with no arguments) returns
            the block data as a one dimensional array of uint8
        """
        blk = self._blocks.blocks[index]
        cb = self._blocks._get_data_callback(index)

        if key is None:
            if self._blk is not None:
                msg = "Converters accessing >1 block must provide a key for each block"
                raise OSError(msg)
            self._blk = blk
            self._cb = cb
        else:
            self._blocks.blocks.assign_object(key, blk)
            self._blocks._data_callbacks.assign_object(key, cb)

        return cb

    def find_available_block_index(self, data_callback, lookup_key=None):
        """
        Find the index of an available block to write data.

        This is typically used inside asdf.extension.Converter.to_yaml_tree

        Parameters
        ----------
        data_callback: callable
            Callable that when called will return data (ndarray) that will
            be written to a block.
            At the moment, this is only assigned if a new block
            is created to avoid circular references during AsdfFile.update.

        lookup_key : hashable, optional
            Unique key used to retrieve the index of a block that was
            previously allocated or reserved. For ndarrays this is
            typically the id of the base ndarray.

        Returns
        -------
        block_index: int
            Index of the block where data returned from data_callback
            will be written.
        """

        if lookup_key is None:
            lookup_key = self._obj
        return self._blocks.make_write_block(data_callback, BlockOptions(), lookup_key)
