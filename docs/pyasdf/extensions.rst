Writing ASDF extensions
=======================

Supporting new types in pyasdf is easy.  There are three pieces needed:

1. A YAML Schema file for each new type.

2. A Python class (inheriting from `pyasdf.AsdfType`) for each new
   type.

3. A Python class to define an "extension" to ASDF, which is a set of
   related types.  This class must implement the
   `pyasdf.AsdfExtension` abstract base class.

For an example, we will make a type to handle rational numbers called ``fraction``.

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

    import pyasdf

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
                     'file://' + TEST_DATA_PATH + '/{url_suffix}.yaml')]
