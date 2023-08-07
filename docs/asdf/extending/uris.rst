.. _extending_uris:

============
URIs in ASDF
============

The ASDF format uses `Uniform Resource Identifiers <https://en.wikipedia.org/wiki/Uniform_Resource_Identifier>`__ to refer to various
entities such as schemas or tags.  These are string identifiers used to
uniquely identify the associated entity.  Here are some examples
of URIs that might be encountered in an ASDF file:

- ``asdf://example.com/schemas/foo-1.0.0`` (URI of the foo-1.0.0 schema)
- ``tag:stsci.edu:asdf/core/asdf-1.1.0`` (URI of the asdf-1.0.0 YAML tag)
- ``http://stsci.edu/schemas/asdf/core/ndarray-1.0.0`` (URI of the ndarray-1.0.0 schema)

Each of these uses a different URI *scheme*, and each is a valid URI format in ASDF.

URI vs URL
==========

One common point of confusion is the distinction between a URI and a URL.  The two are easily
conflated -- for example, consider the URI of the ndarray-1.0.0 schema above.

``http://stsci.edu/schemas/asdf/core/ndarray-1.0.0``

This string looks just like the URL of a web page, but if we were to attempt to visit that location
in a browser, we'd get a 404 Not Found from stsci.edu.  And yet it is still a valid URI!

The similarity arises from the need for URIs to be globally unique.  Since web domains are
already controlled by a single organization or individual, they offer a convenient way to
define URIs -- just reserve some path prefix off a domain you control and dole out strings
with that prefix where unique identifiers are needed.  But using ``http://`` as a URI scheme has the
downside that users expect to be able to retrieve the document contents from that address.

The asdf:// URI scheme
======================

To counter the problem of URIs vs URLs, `asdf` 2.8 introduced support for the ``asdf://`` URI
scheme.  These URIs are constructed just like ``http://`` or ``https://`` URIs, but the ASDF-specific
scheme makes clear that the content cannot be fetched from a webserver.

Entities identified by URI
==========================

The following is a complete list of entity types that are identified by URI in ASDF:

.. _extending_uris_entities_schemas:

Schemas
-------

Schemas are expected to include an ``id`` property that contains the URI that identifies them.
That URI is used when referring to the schema in calls to `asdf` library functions.
We recommend the following pattern for schema URIs:

``asdf://<domain>/<project>/schemas/<name>-<version>``

Where ``<domain>`` is some domain that you control, ``<project>`` collects all entities
for a particular ASDF project, ``<name>`` is the name of the schema, and ``<version>``
is the schema's version number.  For example:

``asdf://example.com/example-project/schemas/foo-1.2.3``

.. _extending_uris_entities_tags:

Tags
----

Tags, which annotate typed objects in an ASDF file's YAML tree, are represented as URIs.  Unlike
schemas, there is no resource associated with the tag; no blob of bytes exists that corresponds
to the URI.  Instead, the URI alone communicates the type of a YAML object.  We recommend
the following pattern for tag URIs:

``asdf://<domain>/<project>/tags/<name>-<version>``

Where ``<domain>`` is some domain that you control, ``<project>`` collects all entities
for a particular ASDF project, ``<name>`` is the name of the tag, and ``<version>``
is the tag's version number.  For example:

``asdf://example.com/example-project/tags/foo-1.2.3``

Manifests
---------

Manifest documents are language-independent definitions of extensions to ASDF and
include an ``id`` property that contains the URI that identifies them.  That URI is
used when referring to the manifest in calls to `asdf` library functions.  We
recommend the following pattern for manifest URIs:

``asdf://<domain>/<project>/manifests/<name>-<version>``

Where ``<domain>`` is some domain that you control, ``<project>`` collects all entities
for a particular ASDF project, ``<name>`` is the name of the manifest, and ``<version>``
is the manifest's version number.  For example:

``asdf://example.com/example-project/manifests/foo-1.2.3``

Extensions
----------

Finally, extensions URIs identify extensions to the ASDF format.  These URIs are included
in an ASDF file's metadata to advertise the fact that additional software support (beyond
a core ASDF library) is needed to properly interpret the file.  Like tags, these URIs
are not associated with a particular resource.  We recommend the following pattern
for extension URIs:

``asdf://<domain>/<project>/extensions/<name>-<version>``

Where ``<domain>`` is some domain that you control, ``<project>`` collects all entities
for a particular ASDF project, ``<name>`` is the name of the extension, and ``<version>``
is the extension's version number.  For example:

``asdf://example.com/example-project/extensions/foo-1.2.3``
