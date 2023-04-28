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

    def get_block_data_callback(self, index):
        """
        Generate a callable that when called will read data
        from a block at the provided index

        Parameters
        ----------
        index : int
            Block index

        Returns
        -------
        callback : callable
            A callable that when called (with no arguments) returns
            the block data as a one dimensional array of uint8
        """
        blk = self._blocks.blocks[index]

        def callback(blk=blk):
            return blk.data

        return callback

    def assign_block_key(self, block_index, key):
        """
        Associate a unique hashable key with a block.

        This is used during Converter.from_yaml_tree and allows
        the AsdfFile to be aware of which blocks belong to the
        object handled by the converter and allows load_block
        to locate the block using the key instead of the index
        (which might change if a file undergoes an AsdfFile.update).

        If the block index is later needed (like during to_yaml_tree)
        the key can be used with find_block_index to lookup the
        block index.

        Parameters
        ----------

        block_index : int
            The index of the block to associate with the key

        key : hashable
            A unique hashable key to associate with a block
        """
        self._blocks.blocks.assign_object(key, self._blocks.blocks[block_index])

    def find_block_index(self, lookup_key, data_callback=None):
        """
        Find the index of a previously allocated or reserved block.

        This is typically used inside asdf.extension.Converter.to_yaml_tree

        Parameters
        ----------
        lookup_key : hashable
            Unique key used to retrieve the index of a block that was
            previously allocated or reserved. For ndarrays this is
            typically the id of the base ndarray.

        data_callback: callable, optional
            Callable that when called will return data (ndarray) that will
            be written to a block.
            At the moment, this is only assigned if a new block
            is created to avoid circular references during AsdfFile.update.

        Returns
        -------
        block_index: int
            Index of the block where data returned from data_callback
            will be written.
        """

        # TODO eventually this will need to map memmap blocks to not rewrite data
        # TODO lookup options from previous block
        return self._blocks.make_write_block(data_callback, BlockOptions(), lookup_key)
