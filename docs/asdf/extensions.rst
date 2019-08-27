.. currentmodule:: asdf.extensions

.. _extensions:

Writing ASDF extensions
=======================

Extensions provide a way for ASDF to represent complex types that are not
defined by the ASDF standard. Examples of types that require custom extensions
include types from third-party libraries, user-defined types, and complex types
that are part of the Python standard library but are not handled in the ASDF
standard. From ASDF's perspective, these are all considered 'custom' types.

Supporting new types in ASDF is easy. Three components are required:

1. A YAML Schema file for each new type.

2. A tag class (inheriting from `asdf.CustomType`) corresponding to each new
   custom type. The class must override `~asdf.CustomType.to_tree` and
   `~asdf.CustomType.from_tree` from `asdf.CustomType` in order to define how
   ASDF serializes and deserializes the custom type.

3. A Python class to define an "extension" to ASDF, which is a set of related
   types. This class must implement the `asdf.AsdfExtension` abstract base
   class. In general, a third-party library that defines multiple custom types
   can group them all in the same extension.

.. note::

    The mechanisms of tag classes and extension classes are specific to this
    particular implementation of ASDF. As of this writing, this is the only
    complete implementation of the ASDF Standard. However, other language
    implementations may use other mechanisms for processing custom types.
    
    All implementations of ASDF, regardless of language, will make use of the
    same schemas for abstract data type definitions. This allows all ASDF files
    to be language-agnostic, and also enables interoperability.

An Example
----------

As an example, we will write an extension for ASDF that allows us to represent
Python's standard `fractions.Fraction` class for representing rational numbers.
We will call our new ASDF type ``fraction``.

First, the YAML Schema, defining the type as a pair of integers:

.. code-block:: yaml

    %YAML 1.1
    ---
    $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
    id: "http://nowhere.org/schemas/custom/fraction-1.0.0"
    title: An example custom type for handling fractions

    tag: "tag:nowhere.org:custom/fraction-1.0.0"
    type: array
    items:
      type: integer
    minItems: 2
    maxItems: 2
    ...

Then, the Python implementation of the tag class and extension class. See the
`asdf.CustomType` and `asdf.AsdfExtension` documentation for more information:

.. runcode:: hidden

    import os
    import asdf
    # This is a hack in order to get the example below to work properly
    __file__ = os.path.join(asdf.__path__[0], 'tests', 'data', 'fraction-1.0.0.yaml')

.. runcode::

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

    class FractionExtension(asdf.AsdfExtension):
        @property
        def types(self):
            return [FractionType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(os.path.dirname(__file__))
                     + '/{url_suffix}.yaml')]

Note that the method `~asdf.CustomType.to_tree` of the tag class
``FractionType`` defines how the library converts `fractions.Fraction` into a
tree that can be stored by ASDF. Conversely, the method
`~asdf.CustomType.from_tree` defines how the library reads a serialized
representation of the object and converts it back into an instance of
`fractions.Fraction`.

Note that the values of the `~asdf.CustomType.name`,
`~asdf.CustomType.organization`, `~asdf.CustomType.standard`, and
`~asdf.CustomType.version` fields are all reflected in the ``id`` and ``tag``
definitions in the schema.

Note also that the base of the ``tag`` value (up to the `name` and `version`
components) is reflected in `~asdf.AsdfExtension.tag_mapping` property of the
`FractionExtension` type, which is used to map tags to URLs. The
`~asdf.AsdfExtension.url_mapping` is used to map URLs (of the same form as the
``id`` field in the schema) to the actual location of a schema file.

Once these classes and the schema have been defined, we can save an asdf file
using them:

.. runcode::

    tree = {'fraction': fractions.Fraction(10, 3)}

    with asdf.AsdfFile(tree, extensions=FractionExtension()) as ff:
        ff.write_to("test.asdf")

.. asdf:: test.asdf ignore_unrecognized_tag

Defining custom types
---------------------

In the example above, we showed how to create an extension that is capable of
serializing `fractions.Fraction`. The custom tag type that we created was
defined as a subclass of `asdf.CustomType`.

Custom type attributes
**********************

We overrode the following attributes of `~asdf.CustomType` in order to define
`FractionType` (each bullet is also a link to the API documentation):

* `~asdf.CustomType.name`
* `~asdf.CustomType.organization`
* `~asdf.CustomType.version`
* `~asdf.CustomType.standard`
* `~asdf.CustomType.types`

Each of these attributes is important, and each is described in more detail in
the linked API documentation.

The choice of `~asdf.CustomType.name` should be descriptive of the custom type
that is being serialized. The choice of `~asdf.CustomType.organization`, and
`~asdf.CustomType.standard` is fairly arbitrary, but also important. Custom
types that are provided by the same package should be grouped into the same
`~asdf.CustomType.standard` and `~asdf.CustomType.organization`.

These three values, along with the `~asdf.CustomType.version`, are used to
define the YAML tag that will mark the serialized type in ASDF files. In our
example, the tag becomes ``tag:nowhere.org:custom/fraction-1.0.0``. The tag
is important when defining the `asdf.AsdfExtension` subclass.

Critically, these values must all be reflected in the associated schema.

Custom type methods
*******************

In addition to the attributes mentioned above, we also overrode the following
methods of `~asdf.CustomType` (each bullet is also a link to the API
documentation):

* `~asdf.CustomType.to_tree`
* `~asdf.CustomType.from_tree`

The `~asdf.CustomType.to_tree` method defines how an instance of a custom data
type is converted into data structures that represent a YAML tree that can be
serialized to a file.

The `~asdf.CustomType.from_tree` method defines how a YAML tree can be
converted back into an instance of the original custom data type.

In the example above, we used a `list` to contain the important attributes of
`fractions.Fraction`. However, this choice is fairly arbitrary, as long as it
is consistent between the way that `~asdf.CustomType.to_tree` and
`~asdf.CustomType.from_tree` are defined. For example, we could have also
chosen to use a `dict`:

.. runcode::

    import asdf
    import fractions

    class FractionType(asdf.CustomType):
        name = 'fraction'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [fractions.Fraction]

        @classmethod
        def to_tree(cls, node, ctx):
            return dict(numerator=node.numerator,
                        denominator=node.denominator)

        @classmethod
        def from_tree(cls, tree, ctx):
            return fractions.Fraction(tree['numerator'],
                                      tree['denominator'])

.. runcode:: hidden

    # Redefine the fraction extension for the sake of the example
    FractionExtension.types = [FractionType]

    tree = {'fraction': fractions.Fraction(10, 3)}

    with asdf.AsdfFile(tree, extensions=FractionExtension()) as ff:
        ff.write_to("test.asdf")

In this case, the associated schema would look like the following::

    %YAML 1.1
    ---
    $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
    id: "http://nowhere.org/schemas/custom/fraction-1.0.0"
    title: An example custom type for handling fractions

    tag: "tag:nowhere.org:custom/fraction-1.0.0"
    type: object
    properties:
      numerator:
        type: integer
      denominator:
        type: integer
    ...

We can compare the output using this representation to the example above:

.. asdf:: test.asdf ignore_unrecognized_tag


Serializing more complex types
******************************

Sometimes the custom types that we wish to represent in ASDF themselves have
attributes which are also custom types. As a somewhat contrived example,
consider a 2D cartesian coordinate that uses `fraction.Fraction` to represent
each of the components. We will call this type `Fractional2DCoordinate`.

First we need to define a schema to represent this new type::

    %YAML 1.1
    ---
    $schema: "http://stsci.edu/schemas/yaml-schema/draft-01"
    id: "http://nowhere.org/schemas/custom/fractional_2d_coord-1.0.0"
    title: An example custom type for handling components

    tag: "tag:nowhere.org:custom/fractional_2d_coord-1.0.0"
    type: object
    properties:
      x:
        $ref: fraction-1.0.0
      y:
        $ref: fraction-1.0.0
    ...

Note that in the schema, the ``x`` and ``y`` attributes are expressed as
references to our ``fraction-1.0.0`` schema. Since both of these schemas are
defined under the same standard and organization, we can simply use the name
and version of the ``fraction-1.0.0`` schema to refer to it. However, if the
reference type was defined in a different organization and standard, it would
be necessary to use the entire YAML tag in the reference (e.g.
``tag:nowhere.org:custom/fraction-1.0.0``). Relative tag references are also
allowed where appropriate.

.. runcode:: hidden

    class Fractional2DCoordinate:
        x = None
        y = None

We also need to define the custom tag type that corresponds to our new type:

.. runcode::

    import asdf
    from asdf.yamlutil import (custom_tree_to_tagged_tree,
                               tagged_tree_to_custom_tree)

    class Fractional2DCoordinateType(asdf.CustomType):
        name = 'fractional_2d_coord'
        organization = 'nowhere.org'
        version = (1, 0, 0)
        standard = 'custom'
        types = [Fractional2DCoordinate]

        @classmethod
        def to_tree(cls, node, ctx):
            tree = dict()
            tree['x'] = custom_tree_to_tagged_tree(node.x, ctx)
            tree['y'] = custom_tree_to_tagged_tree(node.y, ctx)
            return tree

        @classmethod
        def from_tree(cls, tree, ctx):
            coord = Fractional2DCoordinate()
            coord.x = tagged_tree_to_custom_tree(tree['x'], ctx)
            coord.y = tagged_tree_to_custom_tree(tree['y'], ctx)
            return coord

Recall that the ``x`` and ``y`` components of our `Fractional2DCoordinate` type
are represented as `fractions.Fraction`. Since this is a type for which we have
already defined a tag class, we don't want to duplicate the logic from its
`~asdf.CustomType.to_tree` and `~asdf.CustomType.from_tree` methods here.

Instead, we use the functions `~asdf.yamlutil.custom_tree_to_tagged_tree` and
`~asdf.yamlutil.tagged_tree_to_custom_tree` to recursively process the
subtrees. By doing so, we ensures that the `~asdf.CustomType.to_tree` and
`~asdf.CustomType.from_tree` methods specific to `fractions.Fraction` will be
called automatically.

Since `Fractional2DCoordinateType` shares the same
`~asdf.CustomType.organization` and `~asdf.CustomType.standard` as
`FractionType`, it can be added to the same extension class:

.. runcode::

    class FractionExtension(asdf.AsdfExtension):
        @property
        def types(self):
            return [FractionType, Fractional2DCoordinateType]

        @property
        def tag_mapping(self):
            return [('tag:nowhere.org:custom',
                     'http://nowhere.org/schemas/custom{tag_suffix}')]

        @property
        def url_mapping(self):
            return [('http://nowhere.org/schemas/custom/',
                     util.filepath_to_url(os.path.dirname(__file__))
                     + '/{url_suffix}.yaml')]

Now we can use this extension to create an ASDF file:

.. runcode::

    coord = Fractional2DCoordinate()
    coord.x = fractions.Fraction(22, 7)
    coord.y = fractions.Fraction(355, 113)

    tree = {'coordinate': coord}

    with asdf.AsdfFile(tree, extensions=FractionExtension()) as ff:
        ff.write_to("coord.asdf")

.. asdf:: coord.asdf ignore_unrecognized_tag

Note that in the resulting ASDF file, the ``x`` and ``y`` components of
our new `fraction_2d_coord` type are tagged as `fraction-1.0.0`.

Assigning schema and tag versions
*********************************

Authors of new tags and schemas should strive to use the conventions described
by `semantic versioning <https://semver.org/>`_. Tags and schemas for types
that have not been serialized before should begin at ``1.0.0``. Versions for a
particular tag type need not move in lock-step with other tag types in the same
extension.

The patch version should be bumped for bug fixes and other minor,
backwards-compatible changes. New features can be indicated with increments to
the minor version, as long as they remain backwards compatible with older
versions of the schema. Any changes that break backwards compatibility must be
indicated by a major version update.

Since ASDF is intended to be an archival file format, authors of tags and
schemas should work to ensure that ASDF files created with older extensions can
continue to be processed. This means that every time a schema version is bumped
(with the possible exception of patch updates), a **new** schema file should be
created.

For example, if we currently have a schema for ``xyz-1.0.0``, and we wish to
make changes and bump the version to ``xyz-1.1.0``, we should leave the
original schema intact. A **new** schema file should be created for
``xyz-1.1.0``, which can exist in parallel with the old file. The version of
the corresponding tag type should be bumped to ``1.1.0``.

For more details on the behavior of schema and tag versioning from a user
perspective, see :ref:`version_and_compat`, and also
:ref:`custom_type_versions`.

Explicit version support
************************

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
   id: "http://nowhere.org/schemas/custom/person-1.0.0"
   title: An example custom type for representing a Person

   tag: "tag:nowhere.org:custom/person-1.0.0"
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
   id: "http://nowhere.org/schemas/custom/person-1.1.0"
   title: An example custom type for representing a Person

   tag: "tag:nowhere.org:custom/person-1.1.0"
   type: array
   items:
     type: string
   minItems: 3
   maxItems: 3
   ...

We need to update our tag class implementation as well. However, we need to be
careful. We still want to be able to read version 1.0.0 of our schema and be
able to convert it to the newer version of ``Person`` objects. To accomplish
this, we will make use of the `~asdf.CustomType.supported_versions` attribute
for our tag class. This will allow us to declare explicit support for the
schema versions our tag class implements.

Under the hood, ASDF creates multiple copies of our ``PersonType`` tag class,
each with a different `~asdf.CustomType.version` attribute corresponding to one
of the supported versions. This means that in our new tag class implementation,
we can condition our `~asdf.CustomType.from_tree` implementation on the value
of ``version`` to determine which schema version should be used when reading:

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

Handling subclasses
*******************

By default, if a custom type is serialized by an ASDF tag class, then all
subclasses of that type can also be serialized. However, no attributes that are
specific to the subclass will be stored in the file. When reading the file, an
instance of the base custom type will be returned instead of the subclass that
was written.

To properly handle subclasses of custom types already recognized by ASDF, it is
necessary to implement a separate tag class that is specific to the subclass to
be serialized.

However, this can be burdensome, especially if multiple subclasses need to be
handled. Version 2.4.0 of the `asdf` package introduces a new way to handle
subclasses of custom types using decorators.

.. attention::

   This feature was introduced in version 2.4.0 and is **experimental**. The
   API may change in future versions.

In previous examples we wrote a tag class for the built-in type
`fractions.Fraction`. Let's create a subclass of this type that we wish to
be able to serialize in ASDF. We have already defined ``FractionType`` which
handles the serialization of `fractions.Fraction`. We will use decorators to
indicate how to properly serialize the subclass:

.. code-block:: python

   @FractionType.subclass
   class NamedFraction(fractions.Fraction):
      """
      A very contrived example, indeed.
      """
      def __init__(self, *args, name='', **kwargs):
         super().__init__(*args, **kwargs)
         self._name = name

      @FractionType.subclass_property
      def name(self):
         return self._name

The decorators we use are defined as class methods of the ``FractionType`` tag
class. By using these we enable round-trip serialization of our custom subclass
type. See `asdf.CustomType.subclass` and `asdf.CustomType.subclass_property`
for additional details.

Note that this feature is currently not reflected in the ASDF Standard, which
means that other implementations of ASDF may not preserve subclass information.

Creating custom schemas
-----------------------

All custom types to be serialized by ASDF require custom schemas. The best
resource for creating ASDF schemas can be found in the `ASDF Standard
<http://asdf-standard.readthedocs.io/en/latest/extending.html>`_ documentation.

In most cases, ASDF schemas will be included as part of a packaged software
distribution. In these cases, it is important for the
`~asdf.AsdfExtension.url_mapping` of the corresponding `~asdf.AsdfExtension`
extension class to map the schema URL to an actual location on disk. However,
it is possible for schemas to be hosted online as well, in which case the URL
mapping can map (perhaps trivially) to an actual network location. See
:ref:`defining_extensions` for more information.

It is also important for packages that provide custom schemas to test them,
both to make sure that they are valid, and to ensure that any examples they
provide are also valid. See :ref:`testing_custom_schemas` for more information.

Adding custom validators
------------------------

A new type may also add new validation keywords to the schema
language. This can be used to impose type-specific restrictions on the
values in an ASDF file.  This feature is used internally so a schema
can specify the required datatype of an array.

To support custom validation keywords, set the `~asdf.CustomType.validators`
member of a `~asdf.CustomType` subclass to a dictionary where the keys are the
validation keyword name and the values are validation functions.  The
validation functions are of the same form as the validation functions in the
underlying ``jsonschema`` library, and are passed the following arguments:

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

.. _defining_extensions:

Defining custom extension classes
---------------------------------

Extension classes are the mechanism that ASDF uses to register custom tag types
so that they can be used when processing ASDF files. Packages that define their
own custom tag types must also define extensions in order for those types to be
used.

All extension classes must implement the `asdf.AsdfExtension` abstract base
class. A custom extension will override each of the following properties of
`AsdfExtension` (the text in each bullet is also a link to the corresponding
documentation):

* `~asdf.AsdfExtension.types`
* `~asdf.AsdfExtension.tag_mapping`
* `~asdf.AsdfExtension.url_mapping`

.. _packaging_extensions:

Overriding built-in extensions
******************************

It is possible for externally defined extensions to override tag types that are
provided by ASDF's built-in extension. For example, maybe an external package
wants to provide a different implementation of `~asdf.tags.core.NDArrayType`.
In this case, the external package does not need to provide custom schemas
since the schema for the type to be overridden is already provided as part of
the ASDF standard.

Instead, the extension class may inherit from ASDF's
`~asdf.extension.BuiltinExtension` and simply override the
`~asdf.AsdfExtension.types` property to indicate the type that is being
overridden.  Doing this preserves the `~asdf.AsdfExtension.tag_mapping` and
`~asdf.AsdfExtension.url_mapping` that is used by the `BuiltinExtension`, which
allows the schemas that are packaged by ASDF to be located.

ASDF will give precedence to the type that is provided by the external
extension, effectively overriding the corresponding type in the built-in
extension. Note that it is currently undefined if multiple external extensions
are provided that override the same built-in type.

Packaging custom extensions
---------------------------

Packaging schemas
*****************

If a package provides custom schemas, the schema files must be installed as
part of that package distribution. In general, schema files must be installed
into a subdirectory of the package distribution. The ASDF extension class must
supply a `~asdf.AsdfExtension.url_mapping` that maps to the installed location
of the schemas. See :ref:`defining_extensions` for more details.

Registering entry points
************************

Packages that provide their own ASDF extensions can (and should!) install them
so that they are automatically detectable by the ASDF Python package. This is
accomplished using Python's `setuptools` entry points. Entry points are
registered in a package's `setup.py` file.

Consider a package that provides an extension class `MyPackageExtension` in the
submodule `mypackage.asdf.extensions`. We need to register this class as an
extension entry point that ASDF will recognize. First, we create a dictionary:

.. code:: python

    entry_points = {}
    entry_points['asdf_extensions'] = [
        'mypackage = mypackage.asdf.extensions:MyPackageExtension'
    ]

The key used in the `entry_points` dictionary must be ``'asdf_extensions'``.
The value must be an array of one or more strings, each with the following
format:

    ``extension_name = fully.specified.submodule:ExtensionClass``

The extension name can be any arbitrary string, but it should be descriptive of
the package and the extension. In most cases the package itself name will
suffice.

Note that depending on individual package requirements, there may be other
entries in the `entry_points` dictionary.

The entry points must be passed to the call to `setuptools.setup`:

.. code:: python

    from setuptools import setup

    entry_points = {}
    entry_points['asdf_extensions'] = [
        'mypackage = mypackage.asdf.extensions:MyPackageExtension'
    ]

    setup(
        # We omit other package-specific arguments that are not
        # relevant to this example
        entry_points=entry_points,
    )

When running ``python setup.py install`` or ``python setup.py develop`` on this
package, the entry points will be registered automatically. This allows the
ASDF package to recognize the extensions without any user intervention. Users
of your package that wish to read ASDF files using types that you have
registered will not need to use any extension explicitly. Instead, ASDF will
automatically recognize the types you have registered and will process them
appropriately. See :ref:`other_packages` for more information on using
extensions.

.. _testing_custom_schemas:

Testing custom schemas
----------------------

Packages that provide their own schemas can test them using ASDF's
`pytest <https://docs.pytest.org/en/latest/>`_ plugin for schema testing.
Schemas are tested for overall validity, and any examples given within the
schemas are also tested.

The schema tester plugin is automatically registered when the ASDF package is
installed. In order to enable testing, it is necessary to add the directory
containing your schema files to the pytest section of your project's
`setup.cfg` file. If you do not already have such a file, creating a
`setup.cfg` with the following should be sufficient:

.. code:: ini

    [tool:pytest]
    asdf_schema_root = path/to/schemas another/path/to/schemas

The schema directory paths should be paths that are relative to the top of the
package directory **when it is installed**. If this is different from the path
in the source directory, then both paths can be used to facilitate in-place
testing (see ASDF's own `setup.cfg` for an example of this).

.. note::

   Older versions of ASDF (prior to 2.4.0) required the plugin to be registered
   in your project's `conftest.py` file. As of 2.4.0, the plugin is now
   registered automatically and so this line should be removed from your
   `conftest.py` file, unless you need to retain compatibility with older
   versions of ASDF.

The ``asdf_schema_skip_names`` configuration variable can be used to skip
schema files that live within one of the ``asdf_schema_root`` directories but
should not be tested. The names should be given as simple base file names
(without directory paths or extensions). Again, see ASDF's own `setup.cfg` file
for an example.

The schema tests do **not** run by default. In order to enable the tests by
default for your package, add ``asdf_schema_tests_enabled = true`` to the
``[tool:pytest]`` section of your `setup.cfg` file. If you do not wish to
enable the schema tests by default, you can add the ``--asdf-tests`` option to
the ``pytest`` command line to enable tests on a per-run basis.
