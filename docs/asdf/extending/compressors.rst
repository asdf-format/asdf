.. currentmodule:: asdf.extension

.. _extending_compressors:

========================
Binary block compressors
========================

The `Compressor` interface provides an implementation of a compression algorithm
that can be used to transform binary blocks in an `~asdf.AsdfFile`.  Each
Compressor must provide a 4-byte compression code that identifies the algorithm.
Once the Compressor is installed as part of an Extension plugin, this code
will be available to users as an argument to `~asdf.AsdfFile.set_array_compression` and
the ``all_array_compression`` argument to `~asdf.AsdfFile.write_to` and
`~asdf.AsdfFile.update`.

See :ref:`extending_extensions_compressors` for details on including
a Compressor in an extension.

The Compressor interface
========================

Every Compressor implementation must provide one required property
and two required methods:

`Compressor.label` - A 4-byte compression code.  This code is used
by users to select a compression algorithm and also stored in the
binary block header to identify the algorithm that was applied to
the block's data.

`Compressor.compress` - The method that transforms the block's bytes
before they are written to an ASDF file.  The positional argument
is a `memoryview` object which is guaranteed to be 1D and contiguous.
Compressors must be prepared to handle `memoryview.itemsize` > 1.
Any keyword arguments are passed through from the user and may be used
to tune the compression algorithm.  ``compress`` methods have no return
value and instead are expected to yield bytes-like values until the
input data has been fully compressed.

`Compressor.decompress` - The method that transforms the block's bytes
after they are read from an ASDF file.  The first positional argument
is an `~collections.abc.Iterable` of bytes-like objects that each
contain a chunk of the compressed input data.  The second positional
argument is a pre-allocated output array where the decompressed
bytes should be written.  The method is expected to return the
number of bytes written to the output array.

Entry point performance considerations
======================================

For the good of `asdf` users everywhere, it's important that entry point
methods load as quickly as possible.  All extensions must be loaded before
reading an ASDF file, and therefore all compressors are created as well.  Any
compressor module or ``__init__`` method that lingers will introduce a delay
to the initial call to `asdf.open`.  For that reason, we recommend that compressor
authors minimize the number of imports that occur in the module containing the
Compressor implementation, and defer imports of compression libraries to inside
the `Comrpessor.compress` and `Compressor.decompress` methods.  This will
prevent the library from ever being imported when reading ASDF files that
do not utilize the Compressor's algorithm.
