Writing ASDF extensions
=======================

Supporting new types in pyasdf is easy.  There are three pieces needed:

1. A YAML Schema file for each new type.

2. A Python class (inheriting from `pyasdf.AsdfType`) for each new
   type.

3. A Python class to define an "extension" to ASDF, which is a set of
   related types.  This class must implement the
   `pyasdf.AsdfExtension` abstract base class.

For an example, we will make a type to handle rational numbers called
``fraction``.

First, the YAML Schema, defining the type as a pair of integers:

.. code:: yaml

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

Then, the Python implementation.  See the `pyasdf.AsdfType` and
`pyasdf.AsdfExtension` documentation for more information::

    import os

    import pyasdf
    from pyasdf import util

    import fractions

    class FractionType(pyasdf.AsdfType):
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

Adding custom validators
------------------------

A new type may also add new validation keywords to the schema
language. This can be used to impose type-specific restrictions on the
values in an ASDF file.  This feature is used internally so a schema
can specify the required datatype of an array.

To support custom validation keywords, set the ``validators`` member
of an ``AsdfType`` subclass to a dictionary where the keys are the
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
is valid or ``yield`` one or more `pyasdf.ValidationError` objects if
the instance is invalid.

To continue the example from above, for the ``FractionType`` say we
want to add a validation keyword "``simplified``" that, when ``true``,
asserts that the corresponding fraction is in simplified form::

    from pyasdf import ValidationError

    def validate_simplified(validator, simplified, instance, schema):
        if simplified:
            reduced = fraction.Fraction(instance[0], instance[1])
            if (reduced.numerator != instance[0] or
                reduced.denominator != instance[1]):
                yield ValidationError("Fraction is not in simplified form.")

    FractionType.validators = {'simplified': validate_simplified}
