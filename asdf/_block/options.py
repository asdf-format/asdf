from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asdf import _compression as mcompression
from asdf.config import get_config

if TYPE_CHECKING:
    from asdf.typing import ArrayStorage, Compression


class Options:
    """
    Storage and compression options useful when reading or writing ASDF blocks.
    """

    def __init__(
        self,
        storage_type: ArrayStorage = None,
        compression_type: Compression = None,
        compression_kwargs: dict[str, Any] | None = None,
        save_base: bool | None = None,
    ):
        if storage_type is None:
            storage_type = get_config().all_array_storage or "internal"
        if save_base is None:
            save_base = get_config().default_array_save_base

        self._storage_type = None
        self._compression = None
        self._compression_kwargs: dict[str, Any] = compression_kwargs or {}

        # set via setters
        self.compression = compression_type
        self.storage_type = storage_type
        self.save_base = save_base

    @property
    def storage_type(self) -> ArrayStorage:
        return self._storage_type

    @storage_type.setter
    def storage_type(self, storage_type: ArrayStorage) -> None:
        if storage_type not in ["internal", "external", "streamed", "inline"]:
            msg = "array_storage must be one of 'internal', 'external', 'streamed' or 'inline'"
            raise ValueError(msg)
        self._storage_type = storage_type

    @property
    def compression(self) -> Compression:
        return self._compression

    @compression.setter
    def compression(self, compression: Compression) -> None:
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
    def compression_kwargs(self) -> dict[str, Any]:
        return self._compression_kwargs

    @compression_kwargs.setter
    def compression_kwargs(self, kwargs: dict[str, Any] | None) -> None:
        if not kwargs:
            kwargs = {}
        self._compression_kwargs = kwargs

    @property
    def save_base(self) -> bool | None:
        return self._save_base

    @save_base.setter
    def save_base(self, save_base: bool | None) -> None:
        if not (isinstance(save_base, bool) or save_base is None):
            msg = "save_base must be a bool or None"
            raise ValueError(msg)
        self._save_base = save_base

    def __copy__(self):
        return type(self)(self._storage_type, self._compression, self._compression_kwargs)
