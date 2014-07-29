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

   # You can also make the AsdfFile first, and modify its tree directly:
   ff = AsdfFile()
   ff.tree['hello'] = 'world'

   # Use the `with` construct so the file is automatically closed
   with ff.write_to("test.asdf"):
       pass

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
   with ff.write_to("test.asdf"):
       pass

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
contain any ad hoc elements.  One of the few specified elements is
``data``: it must be an array, and is used to specify the "main" data
content (for some definition of "main") so that tools that merely want
to view or preview the ASDF file have a standard location to find the
most interesting data.  If you set this to anything but an array,
pyasdf will complain::

    >>> from pyasdf import AsdfFile
    >>> tree = {'data': 'Not an array'}
    >>> AsdfFile(tree)
    Traceback (most recent call last):
    ...
    ValidationError: mismatched tags, wanted
    'tag:stsci.edu:asdf/0.1.0/core/ndarray', got
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
    'tag:stsci.edu:asdf/0.1.0/core/ndarray', got
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
   with ff.write_to("test.asdf"):
       pass

.. asdf:: test.asdf


Saving inline arrays
--------------------

For these sort of small arrays, you may not care about the efficiency
of a binary representation and want to just save the content directly
in the YAML tree.  The `~pyasdf.AsdfFile.set_block_type` method
can be used to set the type of block of the associated data, either
``internal``, ``external`` or ``inline``.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = AsdfFile(tree)
   ff.set_block_type(my_array, 'inline')
   with ff.write_to("test.asdf"):
       pass

.. asdf:: test.asdf

Saving external arrays
----------------------

For various reasons discussed in the "Exploded Form" section of the
ASDF specification, you may want to save the data in an external
block.

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = AsdfFile(tree)
   ff.set_block_type(my_array, 'external')
   with ff.write_to("test.asdf"):
       pass

.. asdf:: test.asdf

.. asdf:: test0000.asdf

Streaming array data
--------------------

In certain scenarios, you may want to stream data to disk, rather than
writing an entire array of data at once.  For example, it may not be
possible to fit the entire array in memory, or you may want to save
data from a device as it comes in to prevent loss.  The ASDF standard
allows exactly one streaming block per file where the size of the
block isn't included in the block header, but instead is implicitly
determined to include all of the remaining contents of the file.  By
definition, it must be the last block in the file.

To use streaming, rather than including a Numpy array object in the
tree, you include a `pyasdf.Stream` object which sets up the structure
of the streamed data, but will not write out the actual content.  The
`~pyasdf.AsdfFile.write_to_stream` method is then later used to
manually write out the binary data.

.. runcode::

   from pyasdf import AsdfFile, Stream
   import numpy as np

   tree = {
       # Each "row" of data will have 128 entries.
       'my_stream': Stream([128], np.float64)
   }

   ff = AsdfFile(tree)
   with ff.write_to('test.asdf'):
       # Write 100 rows of data, one row at a time.
       # write_to_stream expects the raw binary bytes, not an array,
       # so we use `tostring()`
       for i in range(100):
           ff.write_to_stream(np.array([i] * 128, np.float64).tostring())

.. asdf:: test.asdf

References
----------

ASDF files may reference items in the tree in other ASDF files.  The
syntax used in the file for this is called "JSON Pointer", but the
Python programmer can largely ignore that.

First, we'll create a ASDF file with a couple of arrays in it:

.. runcode::

   from pyasdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.arange(0, 10),
       'b': np.arange(10, 20)
   }

   target = AsdfFile(tree)
   with target.write_to('target.asdf'):
       pass

.. asdf:: target.asdf

Then we will reference those arrays in a couple of different ways.
First, we'll load the source file in Python and use the
`make_reference` method to generate a reference to array ``a``.
Second, we'll work at the lower level by manually writing a JSON
Pointer to array ``b``, which doesn't require loading or having access
to the target file.

.. runcode::

   ff = AsdfFile()

   with AsdfFile.read('target.asdf') as target:
       ff.tree['my_ref_a'] = target.make_reference(['a'])

   ff.tree['my_ref_b'] = {'$ref': 'target.asdf#b'}

   with ff.write_to('source.asdf'):
       pass

.. asdf:: source.asdf

Calling `~pyasdf.AsdfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   ff = AsdfFile.read('source.asdf')
   ff.find_references()
   assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~pyasdf.AsdfFile.resolve_references`
places all of the referenced content directly in the tree, so when we
write it out again, all of the external references are gone, with the
literal content in its place.

.. runcode::

   ff = AsdfFile.read('source.asdf')
   ff.resolve_references()
   with AsdfFile(ff).write_to('resolved.asdf'):
       pass

.. asdf:: resolved.asdf

A similar feature provided by YAML, anchors and aliases, also provides
a way to support references within the same file.  These are supported
by pyasdf, however the JSON Pointer approach is generally favored because:

   - It is possible to reference elements in another file

   - Elements are referenced by location in the tree, not an
     identifier, therefore, everything can be referenced.
