.. currentmodule:: asdf

*************
Core Features
*************


This section discusses the core features of the ASDF data format, and provides
examples and use cases that are specific to the Python implementation.

.. _data-model:

Data Model
==========

The fundamental data object in ASDF is the ``tree``, which is a nested
combination of basic data structures: dictionaries, lists, strings and numbers.
In Python, these types correspond to :class:`dict`, :class:`list`,
:class:`str`, and :class:`int`, :class:`float`, and :class:`complex`,
respectively. The top-level tree object behaves like a Python dictionary and
supports arbitrary nesting of data structures. For simple examples of creating
and reading trees, see :ref:`overview`.

.. note::

   The ASDF Standard imposes a maximum size of 64-bit signed integers literals in
   the tree (see :ref:`asdf-standard:literal_integers` for details and justification).
   Attempting to store a larger value as a YAML literal will result in a validation
   error.

   For arbitrary precision integer support, see `IntegerType`.

   Integers and floats of up to 64 bits can be stored inside of :mod:`numpy`
   arrays (see below).

.. note::

   The ASDF standard does not have an immutable sequence type that maps directly
   to Python's :class:`tuple`. Following the behavior of
   pyyaml, asdf writes tuples as YAML sequences, which when loaded
   are converted to lists. If round-tripping of tuples is important
   to your application see :ref:`extending` to write a custom extension
   to save and load tuples.

One of the key features of `asdf` is its ability to serialize :mod:`numpy`
arrays. This is discussed in detail in :ref:`array-data`.

While the core `asdf` package supports serialization of basic data types and
Numpy arrays, its true power comes from its ability to be extended to support
serialization of a wide range of custom data types. Details on using ASDF
extensions can be found in :ref:`using_extensions`. Details on creating custom
ASDF extensions to support custom data types can be found in :ref:`extending`.

.. _array-data:

Array Data
==========

Much of ASDF's power and convenience comes from its ability to represent
multidimensional array data. The :mod:`asdf` Python package provides native
support for :mod:`numpy` arrays.

.. toctree::
    :maxdepth: 2

    arrays

.. _using_extensions:

Using extensions
================

According to Wikipedia, serialization "is the process of translating data
structures or object state into a format that can be stored...and reconstructed
later" [#wiki]_.

The power of ASDF is that it provides the ability to store, or serialize, the
state of Python objects into a *human-readable* data format. The state of those
objects can later be restored by another program in a process called
deserialization.

While ASDF is capable of serializing basic Python types and Numpy arrays out of
the box, it can also be extended to serialize arbitrary custom data types. This
section discusses the extension mechanism from a user's perspective. For
documentation on creating extensions, see :ref:`extending_extensions`.

Even though this particular implementation of ASDF necessarily serializes
Python data types, in theory an ASDF implementation in another language could
read the resulting file and reconstruct an analogous type in that language.
Conversely, this implementation can read ASDF files that were written by other
implementations of ASDF as long as the proper extensions are available.

.. toctree::
    :maxdepth: 2

    using_extensions

.. _schema_validation:

Schema validation
=================

Schema validation is used to determine whether an ASDF file is well formed. All
ASDF files must conform to the schemas defined by the :ref:`ASDF Standard
<asdf-standard:asdf-standard>`. Schema validation can be run using `AsdfFile.validate`
and occurs when reading ASDF files (using `asdf.open`) and writing them out
(using `AsdfFile.write_to` or `AsdfFile.update`).

Schema validation also plays a role when using custom extensions (see
:ref:`using_extensions` and :ref:`extending_extensions`). Extensions must provide schemas
for the types that they serialize. When writing a file with custom types, the
output is validated against the schemas corresponding to those types. If the
appropriate extension is installed when reading a file with custom types, then
the types will be validated against the schemas provided by the corresponding
extension.

.. _custom-schemas:

Custom schemas
--------------

Every ASDF file is validated against the ASDF Standard, and also against any
schemas provided by custom extensions. However, it is sometimes useful for
particular applications to impose additional restrictions when deciding whether
a given file is valid or not.

For example, consider an application that processes digital image data. The
application expects the file to contain an image, and also some metadata about
how the image was created. The following example schema reflects these
expectations:

.. code:: yaml

    %YAML 1.1
    ---
    id: "http://example.com/schemas/your-custom-schema"
    $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"

    type: object
    properties:
      image:
        description: An ndarray containing image data.
        $ref: "ndarray-1.0.0"

      metadata:
        type: object
        description: Metadata about the image
        properties:
          time:
            description: |
              A timestamp for when the image was created, in UTC.
            type: string
            format: date-time
          resolution:
            description: |
              A 2D array representing the resolution of the image (N x M).
            type: array
            items:
              type: integer
              number: 2

    required: [image, metadata]
    additionalProperties: true

This schema restricts the kinds of files that will be accepted as valid to
those that contain a top-level ``image`` property that is an ``ndarray``, and
a top-level ``metadata`` property that contains information about the time the
image was taken and the resolution of the image.

In order to use this schema for a secondary validation pass, we pass the
``custom_schema`` argument to either `asdf.open` or the `AsdfFile` constructor.
Assume that the schema file lives in ``image_schema.yaml``, and we wish to
open a file called ``image.asdf``. We would open the file with the following
code:

.. code::

    import asdf
    af = asdf.open('image.asdf', custom_schema='image_schema.yaml')

Similarly, if we wished to use this schema when creating new files:

.. code::

    new_af = asdf.AsdfFile(custom_schema='image_schema.yaml')
    ...

If your custom schema is registered with ASDF in an extension, you may
pass the schema URI (``http://example.com/schemas/your-custom-schema``, in this
case) instead of a file path.

.. _top-level core schema:
.. note::
    The top-level core schemas can be found :ref:`here <asdf-standard:core-schema>`.

.. _version_and_compat:

Versioning and Compatibility
============================

There are several different versions to keep in mind when discussing ASDF:

* The software package version
* The ASDF Standard version
* The ASDF file format version
* Individual tag, schema, and extension versions

Each ASDF file contains information about the various versions that were used
to create the file. The most important of these are the ASDF Standard version
and the ASDF file format version. A particular version of the ASDF software
package will explicitly provide support for specific combinations of these
versions.

Tag, schema, and extension versions are also important for serializing and
deserializing data types that are stored in ASDF files. A detailed discussion
of these versions from a user perspective can be found in :ref:`custom_type_versions`.

Since ASDF is designed to serve as an archival format, this library is careful
to maintain backwards compatibility with older versions of the ASDF Standard, ASDF
file format, and core tags.  However, since deserializing custom tags
requires other software packages, backwards compatibility is often
contingent on the available versions of such software packages.

In general, forward compatibility with newer versions of the ASDF Standard and
ASDF file format is not supported by the software.

When creating new ASDF files, it is possible to control the version of the ASDF
standard that is used. This can be specified by passing the ``version`` argument to
either the `AsdfFile` constructor when the file object is created, or to the
`AsdfFile.write_to` method when it is written. By default, the latest stable
version of the ASDF standard will be used.

.. warning::
   Take care when providing ``version`` to `AsdfFile.write_to` to select a version
   that is stable. Writing files with a ``development`` (unstable) version may
   produce files that will become unreadable as that version evolves. The default
   version will always be stable and is often the best choice unless you are trying
   to write out a file that is readable by older software (where you will want to
   use an older, stable version).

External References
===================

Tree References
---------------

ASDF files may reference items in the tree in other ASDF files.  The
syntax used in the file for this is called "JSON Pointer", but users
of `asdf` can largely ignore that.

First, we'll create a ASDF file with a couple of arrays in it:

.. runcode::

   import asdf
   from asdf import AsdfFile
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
``make_reference`` method to generate a reference to array ``a``.
Second, we'll work at the lower level by manually writing a JSON
Pointer to array ``b``, which doesn't require loading or having access
to the target file.

.. runcode::

   ff = AsdfFile()

   with asdf.open('target.asdf') as target:
       ff.tree['my_ref_a'] = target.make_reference(['a'])

   ff.tree['my_ref_b'] = {'$ref': 'target.asdf#b'}

   ff.write_to('source.asdf')

.. asdf:: source.asdf

Calling `~asdf.AsdfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   with asdf.open('source.asdf') as ff:
       ff.find_references()
       assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~asdf.AsdfFile.resolve_references`
places all of the referenced content directly in the tree, so when we
write it out again, all of the external references are gone, with the
literal content in its place.

.. runcode::

   with asdf.open('source.asdf') as ff:
       ff.resolve_references()
       ff.write_to('resolved.asdf')

.. asdf:: resolved.asdf

A similar feature provided by YAML, anchors and aliases, also provides
a way to support references within the same file.  These are supported
by `asdf`, however the JSON Pointer approach is generally favored because:

   - It is possible to reference elements in another file

   - Elements are referenced by location in the tree, not an
     identifier, therefore, everything can be referenced.

Anchors and aliases are handled automatically by `asdf` when the
data structure is recursive.  For example here is a dictionary that is
included twice in the same tree:

.. runcode::

    d = {'foo': 'bar'}
    d['baz'] = d
    tree = {'d': d}

    ff = AsdfFile(tree)
    ff.write_to('anchors.asdf')

.. asdf:: anchors.asdf

.. _array-references:

Array References
----------------

ASDF files can refer to array data that is stored in other files using the
`ExternalArrayReference` type.

External files need not be ASDF files: ASDF is completely agnostic as to the
format of the external file. The ASDF external array reference does not define
how the external data file will be resolved; in fact it does not even check for
the existence of the external file. It simply provides a way for ASDF files to
refer to arrays that exist in external files.

Creating an external array reference is simple. Only four pieces of information
are required:

* The name of the external file. Since ASDF does not itself resolve the file or
  check for its existence, the format of the name is not important. In most
  cases the name will be a path relative to the ASDF file itself, or a URI
  for a network resource.
* The data type of the array data. This is a string representing any valid
  `numpy.dtype`.
* The shape of the data array. This is a tuple representing the dimensions of
  the array data.
* The array data ``target``. This is either an integer or a string that
  indicates to the user something about how the data array should be accessed
  in the external file. For example, if there are multiple data arrays in the
  external file, the ``target`` might be an integer index. Or if the external
  file is an ASDF file, the ``target`` might be a string indicating the key to
  use in the external file's tree. The value and format of the ``target`` field
  is completely arbitrary since ASDF will not use it itself.

As an example, we will create a reference to an external CSV file. We will
assume that one of the rows of the CSV file contains the array data we care
about:

.. runcode::

    import asdf

    csv_data_row = 10 # The row of the CSV file containing the data we want
    csv_row_size = 100 # The size of the array
    extref = asdf.ExternalArrayReference('data.csv', csv_data_row, "int64", (csv_row_size,))

    tree = {'csv_data': extref}
    af = asdf.AsdfFile(tree)
    af.write_to('external_array.asdf')

.. asdf:: external_array.asdf

When reading a file containing external references, the user is responsible for
using the information in the `ExternalArrayReference` type to open the external
file and retrieve the associated array data.

Saving history entries
======================

`asdf` has a convenience method for notating the history of transformations
that have been performed on a file.

Given a `~asdf.AsdfFile` object, call `~asdf.AsdfFile.add_history_entry`, given
a description of the change and optionally a description of the software (i.e.
your software, not `asdf`) that performed the operation.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(32, 32)
   }

   ff = AsdfFile(tree)
   ff.add_history_entry(
       "Initial random numbers",
       {'name': 'asdf examples',
        'author': 'John Q. Public',
        'homepage': 'http://github.com/asdf-format/asdf',
        'version': '0.1'})
   ff.write_to('example.asdf')

.. asdf:: example.asdf

`asdf` automatically saves history metadata about the extensions that were used
to create the file. This information is used when opening files to determine if
the proper extensions are installed (see :ref:`extension_checking` for more
details).

.. rubric:: Footnotes

.. [#wiki] https://en.wikipedia.org/wiki/Serialization

Rendering ASDF trees
====================

The `asdf.info` function prints a representation of an ASDF
tree to stdout.  For example:

.. code:: pycon

    >>> asdf.info("path/to/some/file.asdf")  # doctest: +SKIP
    root (AsdfObject)
    ├─asdf_library (Software)
    │ ├─author (str): The ASDF Developers
    │ ├─homepage (str): http://github.com/asdf-format/asdf
    │ ├─name (str): asdf
    │ └─version (str): 2.5.1
    ├─history (dict)
    │ └─extensions (list) ...
    └─data (dict)
      └─example_key (str): example value

The first argument may be a ``str`` or ``pathlib.Path`` filesystem path,
or an `AsdfFile` or sub-node of an ASDF tree.

By default, `asdf.info` limits the number of lines, and line length,
of the displayed tree.  The ``max_rows`` parameter controls the number of
lines, and ``max_cols`` controls the line length.  Set either to ``None`` to
disable that limit.

An integer ``max_rows`` will be interpreted as an overall limit on the
number of displayed lines.  If ``max_rows`` is a tuple, then each member
limits lines per node at the depth corresponding to its tuple index.
For example, to show all top-level nodes and 5 of each's children:

.. code:: pycon

    >>> asdf.info("file.asdf", max_rows=(None, 5))  # doctest: +SKIP

If the attribute is described in a schema, the info functionality
will see if it has an associated title and if it does, display it
as a comment on the same line. This provides a way for users to
see more information about the attribute, similar to the way
FITS header comments are used.

The `AsdfFile.info` method behaves similarly to `asdf.info`, rendering
the tree of the associated `AsdfFile`.

Normally `asdf.info` will not show the contents of asdf nodes turned
into Python custom objects, but if that object supports a special
method, you may see the contents of such objects.
See :ref:`exposing_extension_object_internals` for how
to implement such support for `asdf.info` and `asdf.search`.

Searching the ASDF tree
=======================

The `AsdfFile` search interface provides a way to interactively discover the
locations and values of nodes within the ASDF tree.  We can search for
nodes by key/index, type, or value.

Basic usage
-----------

Initiate a search by calling `AsdfFile.search` on an open file:

.. code:: pycon

    >>> af.search()  # doctest: +SKIP
    root (AsdfObject)
    ├─asdf_library (Software)
    │ ├─author (str): The ASDF Developers
    │ ├─homepage (str): http://github.com/asdf-format/asdf
    │ ├─name (str): asdf
    │ └─version (str): 2.5.1
    ├─history (dict)
    │ └─extensions (list) ...
    └─data (dict)
      └─example_key (str): example value

    >>> af.search("example")  # doctest: +SKIP
    root (AsdfObject)
    └─data (dict)
      └─example_key (str): example value

.. currentmodule:: asdf.search

The search returns an `AsdfSearchResult` object that displays in
the Python console as a rendered tree.  For single-node search
results, the `AsdfSearchResult.path` property contains the Python code required to
reference that node directly:

.. code:: pycon

    >>> af.search("example").path  # doctest: +SKIP
    "root['data']['example_key']"

While the `AsdfSearchResult.node` property contains the actual value of the node:

.. code:: pycon

   >>> af.search("example").node  # doctest: +SKIP
   'example value'

For searches with multiple matching nodes, use the `AsdfSearchResult.paths` and `AsdfSearchResult.nodes`
properties instead:

.. code:: pycon

    >>> af.search("duplicate_key").paths  # doctest: +SKIP
    ["root['data']['duplicate_key']", "root['other_data']['duplicate_key']"]
    >>> af.search("duplicate_key").nodes  # doctest: +SKIP
    ["value 1", "value 2"]

To replace matching nodes with a new value, use the `AsdfSearchResult.replace` method:

.. code:: pycon

    >>> af.search("example").replace("replacement value")  # doctest: +SKIP
    >>> af.search("example").node  # doctest: +SKIP
    'replacement value'

.. currentmodule:: asdf

The first argument to `AsdfFile.search` searches by dict key or list/tuple index.  We can
also search by type, value, or any combination thereof:

.. code:: pycon

   >>> af.search("foo")  # Find nodes with key containing the string 'foo' # doctest: +SKIP
   >>> af.search(type_=int)  # Find nodes that are instances of int # doctest: +SKIP
   >>> af.search(value=10)  # Find nodes whose value is equal to 10 # doctest: +SKIP
   >>> af.search(
   ...     "foo", type_=int, value=10
   ... )  # Find the intersection of the above # doctest: +SKIP

Chaining searches
-----------------

The return value of `AsdfFile.search`, `asdf.search.AsdfSearchResult`, has its own search method,
so it's possible to chain searches together.  This is useful when you need
to see intermediate results before deciding how to further narrow the search.

.. code:: pycon

    >>> af.search()  # See an overview of the entire ASDF tree # doctest: +SKIP
    >>> af.search().search(type_="NDArrayType")  # Find only ndarrays # doctest: +SKIP
    >>> af.search().search(type_="NDArrayType").search(
    ...     "err"
    ... )  # Only ndarrays with 'err' in the key # doctest: +SKIP

Descending into child nodes
---------------------------

Another way to narrow the search is to use the index operator to descend into
a child node of the current tree root:

.. code:: pycon

    >>> af.search()["data"]  # Restrict search to the 'data' child # doctest: +SKIP
    >>> af.search()["data"].search(
    ...     type_=int
    ... )  # Find integer descendants of 'data' # doctest: +SKIP

Regular expression searches
---------------------------

Any string argument to search is interpreted as a regular expression.  For example,
we can search for nodes whose keys start with a particular string:

.. code:: pycon

    >>> af.search("foo")  # Find nodes with 'foo' anywhere in the key # doctest: +SKIP
    >>> af.search("^foo")  # Find only nodes whose keys start with 'foo' # doctest: +SKIP

Note that all node keys (even list indices) will be converted to string before
the regular expression is matched:

.. code:: pycon

   >>> af.search("^7$")  # Returns all nodes with key '7' or index 7 # doctest: +SKIP

When the ``type_`` argument is a string, the search compares against the fully-qualified
class name of each node:

.. code:: pycon

    >>> af.search(
    ...     type_="asdf.tags.core.Software"
    ... )  # Find instances of ASDF's Software type # doctest: +SKIP
    >>> af.search(type_="^asdf\.")  # Find all ASDF objects # doctest: +SKIP

When the ``value`` argument is a string, the search compares against the string
representation of each node's value.

.. code:: pycon

    >>> af.search(
    ...     value="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ... )  # Find values that look like dates # doctest: +SKIP

Arbitrary search criteria
-------------------------

If ``key``, ``type_``, and ``value`` aren't sufficient, we can also provide a callback
function to search by arbitrary criteria.  The ``filter_`` parameter accepts
a callable that receives the node under consideration, and returns ``True``
to keep it or ``False`` to reject it from the search results.  For example,
to search for NDArrayType with a particular shape:

.. code:: pycon

    >>> af.search(type_="NDArrayType", filter_=lambda n: n.shape[0] == 1024)  # doctest: +SKIP

Formatting search results
-------------------------

.. currentmodule:: asdf.search

The `AsdfSearchResult` object displays its content as a rendered tree with
reasonable defaults for maximum number of lines and columns displayed.  To
change those values, we call `AsdfSearchResult.format`:

.. code:: pycon

    >>> af.search(type_=float)  # Displays limited rows # doctest: +SKIP
    >>> af.search(type_=float).format(max_rows=None)  # Show all matching rows # doctest: +SKIP

Like `AsdfSearchResult.search`, calls to format may be chained:

.. code:: pycon

    >>> af.search("time").format(max_rows=10).search(type_=str).format(
    ...     max_rows=None
    ... )  # doctest: +SKIP


Searching Schema information
============================

In some cases, one may wish to include information and/or documentation about
an object defined by a tagged schema within the schema itself. It can be useful
to directly access this information relative to a given ASDF file. For example
one may wish to examine:

* The ``title`` of a value to get a short description of it.
* The ``description`` of a value to get the longer description of it.

In other cases, it may be useful to store general descriptive information such as
specific archival information about a given value in the file so that an archive
can easily ingest the file into the archive, such as what is done with the ``archive_catalog``
information in the `rad schemas <https://github.com/spacetelescope/rad>`_ for the
Nancy Grace Roman Space Telescope.

.. currentmodule:: asdf

The `AsdfFile.schema_info` method provides a way to access this information. This
method returns a nested tree of dictionaries which contains tuples consisting of
the information from the schema requested together with the value stored in the
ASDF file itself.

One needs to provide a ``key``, which corresponds to the keyword the information
is stored under inside the schema; by default this is ``description``. One can also
provide a ``path`` in the form of a dot-separated string of the keys in the
ASDF file that lead to the value(s) of interest. For example:

.. code:: pycon

    >>> af.schema_info("archive_catalog", "foo.bar")  # doctest: +SKIP
    {'thing1': {'archive_catalog': 'Thing 1 Archive catalog information'},
     'thing2': {'archive_catalog': 'Thing 2 Archive catalog information'}}

Or one can provide a ``path`` as an `asdf.search.AsdfSearchResult` object:

.. code:: pycon

    >>> af.schema_info("archive_catalog", af.search("bar"))  # doctest: +SKIP
    {'thing1': {'archive_catalog': 'Thing 1 Archive catalog information'},
     'thing2': {'archive_catalog': 'Thing 2 Archive catalog information'}}


.. note::
    There is also the `asdf.search.AsdfSearchResult.schema_info` method,
    which can be directly called on an `asdf.search.AsdfSearchResult` object,
    instead of passing the search through `AsdfFile.schema_info`.
