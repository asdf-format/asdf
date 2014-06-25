Examples
========

Hello World
-----------

In it's simplest form, Finf is a way of saving nested data structures
to YAML.  Here we save a dictionary with the key/value pair ``'hello':
'world'``.

.. runcode::

   from pyfinf import FinfFile

   # Make the tree structure, and create a FinfFile from it.
   tree = {'hello': 'world'}
   ff = FinfFile(tree)

   # You can also make the FinfFile first, and modify its tree directly:
   ff = FinfFile()
   ff.tree['hello'] = 'world'

   # Use the `with` construct so the file is automatically closed
   with ff.write_to("test.finf"):
       pass

.. finf:: test.finf

Saving arrays
-------------

Beyond the basic data types of dictionaries, lists, strings and
numbers, the most important thing Finf can save is arrays.  It's as
simple as putting a Numpy array somewhere in the tree.  Here, we save
an 8x8 array of random floating-point numbers.  Note that the YAML
part contains information about the structure (size and data type) of
the array, but the actual array content is in a binary block.

.. runcode::

   from pyfinf import FinfFile
   import numpy as np

   tree = {'my_array': np.random.rand(8, 8)}
   ff = FinfFile(tree)
   with ff.write_to("test.finf"):
       pass

.. finf:: test.finf

Schema validation
-----------------

In the current draft of the FINF schema, there are very few elements
defined at the top-level -- for the most part, the top-level can
contain any ad hoc elements.  One of the few specified elements is
``data``: it must be an array, and is used to specify the "main" data
content (for some definition of "main") so that tools that merely want
to view or preview the FINF file have a standard location to find the
most interesting data.  If you set this to anything but an array,
pyfinf will complain::

    >>> from pyfinf import FinfFile
    >>> tree = {'data': 'Not an array'}
    >>> FinfFile(tree)  # doctest: +SKIP
    ValidationError: mismatched tags, wanted
    'tag:stsci.edu:finf/0.1.0/core/ndarray', got
    'tag:yaml.org,2002:str'

This validation happens only when a `FinfFile` is instantiated, read or saved, so it's still possible to get the tree into an invalid intermediate state::

    >>> from pyfinf import FinfFile
    >>> ff = FinfFile()
    >>> ff.tree['data'] = 'Not an array'
    >>> # The FINF file is now invalid, but pyfinf will tell us when
    >>> # we write it out.
    >>> ff.write_to('test.finf')  # doctest: +SKIP
    ValidationError: mismatched tags, wanted
    'tag:stsci.edu:finf/0.1.0/core/ndarray', got
    'tag:yaml.org,2002:str'

Sharing of data
---------------

Arrays that are views on the same data automatically share the same
data in the file.  In this example an array and a subview on that same
array are saved to the same file, resulting in only a single block of
data being saved.

.. runcode::

   from pyfinf import FinfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   subset = my_array[2:4,3:6]
   tree = {
       'my_array': my_array,
       'subset':   subset
   }
   ff = FinfFile(tree)
   with ff.write_to("test.finf"):
       pass

.. finf:: test.finf


Saving inline arrays
--------------------

For these sort of small arrays, you may not care about the efficiency
of a binary representation and want to just save the content directly
in the YAML tree.  The ``blocks`` member of the ``FinfFile`` instance
can be used to set the type of block of the associated data, either
``internal``, ``external`` or ``inline``.

.. runcode::

   from pyfinf import FinfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = FinfFile(tree)
   ff.set_block_type(my_array, 'inline')
   with ff.write_to("test.finf"):
       pass

.. finf:: test.finf

Saving external arrays
----------------------

For various reasons discussion in the "Exploded Form" section of the
FINF specification, you may want to save the data in an external
block.

.. runcode::

   from pyfinf import FinfFile
   import numpy as np

   my_array = np.random.rand(8, 8)
   tree = {'my_array': my_array}
   ff = FinfFile(tree)
   ff.set_block_type(my_array, 'external')
   with ff.write_to("test.finf"):
       pass

.. finf:: test.finf

.. finf:: test0000.finf

Streaming array data
--------------------

In certain scenarios, you may want to stream data to disk, rather than
writing an entire array of data at once.  For example, it may not be
possible to fit the entire array in memory, or you may want to save
data from a device as it comes in to prevent loss.  The FINF standard
allows exactly one streaming block per file where the size of the
block isn't included in the block header, but instead is implicitly
determined to include all of the remaining contents of the file.  By
definition, it must be the last block in the file.

To use streaming, rather than including a Numpy array object in the
tree, you include a `pyfinf.Stream` object which sets up the structure
of the streamed data, but will not write out content to the file
automatically.

.. runcode::

   from pyfinf import FinfFile, Stream
   import numpy as np

   tree = {
       # Each "row" of data will have 128 entries.
       'my_stream': Stream([128], np.float64)
   }

   ff = FinfFile(tree)
   with ff.write_to('test.finf'):
       # Write 100 rows of data, one row at a time.
       # write_to_stream expects the raw binary bytes, not an array,
       # so we use `tostring()`
       for i in range(100):
           ff.write_to_stream(np.array([i] * 128, np.float64).tostring())

.. finf:: test.finf

References
----------

FINF files may reference items in the tree in other FINF files.  The
syntax used in the file for this is called "JSON Pointer", but the
Python programmer can largely ignore that.

First, we'll create a FINF file with a couple of arrays in it:

.. runcode::

   from pyfinf import FinfFile
   import numpy as np

   tree = {
       'a': np.arange(0, 10),
       'b': np.arange(10, 20)
   }

   target = FinfFile(tree)
   with target.write_to('target.finf'):
       pass

.. finf:: target.finf

Then we will reference those arrays in a couple of different ways.
First, we'll load the source file in Python and use the
`make_reference` method to generate a reference to array ``a``.
Second, we'll work at the lower level by manually writing a JSON
Pointer to array ``b``, which doesn't require loading or having access
to the target file.

.. runcode::

   ff = FinfFile()

   with FinfFile.read('target.finf') as target:
       ff.tree['my_ref_a'] = target.make_reference(['a'])

   ff.tree['my_ref_b'] = {'$ref': 'target.finf#b'}

   with ff.write_to('source.finf'):
       pass

.. finf:: source.finf

Calling `~pyfinf.FinfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   ff = FinfFile.read('source.finf')
   ff.find_references()
   assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~pyfinf.FinfFile.resolve_references`
places all of the referenced content directly in the tree, so when we
write it out again, all of the external references are gone, with the
literal content in its place.

.. runcode::

   ff = FinfFile.read('source.finf')
   ff.resolve_references()
   with FinfFile(ff).write_to('resolved.finf'):
       pass

.. finf:: resolved.finf

A similar feature provided by YAML, anchors and aliases, also provides
a way to support references within the same file.  These are supported
by pyfinf for reading, but there is no direct support for writing
them, since the JSON Pointer approach here is more powerful: it can
reference elements in another file by their physical location in the
tree, not just be an arbitrary identifier.
