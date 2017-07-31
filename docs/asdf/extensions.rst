Writing ASDF extensions
=======================

Extensions provide a way for ASDF to represent complex types that are not
defined by the ASDF standard. Examples of types that require custom extensions
include types from third-party libraries, user-defined types, and also complex
types that are part of the Python standard library but are not handled in the
ASDF standard. From ASDF's perspective, these are all considered 'custom'
types.

Supporting new types in asdf is easy. There are three pieces needed:

1. A YAML Schema file for each new type.

2. A tag class (inheriting from `asdf.CustomType`) corresponding to each new
   custom type. The class must override ``to_tree`` and ``from_tree`` from
   `asdf.CustomType` in order to define how ASDF serializes and deserializes
   the custom type.

3. A Python class to define an "extension" to ASDF, which is a set of related
   types. This class must implement the `asdf.AsdfExtension` abstract base
   class. In general, a third-party library that defines multiple custom types
   can group them all in the same extension.


An Example
----------

As an example, we will write an extension for ASDF that allows us to represent
Python's standard ``fractions.Fraction`` class for representing rational
numbers. We will call our new ASDF type ``fraction``.

First, the YAML Schema, defining the type as a pair of integers:

.. code-block:: yaml

   %YAML 1.1
   ---
   $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
   id: "http://nowhere.org/schemas/custom/1.0.0/fraction"
   title: An example custom type for handling fractions

   tag: "tag:nowhere.org:custom/1.0.0/fraction"
   type: array
   items:
     type: integer
   minItems: 2
   maxItems: 2
   ...

Then, the Python implementation of the tag class and extension class. See the
`asdf.CustomType` and `asdf.AsdfExtension` documentation for more information:

.. code-block:: python

    import os

    import asdf
    from asdf import util

    import fractions

    class FractionType(asdf.CustomType):
        name = 'fraction'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [fractions.Fraction]

        @classmethod
        def to_tree(cls, node, ctx):
            return [node.numerator, node.denominator]

        @classmethod
        def from_tree(cls, tree, ctx):
            return fractions.Fraction(tree[0], tree[1])

    class FractionExtension(object):
        @property
        def types(self):
            return [FractionType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/1.0.0/',
                     util.filepath_to_url(os.path.dirname(__file__))
                     + '/{url_suffix}.yaml')]

Note that the method ``to_tree`` of the tag class ``FractionType`` defines how
the library converts ``fractions.Fraction`` into a tree that can be stored by
ASDF. Conversely, the method ``from_tree`` defines how the library reads a
serialized representation of the object and converts it back into a
``fractions.Fraction``.

Explicit version support
------------------------

To some extent schemas and tag classes will be closely tied to the custom data
types that they represent. This means that in some cases API changes or other
changes to the representation of the underlying types will force us to modify
our schemas and tag classes. ASDF's schema versioning allows us to handle
changes in schemas over time.

Let's consider an imaginary custom type called ``Person`` that we want to
serialize in ASDF. The first version of ``Person`` was constructed using a
first and last name:

.. code-block:: python

    person = Person('James', 'Webb')
    print(person.first, person.last)

Our version 1.0.0 YAML schema for ``Person`` might look like the following:

.. code-block:: yaml

   %YAML 1.1
   ---
   $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
   id: "http://nowhere.org/schemas/custom/1.0.0/person"
   title: An example custom type for representing a Person

   tag: "tag:nowhere.org:custom/1.0.0/person"
   type: array
   items:
     type: string
   minItems: 2
   maxItems: 2
   ...

And our tag implementation would look something like this:

.. code-block:: python

    import asdf
    from people import Person

    class PersonType(asdf.CustomType):
        name = 'person'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [Person]

        @classmethod
        def to_tree(cls, node, ctx):
            return [node.first, node.last]

        @classmethod
        def from_tree(cls, tree, ctx):
            return Person(tree[0], tree[1])

However, a newer version of ``Person`` now requires a middle name in the
constructor as well:

.. code-block:: python

    person = Person('James', 'Edwin', 'Webb')
    print(person.first, person.middle, person.last)
    James Edwin Webb

So we update our YAML schema to version 1.1.0 in order to support newer
versions of Person:

.. code-block:: yaml

   %YAML 1.1
   ---
   $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
   id: "http://nowhere.org/schemas/custom/1.1.0/person"
   title: An example custom type for representing a Person

   tag: "tag:nowhere.org:custom/1.1.0/person"
   type: array
   items:
     type: string
   minItems: 3
   maxItems: 3
   ...

We need to update our tag class implementation as well. However, we need to be
careful. We still want to be able to read version 1.0.0 of our schema and be
able to convert it to the newer version of ``Person`` objects. To accomplish
this, we will make use of the ``supported_versions`` attribute for our tag
class. This will allow us to declare explicit support for the schema versions
our tag class implements.

Under the hood, ASDF creates multiple copies of our ``PersonType`` tag class,
each with a different ``version`` attribute corresponding to one of the
supported versions. This means that in our new tag class implementation, we can
condition our ``from_tree`` implementation on the value of ``cls.version`` to
determine which schema version should be used when reading:

.. code-block:: python

    import asdf
    from people import Person

    class PersonType(asdf.CustomType):
        name = 'person'
        organization = 'nowhere.org'
        version = (1, 1, 0)
        supported_versions = [(1, 0, 0), (1, 1, 0)]
        standard = 'custom'
        types = [Person]

        @classmethod
        def to_tree(cls, node, ctx):
            return [node.first, node.middle, node.last]

        @classmethod
        def from_tree(cls, tree, ctx):
            # Handle the older version of the person schema
            if cls.version == (1, 0, 0):
                # Construct a Person object with an empty middle name field
                return Person(tree[0], '', tree[1])
            else:
                # The newer version of the schema stores the middle name too
                return person(tree[0], tree[1], tree[2])
                
Note that the implementation of ``to_tree`` is not conditioned on
``cls.version`` since we do not need to convert new ``Person`` objects back to
the older version of the schema.


Adding custom validators
------------------------

A new type may also add new validation keywords to the schema
language. This can be used to impose type-specific restrictions on the
values in an ASDF file.  This feature is used internally so a schema
can specify the required datatype of an array.

To support custom validation keywords, set the ``validators`` member
of a ``CustomType`` subclass to a dictionary where the keys are the
validation keyword name and the values are validation functions.  The
validation functions are of the same form as the validation functions
in the underlying ``jsonschema`` library, and are passed the following
arguments:

  - ``validator``: A `jsonschema.Validator` instance.

  - ``value``: The value of the schema keyword.

  - ``instance``: The instance to validate.  This will be made up of
    basic datatypes as represented in the YAML file (list, dict,
    number, strings), and not include any object types.

  - ``schema``: The entire schema that applies to instance.  Useful to
    get other related schema keywords.

The validation function should either return ``None`` if the instance
is valid or ``yield`` one or more `asdf.ValidationError` objects if
the instance is invalid.

To continue the example from above, for the ``FractionType`` say we
want to add a validation keyword "``simplified``" that, when ``true``,
asserts that the corresponding fraction is in simplified form:

.. code-block:: python

    from asdf import ValidationError

    def validate_simplified(validator, simplified, instance, schema):
        if simplified:
            reduced = fraction.Fraction(instance[0], instance[1])
            if (reduced.numerator != instance[0] or
                reduced.denominator != instance[1]):
                yield ValidationError("Fraction is not in simplified form.")

    FractionType.validators = {'simplified': validate_simplified}
