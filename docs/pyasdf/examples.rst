.. _examples:

Examples
========

Hello World
-----------

In it's simplest form, ASDF is a way of saving nested data structures
to YAML.  Here we save a dictionary with the key/value pair ``'hello':
'world'``.

.. runcode::

   from pyasdf import AsdfFile

   # Make the tree structure, and create a AsdfFile from it.
   tree = {'hello': 'world'}
   ff = AsdfFile(tree)
   ff.write_to("test.asdf")

   # You can also make the AsdfFile first, and modify its tree directly:
   ff = AsdfFile()
   ff.tree['hello'] = 'world'
   ff.write_to("test.asdf")

.. asdf:: test.asdf

Saving arrays
-------------

Beyond the basic data types of dictionaries, lists, strings and
numbers, the most important thing ASDF can save is arrays.  It's as
simple as putting a Numpy array somewhere in the tree.  Here, we save
an 8x8 array of random floating-point numbers.  Note that the YAML
part contains information about the structure (size and data type) of
the array, but the actual array content is in a binary block.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   tree = {'my_array': np.random.rand(8, 8)}
   ff = AsdfFile(tree)
   ff.write_to("test.asdf")

.. note::

   In the file examples below, the first YAML part appears as it
   appears in the file.  The ``BLOCK`` sections are stored as binary
   data in the file, but are presented in human-readable form on this
   page.


.. asdf:: test.asdf

Schema validation
-----------------

In the current draft of the ASDF schema, there are very few elements
defined at the top-level -- for the most part, the top-level can
contain any elements.  One of the few specified elements is ``data``:
it must be an array, and is used to specify the "main" data content
(for some definition of "main") so that tools that merely want to view
or preview the ASDF file have a standard location to find the most
interesting data.  If you set this to anything but an array, ``pyasdf``
will complain::

    >>> from pyasdf import AsdfFile
    >>> tree = {'data': 'Not an array'}
    >>> AsdfFile(tree)
    Traceback (most recent call last):
    ...
    ValidationError: mismatched tags, wanted
    'tag:stsci.edu:asdf/core/ndarray-1.0.0', got
    'tag:yaml.org,2002:str'
    ...

This validation happens only when a `AsdfFile` is instantiated, read
or saved, so it's still possible to get the tree into an invalid
intermediate state::

    >>> from pyasdf import AsdfFile
    >>> ff = AsdfFile()
    >>> ff.tree['data'] = 'Not an array'
    >>> # The ASDF file is now invalid, but pyasdf will tell us when
    >>> # we write it out.
    >>> ff.write_to('test.asdf')
    Traceback (most recent call last):
    ...
    ValidationError: mismatched tags, wanted
    'tag:stsci.edu:asdf/core/ndarray-1.0.0', got
    'tag:yaml.org,2002:str'
    ...

Sharing of data
---------------

Arrays that are views on the same data automatically share the same
data in the file.  In this example an array and a subview on that same
array are saved to the same file, resulting in only a single block of
data being saved.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   subset = my_array[2:4,3:6]
   tree = {
       'my_array': my_array,
       'subset':   subset
   }
   ff = AsdfFile(tree)
   ff.write_to("test.asdf")

.. asdf:: test.asdf


Saving inline arrays
--------------------

For these sort of small arrays, you may not care about the efficiency
of a binary representation and want to just save the content directly
in the YAML tree.  The `~pyasdf.AsdfFile.set_array_storage` method
can be used to set the type of block of the associated data, either
``internal``, ``external`` or ``inline``.

- ``internal``: The default.  The array data will be
  stored in a binary block in the same ASDF file.

- ``external``: Store the data in a binary block in a
  separate ASDF file.

- ``inline``: Store the data as YAML inline in the tree.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = AsdfFile(tree)
   ff.set_array_storage(my_array, 'inline')
   ff.write_to("test.asdf")

.. asdf:: test.asdf

Saving external arrays
----------------------

ASDF files may also be saved in "exploded form", in multiple files:

- An ASDF file containing only the header and tree.

- *n* ASDF files, each containing a single block.

Exploded form is useful in the following scenarios:

- Not all text editors may handle the hybrid text and binary nature of
  the ASDF file, and therefore either can't open a ASDF file or would
  break a ASDF file upon saving.  In this scenario, a user may explode
  the ASDF file, edit the YAML portion as a pure YAML file, and
  implode the parts back together.

- Over a network protocol, such as HTTP, a client may only need to
  access some of the blocks.  While reading a subset of the file can
  be done using HTTP ``Range`` headers, it still requires one (small)
  request per block to "jump" through the file to determine the start
  location of each block.  This can become time-consuming over a
  high-latency network if there are many blocks.  Exploded form allows
  each block to be requested directly by a specific URI.

- An ASDF writer may stream a table to disk, when the size of the table
  is not known at the outset.  Using exploded form simplifies this,
  since a standalone file containing a single table can be iteratively
  appended to without worrying about any blocks that may follow it.

To save a block in an external file, set its block type to
``'external'``.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = AsdfFile(tree)

   # On an individual block basis:
   ff.set_array_storage(my_array, 'external')
   ff.write_to("test.asdf")

   # Or for every block:
   ff.write_to("test.asdf", all_array_storage='external')

.. asdf:: test.asdf

.. asdf:: test0000.asdf

Streaming array data
--------------------

In certain scenarios, you may want to stream data to disk, rather than
writing an entire array of data at once.  For example, it may not be
possible to fit the entire array in memory, or you may want to save
data from a device as it comes in to prevent data loss.  The ASDF
standard allows exactly one streaming block per file where the size of
the block isn't included in the block header, but instead is
implicitly determined to include all of the remaining contents of the
file.  By definition, it must be the last block in the file.

To use streaming, rather than including a Numpy array object in the
tree, you include a `pyasdf.Stream` object which sets up the structure
of the streamed data, but will not write out the actual content.  The
file handle's `write` method is then used to manually write out the
binary data.

.. runcode::

   from pyasdf import AsdfFile, Stream
   import numpy as np

   tree = {
       # Each "row" of data will have 128 entries.
       'my_stream': Stream([128], np.float64)
   }

   ff = AsdfFile(tree)
   with open('test.asdf', 'wb') as fd:
       ff.write_to(fd)
       # Write 100 rows of data, one row at a time.  ``write``
       # expects the raw binary bytes, not an array, so we use
       # ``tostring()``.
       for i in range(100):
           fd.write(np.array([i] * 128, np.float64).tostring())

.. asdf:: test.asdf

References
----------

ASDF files may reference items in the tree in other ASDF files.  The
syntax used in the file for this is called "JSON Pointer", but users
of ``pyasdf`` can largely ignore that.

First, we'll create a ASDF file with a couple of arrays in it:

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.arange(0, 10),
       'b': np.arange(10, 20)
   }

   target = AsdfFile(tree)
   target.write_to('target.asdf')

.. asdf:: target.asdf

Then we will reference those arrays in a couple of different ways.
First, we'll load the source file in Python and use the
`make_reference` method to generate a reference to array ``a``.
Second, we'll work at the lower level by manually writing a JSON
Pointer to array ``b``, which doesn't require loading or having access
to the target file.

.. runcode::

   ff = AsdfFile()

   with AsdfFile.open('target.asdf') as target:
       ff.tree['my_ref_a'] = target.make_reference(['a'])

   ff.tree['my_ref_b'] = {'$ref': 'target.asdf#b'}

   ff.write_to('source.asdf')

.. asdf:: source.asdf

Calling `~pyasdf.AsdfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   with AsdfFile.open('source.asdf') as ff:
       ff.find_references()
       assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~pyasdf.AsdfFile.resolve_references`
places all of the referenced content directly in the tree, so when we
write it out again, all of the external references are gone, with the
literal content in its place.

.. runcode::

   with AsdfFile.open('source.asdf') as ff:
       ff.resolve_references()
       ff.write_to('resolved.asdf')

.. asdf:: resolved.asdf

A similar feature provided by YAML, anchors and aliases, also provides
a way to support references within the same file.  These are supported
by pyasdf, however the JSON Pointer approach is generally favored because:

   - It is possible to reference elements in another file

   - Elements are referenced by location in the tree, not an
     identifier, therefore, everything can be referenced.

Anchors and aliases are handled automatically by ``pyasdf`` when the
data structure is recursive.  For example here is a dictionary that is
included twice in the same tree:

.. runcode::

    d = {'foo': 'bar'}
    d['baz'] = d
    tree = {'d': d}

    ff = AsdfFile(tree)
    ff.write_to('anchors.asdf')

.. asdf:: anchors.asdf

Compression
-----------

Individual blocks in an ASDF file may be compressed.

You can easily `zlib <http://www.zlib.net/>`__ or `bzip2
<http://www.bzip.org>`__ compress all blocks:

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(256, 256),
       'b': np.random.rand(512, 512)
   }

   target = AsdfFile(tree)
   target.write_to('target.asdf', all_array_compression='zlib')
   target.write_to('target.asdf', all_array_compression='bzp2')

.. asdf:: target.asdf

Saving history entries
----------------------

``pyasdf`` has a convenience method for notating the history of
transformations that have been performed on a file.

Given a `~pyasdf.AsdfFile` object, call
`~pyasdf.AsdfFile.add_history_entry`, given a description of the
change and optionally a description of the software (i.e. your
software, not ``pyasdf``) that performed the operation.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(256, 256)
   }

   ff = AsdfFile(tree)
   ff.add_history_entry(
       u"Initial random numbers",
       {u'name': u'pyasdf examples',
        u'author': u'John Q. Public',
        u'homepage': u'http://github.com/spacetelescope/pyasdf',
        u'version': u'0.1'})
   ff.write_to('example.asdf')

.. asdf:: example.asdf

Saving ASDF in FITS
-------------------

Sometimes you may need to store the structured data supported by ASDF
inside of a FITS file in order to be compatible with legacy tools that
support only FITS.  This can be achieved by including a special
extension with the name ``ASDF`` to the FITS file, containing the YAML
tree from an ASDF file.  The array tags within the ASDF tree point
directly to other binary extensions in the FITS file.

First, make a FITS file in the usual way with astropy.io.fits.  Here,
we are building a FITS file from scratch, but it could also have been
loaded from a file.

This FITS file has two image extensions, SCI and DQ respectively.

.. runcode::

    from astropy.io import fits

    hdulist = fits.HDUList()
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='SCI'))
    hdulist.append(fits.ImageHDU(np.arange(512, dtype=np.float), name='DQ'))

Next we make a tree structure out of the data in the FITS file.
Importantly, we use the *same* arrays in the FITS HDUList and store
them in the tree.  By doing this, pyasdf will be smart enough to point
to the data in the regular FITS extensions.

.. runcode::

    tree = {
        'model': {
            'sci': {
                'data': hdulist['SCI'].data,
            },
            'dq': {
                'data': hdulist['DQ'].data,
            }
        }
    }

Now we take both the FITS HDUList and the ASDF tree and create a
`~pyasdf.fits_embed.AsdfInFits` object.  It behaves identically to the
`~pyasdf.AsdfFile` object, but reads and writes this special
ASDF-in-FITS format.

.. runcode::

    from pyasdf import fits_embed

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to('embedded_asdf.fits')

.. runcode:: hidden

    with open('content.asdf', 'wb') as fd:
        fd.write(hdulist['ASDF'].data.tostring())

The special ASDF extension in the resulting FITS file looks like the
following.  Note that the data source of the arrays uses the ``fits:``
prefix to indicate that the data comes from a FITS extension.

.. asdf:: content.asdf

To load an ASDF-in-FITS file, first open it with ``astropy.io.fits``, and then
pass that HDU list to `~pyasdf.fits_embed.AsdfInFits`:


.. runcode::

    with fits.open('embedded_asdf.fits') as hdulist:
        with fits_embed.AsdfInFits.open(hdulist) as asdf:
            science = asdf.tree['model']['sci']
