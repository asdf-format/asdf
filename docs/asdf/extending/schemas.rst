.. _extending_schemas:

============
ASDF schemas
============

ASDF schemas are YAML documents that describe validations to be performed
on tagged objects nested within the ASDF tree or on the tree itself.  Schemas
can validate the presence, datatype, and value of objects and their properties,
and can be combined in different ways to facilitate reuse.

These schemas, though expressed in YAML, are structured according to
the `JSON Schema Draft 4`_ specification.  The excellent `Understanding JSON Schema`_
book is a great place to start for users not already familiar with
JSON Schema.  Just keep in mind that the book includes coverage of later drafts
of the JSON Schema spec, so certain features (constant values, conditional
subschemas, etc) will not be available when writing schemas for ASDF.
The book makes clear which features were introduced after Draft 4.

Anatomy of a schema
===================

Here is an example of an ASDF schema that validates an object with a
numeric value and corresponding unit:

.. code-block:: yaml
    :linenos:

    %YAML 1.1
    ---
    $schema: http://stsci.edu/schemas/yaml-schema/draft-01
    id: asdf://asdf-format.org/core/schemas/quantity-2.0.0

    title: Quantity object containing numeric value and unit
    description: >-
      An object with a numeric value, which may be a scalar
      or an array, and associated unit.

    type: object
    properties:
      value:
        description: A vector of one or more values
        anyOf:
          - type: number
          - tag: tag:stsci.edu:asdf/core/ndarray-1.0.0
      unit:
        description: The unit corresponding to the values
        tag: tag:stsci.edu:asdf/unit/unit-1.0.0
      required: [value, unit]
    ...

This is similar to the quantity schema, found :ref:`here <asdf-standard:unit-schema>`, of the ASDF Standard, but
has been updated to reflect current recommendations regarding schemas.
Let's walk through this schema line by line.

.. code-block:: yaml
    :linenos:

    %YAML 1.1
    ---

These first two lines form the header of the file.  The ``%YAML 1.1``
indicates that we're following version 1.1 of the YAML spec.  The
``---`` marks the start of a new YAML document.

.. code-block:: yaml
    :lineno-start: 3

    $schema: http://stsci.edu/schemas/yaml-schema/draft-01

The ``$schema`` property contains the URI of the schema that validates
this document.  Since our document is itself a schema, the URI refers to
a *metaschema*.  ASDF comes with three built-in metaschemas:

- ``http://json-schema.org/draft-04/schema`` - The JSON Schema Draft 4 metaschema.
  Includes basic validators and combiners.

- ``http://stsci.edu/schemas/yaml-schema/draft-01`` - The YAML Schema metaschema.
  Includes everything in JSON Schema Draft 4, plus additional YAML-specific
  validators including ``tag`` and ``propertyOrder``.

- ``http://stsci.edu/schemas/asdf/asdf-schema-1.0.0`` - The ASDF Schema metaschema.
  Includes everything in YAML Schema, plus additional ASDF-specific validators
  that check ndarray properties.

Our schema makes use of the ``tag`` validator, so we're specifying the YAML Schema
URI here.

.. code-block:: yaml
    :lineno-start: 4

    id: asdf://asdf-format.org/core/schemas/quantity-2.0.0

The ``id`` property contains the URI that uniquely identifies our schema.  This
URI is how we'll refer to the schema when using the asdf library.

.. code-block:: yaml
    :lineno-start: 6

    title: Quantity object containing numeric value and unit
    description: >-
      An object with a numeric value, which may be a scalar
      or an array, and associated unit.

Title and description are optional (but recommended) documentation properties.
These properties can be placed multiple times at any level of the schema and do
not have an impact on the validation process.

.. code-block:: yaml
    :lineno-start: 11

    type: object

This line invokes the ``type`` validator to check the data type of the
top-level value.  We're asserting that the type must be a YAML mapping,
which in Python is represented as a `dict`.

.. code-block:: yaml
    :lineno-start: 12

    properties:

The ``properties`` validator announces that we'd like to validate certain
named properties of mapping.  If a property is listed here and is present
in the ASDF, it will be validated accordingly.

.. code-block:: yaml
    :lineno-start: 13

      value:
        description: A vector of one or more values

Here we're identifying a property named ``value`` that we'd like to
validate.  The ``description`` is used to add some additional
documentation.

.. code-block:: yaml
    :lineno-start: 15

      anyOf:

The ``anyOf`` validator is one of JSON Schema's combiners.  The ``value``
property will be validated against each of the following subschemas, and
if any validates successfully, the entire ``anyOf`` will be considered
valid.  Other available combiners are ``allOf``, which requires that all
subschemas validate successfully, ``oneOf``, which requires that one and
only one of the subschemas validates, and ``not``, which requires that
a single subschema does *not* validate.

.. code-block:: yaml
    :lineno-start: 16

        - type: number

The first subschema in the list contains a ``type`` validator that
succeeds if the entity assigned to ``value`` is a numeric literal.

.. code-block:: yaml
    :lineno-start: 17

        - tag: tag:stsci.edu:asdf/core/ndarray-1.0.0

The second subschema contains a ``tag`` validator, which makes an
assertion regarding the YAML tag URI of the object assigned to ``value``.
In this subschema we're requiring the tag of an ndarray-1.0.0 object,
which is how n-dimensional arrays are represented in an ASDF tree.

The net effect of the ``anyOf`` combiner and its two subschemas is:
validate successfully if the ``value`` object is either a numeric
literal or an n-dimensional array.

.. code-block:: yaml
    :lineno-start: 18

      unit:
        description: The unit corresponding to the values
        tag: tag:stsci.edu:asdf/unit/unit-1.0.0

The ``unit`` property has another bit of documentation and a
``tag`` validator that requires it to be a unit-1.0.0 object.

.. code-block:: yaml
    :lineno-start: 21

    required: [value, unit]

Since the ``properties`` validator does not require the presence of
its listed properties, we need another validator to do that.  The ``required``
validator defines a list of properties that need to be present if validation
is to succeed.

.. code-block:: yaml
    :lineno-start: 21

    ...

Finally, the YAML document end indicator indicates the end of the schema.

Checking schema syntax
======================

The `~asdf.schema.check_schema` function performs basic syntax checks on a schema and
will raise an error if it discovers a problem.  It does not currently accept URIs and
requires that the schema already be loaded into Python objects.  If the schema is already
registered with the asdf library as a resource (see :ref:`extending_resources`), it can
be loaded and checked like this:

.. code-block:: python

    from asdf.schema import load_schema, check_schema

    schema = load_schema("asdf://example.com/example-project/schemas/foo-1.0.0")
    check_schema(schema)

Otherwise, the schema can be loaded using pyyaml directly:

.. code-block:: python

    from asdf.schema import check_schema
    import yaml

    schema = yaml.safe_load(open("/path/to/foo-1.0.0.yaml").read())
    check_schema(schema)

Testing validation
==================

Getting a schema to validate as intended can be a tricky business, so it's helpful
to test validation against some example objects as you go along.  The `~asdf.schema.validate`
function will validate a Python object against a schema:

.. code-block:: python

  from asdf.schema import validate
  import yaml

  schema = yaml.safe_load(open("/path/to/foo-1.0.0.yaml").read())
  obj = {"foo": "bar"}
  validate(obj, schema=schema)

The validate function will return successfully if the object is valid, or raise
an error if not.

See also:
=========

- `JSON Schema Draft 4 <https://json-schema.org/specification-links.html#draft-4>`_

- `Understanding JSON Schema <https://json-schema.org/understanding-json-schema/>`_

- :ref:`Unit Schemas <asdf-standard:unit-schema>`
