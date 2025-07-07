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

.. _converter_interface:

The Converter interface
=======================

Every Converter implementation must provide two required properties and
two required methods:

`Converter.tags` - a list of tag URIs or URI patterns handled by the converter.
Patterns may include the wildcard character ``*``, which matches any sequence of
characters up to a ``/``, or ``**``, which matches any sequence of characters.
The `~asdf.util.uri_match` method can be used to test URI patterns.

`Converter.types` - a list of Python types or fully-qualified Python type names handled
by the converter. For strings, the private or public path can be used. For example,
if class ``Foo`` is implemented in ``example_package.foo.Foo`` but imported
as ``example_package.Foo`` for convenience either ``example_package.foo.Foo``
or ``example_package.Foo`` can be used. As most libraries do not consider moving
where a class is implemented it is preferred to use the "public" location
where the class is imported (in this example ``example_package.Foo``).

The string type name is recommended over a type object for performance reasons,
see :ref:`extending_converters_performance`.

`Converter.to_yaml_tree` - a method that accepts a complex Python object and returns
a simple node object (typically a `dict`) suitable for serialization to YAML.  The
node is permitted to contain nested complex objects; these will in turn
be passed to other ``to_yaml_tree`` methods in other Converters.

`Converter.from_yaml_tree` - a method that accepts a simple node object from parsed YAML and
returns the appropriate complex Python object.  For a non-lazy-tree, nested
nodes in the received node will have already been converted to complex objects
by other calls to ``from_yaml_tree`` methods, except where reference cycles are present -- see
:ref:`extending_converters_reference_cycles` for information on how to handle that
situation. For a ``lazy_tree`` (see `asdf.open`) the node will contain `asdf.lazy_nodes`
instances which act like dicts and lists but convert child objects only when they are
accessed.

Additionally, the Converter interface includes a method that must be implemented
when some logic is required to select the tag to assign to a ``to_yaml_tree`` result:

`Converter.select_tag<Converter>` - an optional method that accepts a complex Python object and a list
of candidate tags and returns the tag that should be used to serialize the object.

`Converter.lazy<Converter>` - a boolean attribute indicating if this converter accepts "lazy" objects
(those defined in `asdf.lazy_nodes`). This is mostly useful for container-like classes
(where the "lazy" objects can defer conversion of contained objects until they are accessed).
If a converter produces a generator lazy should be set to ``False`` as asdf will need
to generate nodes further out the branch to fully resolve the object returned from the
generator.


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

Now we can include a Rectangle object in an `~asdf.AsdfFile` tree
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
the converter's list of tags and implement a `select_tag<Converter>` method:

.. code-block:: python

    RECTANGLE_TAG = "asdf://example.com/shapes/tags/rectangle-1.0.0"
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


Tag wildcards to support multiple versions
==========================================

As noted above `Converter.tags` can contain wildcard patterns
(``asdf://example.com/shapes/tags/rectangle-1.*`` to match all ``1.x.x`` versions
of the rectangle tag). When a wildcard is used the specific tag
versions should be defined in the manifest (or extension) that uses
the `Converter`. If a `Converter` with a tag wildcard is provided to an
extension with a manifest that contains no tags that match the pattern
the `Converter` will be ignored. No errors or warnings will be produced
when this extension is registered with asdf (as this can be a useful pattern).
However attempts to use the `Converter` can produce errors during
reading and writing (if it's expected that the `Converter` is used).
Developers are encouraged to write unit tests that check reading and
writing with any custom `Converter` instances.

.. _extending_converters_deferral:

Deferring to another converter
==============================

Converters only support the exact types listed in `Converter.types`. When a
supported type is subclassed the extension will need to be updated to support
the new subclass. There are a few options for supporting subclasses.

If serialization of the subclass needs to differ from the superclass a new
Converter, tag and schema should be defined.

If the subclass can be treated the same as the superclass (specifically if
subclass instances can be serialized as the superclass) then the subclass
can be added to the existing `Converter.types`. Note that adding the
subclass to the supported types (without making other changes to the Converter)
will result in subclass instances using the same tag as the superclass. This
means that any instances created during deserialization will always
be of the superclass (subclass instances will never be read from an ASDF file).

Another option (useful when modifying the existing Converter is not
convenient) is to define a Converter that does not tag the subclass instance
being serialized and instead defers to the existing Converter. Deferral
is triggered by returning ``None`` from `Converter.select_tag<Converter>` and
implementing `Converter.to_yaml_tree` to convert the subclass instance
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

    import fractions


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

    import asdf


    class FractionWithInverseConverter(asdf.extension.Converter):
        tags = ["asdf://example.com/fractions/tags/fraction-1.0.0"]
        types = [FractionWithInverse]

        def to_yaml_tree(self, obj, tag, ctx):
            return {
                "numerator": obj.numerator,
                "denominator": obj.denominator,
                "inverse": obj.inverse,
            }

        def from_yaml_tree(self, node, tag, ctx):
            obj = FractionWithInverse(node["numerator"], node["denominator"])
            obj.inverse = node["inverse"]
            return obj

.. warning::

   The type ``FractionsWithInverse`` and not a string was used above to
   keep this example simple. See the note about `Converter.types` as strings
   in the :ref:`converter_interface` section above.

After adding this Converter to an Extension and installing it, the fraction
will serialize correctly:

.. code-block:: python

    class FractionsExtension(asdf.extension.Extension):
        extension_uri = "asdf://example.com/fractions/extensions/fractions-1.0.0"
        converters = [FractionWithInverseConverter()]
        tags = ["asdf://example.com/fractions/tags/fraction-1.0.0"]


    asdf.get_config().add_extension(FractionsExtension())

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
            obj = FractionWithInverse(node["numerator"], node["denominator"])
            yield obj
            obj.inverse = node["inverse"]

The generator version of ``from_yaml_tree`` yields the partially constructed
``FractionWithInverse`` object before setting its inverse property.  This allows
`asdf` to proceed to constructing the inverse ``FractionWithInverse`` object,
and resume the original ``from_yaml_tree`` execution only when the inverse
is actually available.

With this modification we can successfully deserialize our ASDF file:

.. code-block:: python

    with asdf.open("with_inverse.asdf") as af:
        reconstituted_f1 = af["fraction"]

    assert reconstituted_f1.inverse.inverse is reconstituted_f1

.. _extending_converter_block_storage:

Block storage
=============

As described above :ref:`extending_converters` can return complex objects that will
be passed to other Converters. If a Converter returns a ndarray, asdf will recognize this
array and store it in an ASDF block. This is the easiest and preferred means of
storing data in ASDF blocks.

For applications that require more flexibility,
Converters can control block storage through use of the `asdf.extension.SerializationContext`
provided as an argument to `Converter.to_yaml_tree` `Converter.from_yaml_tree` and ``Converter.select_tag``.

It is helpful to first review some details of how asdf
:ref:`stores block <asdf-standard:block>`. Blocks are stored sequentially within a
ASDF file following the YAML tree. During reads and writes, asdf will need to know
the index of the block a Converter would like to use to read or write the correct
block. However, the index used for reading might not be the same index for writing
if the tree was modified or the file is being written to a new location. During
serialization and deserialization, asdf will associate each object with the
accessed block during `Converter.from_yaml_tree` and `Converter.to_yaml_tree`.

.. note::
   Converters using multiple blocks are slightly more complicated.
   See: :ref:`extending_converter_multiple_block_storage`

A simple example of a Converter using block storage to store the ``payload`` for
``BlockData`` object instances is as follows:

.. runcode::

    import asdf
    import numpy as np
    from asdf.extension import Converter, Extension

    class BlockData:
        def __init__(self, payload):
            self.payload = payload


    class BlockConverter(Converter):
        tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
        types = [BlockData]

        def to_yaml_tree(self, obj, tag, ctx):
            block_index = ctx.find_available_block_index(
                lambda: np.ndarray(len(obj.payload), dtype="uint8", buffer=obj.payload),
            )
            return {"block_index": block_index}

        def from_yaml_tree(self, node, tag, ctx):
            block_index = node["block_index"]
            data_callback = ctx.get_block_data_callback(block_index)
            obj = BlockData(data_callback())
            return obj

    class BlockExtension(Extension):
        tags = ["asdf://somewhere.org/tags/block_data-1.0.0"]
        converters = [BlockConverter()]
        extension_uri = "asdf://somewhere.org/extensions/block_data-1.0.0"

    with asdf.config_context() as cfg:
        cfg.add_extension(BlockExtension())
        ff = asdf.AsdfFile({"example": BlockData(b"abcdefg")})
        ff.write_to("block_converter_example.asdf")

.. asdf:: block_converter_example.asdf

During read, `Converter.from_yaml_tree` will be called. Within this method
the Converter can prepare to access a block by calling
``SerializationContext.get_block_data_callback``. This will return a function
that when called will return the contents of the block (to support lazy
loading without keeping a reference to the ``SerializationContext`` (which is meant
to be a short lived and lightweight object).

During write, `Converter.to_yaml_tree` will be called. The Converter can
use ``SerializationContext.find_available_block_index`` to find the location of an
available block for writing. The data to be written to the block can be provided
as an ``ndarray`` or a callable function that will return a ``ndarray`` (note that
it is possible this callable function will be called multiple times and the
developer should cache results from any non-repeatable sources).

.. _extending_converter_multiple_block_storage:

Converters using multiple blocks
--------------------------------

As discussed above, while serializing and deserializing objects that use
one block, asdf will watch which block is accessed by ``find_available_block_index``
and ``get_block_data_callback`` and associate the block with the converted object.
This association allows asdf to map read and write blocks during updates of ASDF
files. An object that uses multiple blocks must provide a unique key for each
block it uses. These keys are generated using ``SerializationContext.generate_block_key``
and must be stored by the extension code. These keys must be resupplied to the converter
when writing an object that was read from an ASDF file.

.. runcode::

    import asdf
    import numpy as np
    from asdf.extension import Converter, Extension

    class MultiBlockData:
        def __init__(self, data):
            self.data = data
            self.keys = []


    class MultiBlockConverter(Converter):
        tags = ["asdf://somewhere.org/tags/multi_block_data-1.0.0"]
        types = [MultiBlockData]

        def to_yaml_tree(self, obj, tag, ctx):
            if not len(obj.keys):
                obj.keys = [ctx.generate_block_key() for _ in obj.data]
            indices = [ctx.find_available_block_index(d, k) for d, k in zip(obj.data, obj.keys)]
            return {
                "indices": indices,
            }

        def from_yaml_tree(self, node, tag, ctx):
            indices = node["indices"]
            keys = [ctx.generate_block_key() for _ in indices]
            cbs = [ctx.get_block_data_callback(i, k) for i, k in zip(indices, keys)]
            obj = MultiBlockData([cb() for cb in cbs])
            obj.keys = keys
            return obj


    class MultiBlockExtension(Extension):
        tags = ["asdf://somewhere.org/tags/multi_block_data-1.0.0"]
        converters = [MultiBlockConverter()]
        extension_uri = "asdf://somewhere.org/extensions/multi_block_data-1.0.0"

    with asdf.config_context() as cfg:
        cfg.add_extension(MultiBlockExtension())
        obj = MultiBlockData([np.arange(3, dtype="uint8") + i for i in range(3)])
        ff = asdf.AsdfFile({"example": obj})
        ff.write_to("multi_block_converter_example.asdf")

.. asdf:: multi_block_converter_example.asdf

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
