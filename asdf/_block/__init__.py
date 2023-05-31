"""
Submodule for reading and writing ASDF blocks.

The primary interface to this submodule is ``_block.manager.Manager``
that in some ways mimics the older ``BlockManager``. An instance
of ``Manager`` will be created by each `asdf.AsdfFile` instance.

Internally, this submodule is broken up into:
    - low-level:
        - ``io``: functions for reading and writing blocks
        - ``key``: ``Key`` used to implement ``Store`` (see below)
        - ``store``: ``Store`` special key-value store for indexing blocks
    - medium-level:
        - ``reader``:  ``ReadBlock`` and ``read_blocks``
        - ``writer``:  ``WriteBlock`` and ``write_blocks``
        - ``callback``: ``DataCallback`` for reading block data
        - ``external``: ``ExternalBlockCache`` for reading external blocks
        - ``options``: ``Options`` controlling block storage
    - high-level:
        - ``manager``: ``Manager`` and associated classes


The low-level ``io`` functions are responsible for reading and writing
bytes compatible with the block format defined in the ASDF standard.
These should be compatible with as wide a variety of file formats as possible
including files that are:
    - seekable and non-seekable
    - memory mappable
    - accessed from a remote server
    - stored in memory
    - etc

To help organize ASDF block data the ``key`` and ``store`` submodules
provide a special key-value store, ``Store``. ``Store`` uses ``Key``
instances to tie the lifetime of values to the lifetime of objects
in the ASDF tree (without keeping references to the objects) and
allows non-hashable objects to be used as keys. See the ``key``
submodule docstring for more details. One usage of ``Store`` is
for managing ASDF block ``Options``. ``Options`` determine where
and how array data will be written and a single ``Options`` instance
might be associated with several arrays within the ASDF tree
(if the arrays share the same base array). By using a ``Key`` generated
with the base array the block ``Options`` can be stored in a ``Store``
without keeping a reference to the base array and these ``Options``
will be made unavailable if the base array is garbage collected (so
they are not inapproriately assigned to a new array).

The medium-level submodules ``reader`` and ``writer`` each define
a helper class and function for reading or writing blocks:
    - ``ReadBlock`` and ``WriteBlock``
    - ``read_blocks`` and ``write_blocks``
These abstract some of the complexity of reading and writing blocks
using the low-level API and are the primary means by which the ``Manager``
reads and writes ASDF blocks. Reading of external blocks by the ``Manager``
requires some special handling which is contained in the ``external``
submodule.

To allow for lazy-loading of ASDF block data, ``callback`` defines
``DataCallback`` which allows reading block data even after the blocks
have been rearranged following an update-in-place.
"""
