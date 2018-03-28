*************
Core Features
*************

Data Model
==========

The fundamental data object in ASDF is the ``tree``, which is a nested
combination of basic data structures: dictionaries, lists, strings and numbers.
The top-level tree object behaves like a Python dictionary and supports
arbitrary nesting of data structures.

One of the key features of ASDF is its ability to serialize Numpy arrays. This
is discussed in detail in :ref:`array-data`.

While the core ASDF package supports serialization of a basic data types and
Numpy arrays, its true power comes from the ability to extend ASDF to support
serialization of a wide range of custom data types. Details on extending ASDF
to support custom data types can be found in :ref:`extensions`.

.. _array-data:

Array Data
==========

.. toctree::
    :maxdepth: 2

    arrays

Schema validation
=================

This section needs to be updated later.

Versioning and Compatibility
============================

There are several different versions to keep in mind when discussing ASDF:

* Software package version
* ASDF standard version
* ASDF file format version
* Individual tag and schema versions


ASDF is designed to serve as an archival format.

Using Extensions
================

External References
===================

Array References
----------------

ASDF files may reference items in the tree in other ASDF files.  The
syntax used in the file for this is called "JSON Pointer", but users
of ``asdf`` can largely ignore that.

First, we'll create a ASDF file with a couple of arrays in it:

.. runcode::

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

Calling `~asdf.AsdfFile.find_references` will look up all of the
references so they can be used as if they were local to the tree.  It
doesn't actually move any of the data, and keeps the references as
references.

.. runcode::

   with AsdfFile.open('source.asdf') as ff:
       ff.find_references()
       assert ff.tree['my_ref_b'].shape == (10,)

On the other hand, calling `~asdf.AsdfFile.resolve_references`
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
by asdf, however the JSON Pointer approach is generally favored because:

   - It is possible to reference elements in another file

   - Elements are referenced by location in the tree, not an
     identifier, therefore, everything can be referenced.

Anchors and aliases are handled automatically by ``asdf`` when the
data structure is recursive.  For example here is a dictionary that is
included twice in the same tree:

.. runcode::

    d = {'foo': 'bar'}
    d['baz'] = d
    tree = {'d': d}

    ff = AsdfFile(tree)
    ff.write_to('anchors.asdf')

.. asdf:: anchors.asdf

Array References
----------------

Saving history entries
======================

``asdf`` has a convenience method for notating the history of
transformations that have been performed on a file.

Given a `~asdf.AsdfFile` object, call
`~asdf.AsdfFile.add_history_entry`, given a description of the
change and optionally a description of the software (i.e. your
software, not ``asdf``) that performed the operation.

.. runcode::

   from asdf import AsdfFile
   import numpy as np

   tree = {
       'a': np.random.rand(256, 256)
   }

   ff = AsdfFile(tree)
   ff.add_history_entry(
       u"Initial random numbers",
       {u'name': u'asdf examples',
        u'author': u'John Q. Public',
        u'homepage': u'http://github.com/spacetelescope/asdf',
        u'version': u'0.1'})
   ff.write_to('example.asdf')

.. asdf:: example.asdf

Saving ASDF in FITS
===================

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
them in the tree.  By doing this, asdf will be smart enough to point
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
`~asdf.fits_embed.AsdfInFits` object.  It behaves identically to the
`~asdf.AsdfFile` object, but reads and writes this special
ASDF-in-FITS format.

.. runcode::

    from asdf import fits_embed

    ff = fits_embed.AsdfInFits(hdulist, tree)
    ff.write_to('embedded_asdf.fits')

.. runcode:: hidden

    from astropy.io import fits

    with fits.open('embedded_asdf.fits') as new_hdulist:
        with open('content.asdf', 'wb') as fd:
            fd.write(new_hdulist['ASDF'].data.tostring())

The special ASDF extension in the resulting FITS file looks like the
following.  Note that the data source of the arrays uses the ``fits:``
prefix to indicate that the data comes from a FITS extension.

.. asdf:: content.asdf

To load an ASDF-in-FITS file, first open it with ``astropy.io.fits``, and then
pass that HDU list to `~asdf.fits_embed.AsdfInFits`:


.. runcode::

    with fits.open('embedded_asdf.fits') as hdulist:
        with fits_embed.AsdfInFits.open(hdulist) as asdf:
            science = asdf.tree['model']['sci']
