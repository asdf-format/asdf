.. currentmodule:: asdf.extension

.. _extending_converters:

==========
Converters
==========

The `~asdf.extension.Converter` interface defines a mapping between
tagged objects in the ASDF tree and their corresponding Python object(s).
Typically a Converter will map one YAML tag to one Python type, but
the interface also supports many-to-one and many-to-many mappings.  A
Converter provides the software support for a tag and is responsible
for both converting from parsed YAML to more complex Python objects
and vice versa.

The Converter interface
=======================

Every Converter implementation must provide two required properties and
two required methods:

`Converter.tags` - a list of tag URIs or URI patterns handled by the converter.
Patterns may include the wildcard character `*`, which matches any sequence of
characters up to a `/`, or `**`, which matches any sequence of characters.
The `~asdf.util.uri_match` method can be used to test URI patterns.

`Converter.types` - a list of Python types or fully-qualified Python type names handled
by the converter.  Note that a string name must reflect the actual location of the
class's implementation and not just a module where it is imported for convenience.
For example, if class ``Foo`` is implemented in ``example_package.foo.Foo`` but
imported as ``example_package.Foo`` for convenience, it is the former name that
must be used.  The `~asdf.util.get_class_name` method will return the name that
`asdf` expects.

The string type name is recommended over a type object for performance reasons,
see :ref:`extending_converters_performance`.

`Converter.to_yaml_tree` - a method that accepts a complex Python object and returns
a simple node object (typically a `dict`) suitable for serialization to YAML.  The
node is permitted to contain nested complex objects; these will in turn
be passed to other ``to_yaml_tree`` methods in other Converters.

`Converter.from_yaml_tree` - a method that accepts a simple node object from parsed YAML and
returns the appropriate complex Python object.  Nested nodes in the received node
will have already been converted to complex objects by other calls to ``from_yaml_tree``
methods, except where reference cycles are present -- see
:ref:`extending_converters_reference_cycles` for information on how to handle that
situation.

Additionally, the Converter interface includes a method that must be implemented
when some logic is required to select the tag to assign to a ``to_yaml_tree`` result:

`Converter.select_tag` - a method that accepts a complex Python object and a list
candidate tags and returns the tag that should be used to serialize the object.

A simple example
================

Say we have a Python class, ``Rectangle``, that we wish to serialize
to an ASDF file.  A ``Rectangle`` instance has two attributes, width
and height, and a convenient method that computes its area:

.. code-block:: python

    # in module example_package.shapes
    class Rectangle:
        def __init__(self, width, height):
            self.width = width
            self.height = height

        def get_area(self):
            return self.width * self.height

We'll need to designate a tag URI to represent this object's type
in the ASDF tree -- let's use ``asdf://example.com/example-project/tags/rectangle-1.0.0``.
Here is a simple Converter implementation for this type and tag:

.. code-block:: python

    from asdf.extension import Converter

    class RectangleConverter(Converter):
        tags = ["asdf://example.com/shapes/tags/rectangle-1.0.0"]
        types = ["example_package.shapes.Rectangle"]

        def to_yaml_tree(self, obj, tag, ctx):
            return {
                "width": obj.width,
                "height": obj.height,
            }

        def from_yaml_tree(self, node, tag, ctx):
            from example_package.shapes import Rectangle

            return Rectangle(node["width"], node["height"])

Note that import of the ``Rectangle`` class has been deferred to
inside the ``from_yaml_tree`` method.  This is a performance consideration
that is discussed in :ref:`extending_converters_performance`.

In order to use this Converter, we'll need to create a simple extension
around it and install that extension:

.. code-block:: python

    import asdf
    from asdf.extension import Extension

    class ShapesExtension(Extension):
        extension_uri = "asdf://example.com/shapes/extensions/shapes-1.0.0"
        converters = [RectangleConverter()]
        tags = ["asdf://example.com/shapes/tags/rectangle-1.0.0"]

    asdf.get_config().add_extension(ShapesExtension())

Now we can include a Rectangle object in an `~asdf.asdf.AsdfFile` tree
and write out a file:

.. code-block:: python

    with asdf.AsdfFile() as af:
        af["rect"] = Rectangle(5, 4)
        af.write_to("test.asdf")

The portion of the ASDF file that represents the rectangle looks like this:

.. code-block:: yaml

    rect: !<asdf://example.com/shapes/tags/rectangle-1.0.0> {height: 4, width: 5}

Multiple tags
=============

Now say we want to map our one Rectangle class to one of two tags, either
rectangle-1.0.0 or square-1.0.0.  We'll need to add square-1.0.0 to
the converter's list of tags and implement a ``select_tag`` method:

.. code-block:: python

    RETANGLE_TAG = "asdf://example.com/shapes/tags/rectangle-1.0.0"
    SQUARE_TAG = "asdf://example.com/shapes/tags/square-1.0.0"

    class RectangleConverter(Converter):
        tags = [RECTANGLE_TAG, SQUARE_TAG]
        types = ["example_package.shapes.Rectangle"]

        def select_tag(self, obj, tags, ctx):
            if obj.width == obj.height:
                return SQUARE_TAG
            else:
                return RECTANGLE_TAG

        def to_yaml_tree(self, obj, tag, ctx):
            if tag == SQUARE_TAG:
                return {
                    "side_length": obj.width,
                }
            else:
                return {
                    "width": obj.width,
                    "height": obj.height,
                }

        def from_yaml_tree(self, node, tag, ctx):
            from example_package.shapes import Rectangle

            if tag == SQUARE_TAG:
                return Rectangle(node["side_length"], node["side_length"])
            else:
                return Rectangle(node["width"], node["height"])

.. _extending_converters_reference_cycles:

Reference cycles
================

Special considerations must be made when deserializing a tagged object that
contains a reference to itself among its descendants.  Consider a
`fractions.Fraction` subclass that maintains a reference to its multiplicative
inverse:

.. code-block:: python

    # in the example_project.fractions module
    class FractionWithInverse(fractions.Fraction):
        def __init__(self, *args, **kwargs):
            self._inverse = None

        @property
        def inverse(self):
            return self._inverse

        @inverse.setter
        def inverse(self, value):
            self._inverse = value

The inverse of the inverse of a fraction is the fraction itself,
we might wish to construct the objects in the following way:

.. code-block:: python

    f1 = FractionWithInverse(3, 5)
    f2 = FractionWithInverse(5, 3)
    f1.inverse = f2
    f2.inverse = f1

Which creates an "infinite loop" between the two fractions.  An ordinary
Converter wouldn't be able to deserialize this, since each fraction
requires that the other be deserialized first!  Let's see what happens
when we define our ``from_yaml_tree`` method in a naive way:

.. code-block:: python

    class FractionWithInverseConverter(Converter):
        tags = ["asdf://example.com/fractions/tags/fraction-1.0.0"]
        types = ["example_project.fractions.FractionWithInverse"]

        def to_yaml_tree(self, obj, tag, ctx):
            return {
                "numerator": obj.width,
                "denominator": obj.height,
                "inverse": obj.inverse,
            }

        def from_yaml_tree(self, node, tag, ctx):
            from example_project.fractions import FractionWithInverse

            obj = FractionWithInverse(
                tree["numerator"],
                tree["denominator"]
            )
            obj.inverse = tree["inverse"]
            return obj

After adding this Converter to an Extension and installing it, the fraction
will serialize correctly:

.. code-block:: python

    with asdf.AsdfFile({"fraction": f1}) as af:
        af.write_to("with_inverse.asdf")

But upon deserialization, we notice a problem:

.. code-block:: python

    with asdf.open("with_inverse.asdf") as af:
        reconstituted_f1 = af["fraction"]

    assert reconstituted_f1.inverse.inverse is asdf.treeutil.PendingValue

The presence of `~asdf.treeutil.PendingValue` is asdf's way of telling us
that the value corresponding to the key ``inverse`` was not fully deserialized
at the time that we retrieved it.  We can handle this situation by making our
``from_yaml_tree`` a generator function:

.. code-block:: python

        def from_yaml_tree(self, node, tag, ctx):
            from example_project.fractions import FractionWithInverse

            obj = FractionWithInverse(
                tree["numerator"],
                tree["denominator"]
            )
            yield obj
            obj.inverse = tree["inverse"]

The generator version of ``from_yaml_tree`` yields the partially constructed
``FractionWithInverse`` object before setting its inverse property.  This allows
`asdf` to proceed to constructing the inverse ``FractionWithInverse`` object,
and resume the original ``from_yaml_tree`` execution only when the inverse
is actually available.

With this modification we can successfully deserialize our ASDF file:

.. code-block:: python

    with asdf.open("with_inverse.asdf") as af:
            reconstituted_f1 = ff["fraction"]

    assert reconstituted_f1.inverse.inverse is reconstituted_f1

.. _extending_converters_performance:

Entry point performance considerations
======================================

For the good of `asdf` users everywhere, it's important that entry point
methods load as quickly as possible.  All extensions must be loaded before
reading an ASDF file, and therefore all converters are created as well.  Any
converter module or ``__init__`` method that lingers will introduce a delay
to the initial call to `asdf.open`.  For that reason, we recommend that converter
authors minimize the number of imports that occur in the module containing the
Converter implementation, and defer imports of serializable types to within the
``from_yaml_tree`` method.  This will prevent the type from ever being imported
when reading ASDF files that do not contain the associated tag.
