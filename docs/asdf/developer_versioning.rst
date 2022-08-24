Tag Versioning and You
======================

Here we'll explore ASDF tag versioning, and walk through the process
of supporting new and updated tags with AsdfType subclasses.  AsdfType
is the original API that is currently used to support the ASDF core tags.
The new API, Converter, remains experimental and is currently (2020-09-24)
being trialled in the asdf-astropy package.

ASDF versioning conventions
---------------------------

The ASDF Standard document provides a helpful :ref:`overview <asdf-standard:versioning-conventions>`
of the various ASDF versioning conventions.  We will be concerned with the *standard version*
and individual *tag versions*.

Overview
--------

The "standard version" or "ASDF Standard version" refers to the subset
of individual tag versions that correspond to a specific release version
of the ASDF Standard.  The list of tags and versions is maintained in
version_map files in the asdf-standard repository.  For example,
version_map-1.3.0.yaml contains a list of all tag versions that
we must handle in order to fully support version 1.3.0 of the ASDF
Standard.  This list contains both "core" tags and non-core tags.
The distinction there is that core tags are supported by this library,
while the others are supported by some external Python library,
such as astropy.

Our support for specific versions of the ASDF core tags is implemented
with AsdfType subclasses.  We'll discuss these more later, but
for now the important thing to know is that each AsdfType class
identifies the tag name and version(s) that it supports.  Any core
tag objects that lack this support will not serialize or deserialize
properly.

When reading an ASDF file, the standard version doesn't play a
significant role.  Each core object is self-described
by a YAML tag, which will be used to deserialize the object even
if that tag conflicts with the overall standard version of the file.
The library will use the tag to identify the most appropriate
AsdfType to deserialize the object.

On write, the situation is different.  The library may have a choice
in which tag and/or AsdfType to use when serializing
a given core object -- if multiple versions of the same tag
are present, which shall we choose?  Here the standard version
becomes important.  The tag version selected is specified by
the version map of the standard version that the file is being
written under.

By default, the standard version used for writes is the latest
offered, but users may override with another version.

Implementation details
----------------------

Supported ASDF standard version list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The list of supported ASDF standard versions is maintained in
``asdf.versioning.supported_versions``.  The default version,
``asdf.versioning.default_version``, is applied whenever a user declines to
specify the standard version of a new file, and is set to the latest
supported version.

AsdfType
~~~~~~~~

In this library, each core tag is handled by a distinct
``asdf.types.AsdfType`` subclass.  The AsdfType subclass is responsible
for identifying the base name of its tag and the tag version(s)
that it supports.  It also provides any custom serialization/deserialization
behavior that is required -- AsdfType provides a default
implementation that is only able to get and set attributes on dict-like
objects.

In some cases, the AsdfType subclass also serves as the deserialized
object type.  For example, ``asdf.types.core.Software`` subclasses both
AsdfType and dict.  Its AsdfType-like behavior is
to identify its tag and version, while its dict-like behavior is
to act as a container for the attributes described by the tag.  The class
definition is mostly empty because as a dict it can rely on
AsdfType's default implementation for (de)serialization.

Meanwhile, other AsdfType subclasses deserialize ASDF objects
into instances of entirely separate classes.  For example,
``asdf.types.core.complex.ComplexType`` handles complex number types,
which aren't natively supported by YAML.  ComplexType includes
an additional class attribute, ``types``, that lists the types that
it is able to handle.  It also provides custom implementations
of the ``to_tree`` and ``from_tree`` class methods, which enable it to
serialize a complex value into the appropriate string, and later
rebuild the complex value from that string.  This additional code is
necessary because ComplexType does not (de)serialize itself.

We won't find an explicit list of AsdfType subclasses
in the code; that list is assembled at runtime by AsdfType's
metaclass, ``asdf.types.AsdfTypeMeta``.  The list can be inspected in
the console like so:

.. code-block:: pycon

    >>> import asdf
    >>> asdf.types._all_asdftypes  # doctest: +SKIP

The AsdfType class attributes relevant to versioning are as follows:

- *name*: the base name of the tag, without its version string.
  For example, the tag URI ``tag:stsci.edu:asdf/core/example-1.2.0`` will
  have a name value of ``"core/example"``.

- *version*: the primary tag version supported by the AsdfType.
  For the example above, version should be set to ``"1.2.0"``.  This should
  be the latest version that the tag supports.

- *supported_versions*: a set of tag versions that the AsdfType
  supports.  In the above example, this might be
  ``{"1.0.0", "1.1.0", "1.2.0"}``.

AsdfType selection rules
~~~~~~~~~~~~~~~~~~~~~~~~

On read, the library will ideally be able to identify an AsdfType
subclass that explicitly supports a given tag (either in the ``version``
class attribute or ``supported_versions``.  If that is not possible,
it proceeds as follows:

- Use the AsdfType that supports the latest version that is
  less than the tag version.  For example, if the tag is example-1.2.0,
  and AsdfType are available for 1.1.0 and 1.3.0, it will
  use the 1.1.0 subclass.
- If the above fails, use the earliest available AsdfType
- If no AsdfType exists that supports any version of that tag,
  then ASDF will deserialize the data into vanilla diff.

The library does not currently emit a warning in either of the
first two cases, but in the third case, a warning is emitted.

The rules for selecting an AsdfType for a given tag are implemented
by ``asdf.type_index.AsdfTypeIndex.fix_yaml_tag``.

On write, the library will read the version map that corresponds
to the ASDF Standard version in use, which dictates the subset of
tag versions that are available.  From the subset of AsdfType
subclasses that handle those tag versions, it selects the subclass
that is able to handle the type of the core object being serialized.

If an object is not supported by an AsdfType, its serialization will be
handled by pyyaml.  If pyyaml doesn't know how to serialize, it will
raise ``yaml.representer.RepresenterError``.

The rules for selecting an AsdfType for a given serializable object
are implemented by ``asdf.type_index.AsdfTypeIndex.from_custom_type``.

Implementing updates to the standard
------------------------------------

Let's assume that there is a new standard version, 2.0.0, which
includes one entirely new core tag, ``core/new_object-1.0.0``,
one backwards-compatible update to an existing tag,
``core/updated_object-1.1.0``, and one breaking change to an
existing tag, ``core/breaking_object-2.0.0``.  The following
sections walk through the steps we'll need to take to support
this new material.

Update the asdf-standard submodule commit pointer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The asdf-standard repository is integrated into the asdf repository
as a submodule.  To pull in new commits from the remote master (
assumed to be named ``origin``:

.. code-block:: console

    $ cd asdf-standard
    $ git fetch origin
    $ git checkout origin/master

Support the new standard version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The list can be found in ``asdf.versioning.supported_versions``.
Add ``AsdfVersion("2.0.0")`` to the end of the list
(maintaining the sort order).  This new version will become the default
for new files, but we can update the definition of
``asdf.versioning.default_version`` if that is undesirable.

Support the new tag
~~~~~~~~~~~~~~~~~~~

Tags for previously unsupported objects are straightforward, since
we don't need to worry about compatibility issues.  Create a new
AsdfType subclass with ``name`` and ``version`` set appropriately:

.. code-block:: python

    class NewObjectType(AsdfType):
        name = "core/new_object"
        version = "1.0.0"

In a real-life scenario, we'd need to actually support (de)serialization
in some way, but those details are beyond the scope of this document.

Support the backwards-compatible tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since our updated_object-1.1.0 is backwards-compatible,
we can share the same AsdfType subclass between it and the previous
version.  Presumably there exists an AsdfType that looks something
like this:

.. code-block:: python

    class UpdatedObjectType(AsdfType):
        name = "core/updated_object"
        version = "1.0.0"

We'll need to update the version, and list 1.0.0 as a supported
version, so that this class can continue to handle it:

.. code-block:: python

    class UpdatedObjectType(AsdfType):
        name = "core/updated_object"
        version = "1.1.0"
        supported_versions = {"1.0.0", "1.1.0"}

Support the breaking tag
~~~~~~~~~~~~~~~~~~~~~~~~

The tag with breaking changes, core/breaking_object-2.0.0,
may not be easily supported by the same AsdfType as the previous
version.  In that case, we can create a new AsdfType for 2.0.0,
and as long as the two subclasses have distinct ``version`` values
and non-overlapping ``supported_versions`` sets, they should coexist
peaceably.

If this is the existing AsdfType:

.. code-block:: python

    class BreakingObjectType(AsdfType):
        name = "core/breaking_object"
        version = "1.0.0"

The new AsdfType might look something like this:

.. code-block:: python

    class BreakingObjectType2(AsdfType):
        name = "core/breaking_object"
        version = "2.0.0"

**CAUTION:** We might be tempted here to simply update the original
BreakingObjectType, but failing to handle an older version of the tag
constitutes dropping support for any ASDF Standard version that relies
on that tag.  This should only be done after a deprecation period and
with a major version release of the library, since files written by an
older release will not be readable by the new code.
