from asdf import compression as mcompression
from asdf.config import get_config


class Options:
    """
    Storage and compression options useful when reading or writing ASDF blocks.
    """

    def __init__(self, storage_type=None, compression_type=None, compression_kwargs=None):
        if storage_type is None:
            storage_type = get_config().all_array_storage or "internal"
        self._storage_type = None
        self._compression = None
        self._compression_kwargs = None

        # set via setters
        self.compression_kwargs = compression_kwargs
        self.compression = compression_type
        self.storage_type = storage_type

    @property
    def storage_type(self):
        return self._storage_type

    @storage_type.setter
    def storage_type(self, storage_type):
        if storage_type not in ["internal", "external", "streamed", "inline"]:
            msg = "array_storage must be one of 'internal', 'external', 'streamed' or 'inline'"
            raise ValueError(msg)
        self._storage_type = storage_type

    @property
    def compression(self):
        return self._compression

    @compression.setter
    def compression(self, compression):
        msg = f"Invalid compression type: {compression}"
        if compression == "input":
            # "input" compression will validate as the ASDF compression module made
            # some assumptions about availability of information (that the input block
            # is known). The Options here do not have the same assumption.
            # For a block read from a file, it's options will be initialized with
            # the compression value read from the block header so we should never
            # see 'input' at this point.
            raise ValueError(msg)
        try:
            compression = mcompression.validate(compression)
        except ValueError:
            raise ValueError(msg)
        self._compression = compression

    @property
    def compression_kwargs(self):
        return self._compression_kwargs

    @compression_kwargs.setter
    def compression_kwargs(self, kwargs):
        if not kwargs:
            kwargs = {}
        self._compression_kwargs = kwargs

    def __copy__(self):
        return type(self)(self._storage_type, self._compression, self._compression_kwargs)
