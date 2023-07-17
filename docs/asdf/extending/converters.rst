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
Patterns may include the wildcard character ``*``, which matches any sequence of
characters up to a ``/``, or ``**``, which matches any sequence of characters.
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

.. _extending_converters_deferral:

Deferring to another converter
==============================

Converters only support the exact types listed in ``Converter.types``. When a
supported type is subclassed the extension will need to be updated to support
the new subclass. There are a few options for supporting subclasses.

If serialization of the subclass needs to differ from the superclass a new
Converter, tag and schema should be defined.

If the subclass can be treated the same as the superclass (specifically if
subclass instances can be serialized as the superclass) then the subclass
can be added to the existing ``Converter.types``. Note that adding the
subclass to the supported types (without making other changes to the Converter)
will result in subclass instances using the same tag as the superclass. This
means that any instances created during deserialization will always
be of the superclass (subclass instances will never be read from an ASDF file).

Another option (useful when modifying the existing Converter is not
convenient) is to define a Converter that does not tag the subclass instance
being serialized and instead defers to the existing Converter. Deferral
is triggered by returning ``None`` from ``Converter.select_tag`` and
implementing ``Converter.to_yaml_tree`` to convert the subclass instance
into an instance of the (supported) superclass.

For example, using the example ``Rectangle`` class above, let's say we
have another class, ``AspectRectangle``, that represents a rectangle as
a height and aspect ratio. We know we never need to deserialize this
class for our uses and are ok with always reading ``Rectangle`` instances
after saving ``AspectRectangle`` instances. In this case we can
define a Converter for ``AspectRectangle`` that converts instances
to ``Rectangle`` and defers to the ``RectangleConverter``.

.. code-block:: python

    class AspectRectangle(Rectangle):
        def __init__(self, height, ratio):
            self.height = height
            self.ratio = ratio

        def get_area(self):
            width = self.height * self.ratio
            return width * self.height


    class AspectRectangleConverter(Converter):
        tags = []
        types = [AspectRectangle]

        def select_tag(self, obj, tags, ctx):
            return None  # defer to a different Converter

        def to_yaml_tree(self, obj, tag, ctx):
            # convert the instance of AspectRectangle (obj) to
            # a supported type (Rectangle)
            return Rectangle(obj.height * obj.ratio, obj.height)

        def from_yaml_tree(self, node, tag, ctx):
            raise NotImplementedError()

Just like a non-deferring Converter this Converter will need to be
added to an Extension and registered with asdf.

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

            obj = FractionWithInverse(tree["numerator"], tree["denominator"])
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

The presence of `~asdf.treeutil._PendingValue` is asdf's way of telling us
that the value corresponding to the key ``inverse`` was not fully deserialized
at the time that we retrieved it.  We can handle this situation by making our
``from_yaml_tree`` a generator function:

.. code-block:: python

        def from_yaml_tree(self, node, tag, ctx):
            from example_project.fractions import FractionWithInverse

            obj = FractionWithInverse(tree["numerator"], tree["denominator"])
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

.. _extending_converter_block_storage:

Block storage
=============

As described above :ref:`extending_converters` can return complex objects that will
be passed to other Converters. If a Converter returns a ndarray, ASDF will recognize this
array and store it in an ASDF block. This is the easiest and preferred means of
storing data in ASDF blocks.

For applications that require more flexibility,
Converters can control block storage through use of the ``SerializationContext``
provided as an argument to `Converter.to_yaml_tree` `Converter.from_yaml_tree` and `Converter.select_tag`.

It is helpful to first review some details of how ASDF
:ref:`stores block <asdf-standard:block>`. Blocks are stored sequentially within a
ASDF file following the YAML tree. During reads and writes, ASDF will need to know
the index of the block a Converter would like to use to read or write the correct
block. However, the index used for reading might not be the same index for writing
if the tree was modified or the file is being written to a new location. To allow
ASDF to track the relationship between blocks and objects, Converters will need
to generate unique hashable keys for each block used and associate these keys with
block indices during read and write (more on this below).

.. note::
   Use of ``id(obj)`` will not generate a unique key as it returns the memory address
   which might be reused after the object is garbage collected.

A simple example of a Converter using block storage to store the ``payload`` for
``BlockData`` object instances is as follows:

.. runcode::

    import asdf
    import numpy as np
    from asdf.extension import Converter, Extension

    class BlockData:
        def __init__(self, payload):
            self.payload = payload
            self._asdf_key = asdf.util.BlockKey()


    class BlockConverter(Converter):
        tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
        types = [BlockData]

        def to_yaml_tree(self, obj, tag, ctx):
            block_index = ctx.find_block_index(
                obj._asdf_key,
                lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload),
            )
            return {"block_index": block_index}

        def from_yaml_tree(self, node, tag, ctx):
            block_index = node["block_index"]
            obj = BlockData(b"")
            ctx.assign_block_key(block_index, obj._asdf_key)
            obj.payload = ctx.get_block_data_callback(block_index)()
            return obj

        def reserve_blocks(self, obj, tag):
            return [obj._asdf_key]

    class BlockExtension(Extension):
        tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
        converters = [BlockConverter()]
        extension_uri = "asdf://somewhere.org/extensions/block_data-1.0.0"

    with asdf.config_context() as cfg:
        cfg.add_extension(BlockExtension())
        ff = asdf.AsdfFile({"example": BlockData(b"abcdefg")})
        ff.write_to("block_converter_example.asdf")

.. asdf:: block_converter_example.asdf

During read, ``Converter.from_yaml_tree`` will be called. Within this method
the Converter should associate any used blocks with unique hashable keys by calling
``SerializationContext.assign_block_key`` and can generate (and use) a callable
function that will return block data using ``SerializationContext.get_block_data_callback``.
A callback for reading the data is provided to support lazy loading without
keeping a reference to the ``SerializationContext`` (which is meant to be
a short lived and lightweight object).

During write, ``Converter.to_yaml_tree`` will be called. The Converter should
use ``SerializationContext.find_block_index`` to find the location of an
available block by providing a hashable key unique to this object (this should
be the same key used during reading to allow ASDF to associate blocks and objects
during in-place updates). The second argument to ``SerializationContext.find_block_index``
must be a callable function (returning a ndarray) that ASDF will call when it
is time to write data to the portion of the file corresponding to this block.
Note that it's possible this callback will be called multiple times during a
write and ASDF will not cache the result. If the data is coming from a non-repeatable
source (such as a non-seekable stream of bytes) the data should be cached prior
to providing it to ASDF to allow ASDF to call the callback multiple times.

A Converter that uses block storage must also define ``Converter.reserve_blocks``.
``Converter.reserve_blocks`` will be called during memory management to free
resources for unused blocks. ``Converter.reserve_blocks`` must
return a list of keys associated with an object.

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
