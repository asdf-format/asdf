.. currentmodule:: asdf.extension

.. _extending_validators:

==========
Validators
==========

The `~asdf.extension.Validator` interface provides support for a custom
ASDF schema property.  The Validator identifies the schema property and
tag(s) that it works on and provides a method for doing the work of
validation.

The Validator interface
=======================

Every Validator implementation must provide two required properties and
one required method:

`Validator.schema_property` - The schema property that triggers this
validator.  The property need not be globally unique, but it should be
unique among the validators that apply to the tag(s), and must not
collide with any of the built-in JSON schema properties (type, additionalProperties,
etc).

`Validator.tags` - a list of tag URIs or URI patterns handled by the validator.
Patterns may include the wildcard character ``*``, which matches any sequence of
characters up to a ``/``, or ``**``, which matches any sequence of characters.
The `~asdf.util.uri_match` method can be used to test URI patterns.

`Validator.validate` - a method that accepts the schema property value, a tagged ASDF node,
and the surrounding schema dict, and performs validation on the node.  For every error
present, the method should yield an instance of ``asdf.exceptions.ValidationError``.

A simple example
================

Say we have a custom tagged object, ``asdf://example.com/example-project/tags/rectangle-1.0.0``,
which describes a rectangle with ``width`` and ``height`` properties.  Let's implement
a validator that checks that the area of the rectangle is less than some maximum value.

The schema property will be called ``max_area``, so our validator will look like this:

.. code-block:: python

    from asdf.extension import Validator
    from asdf.exceptions import ValidationError


    class MaxAreaValidator(Validator):
        schema_property = "max_area"
        tags = ["asdf://example.com/example-project/tags/rectangle-1.0.0"]

        def validate(self, max_area, node, schema):
            area = node["width"] * node["height"]
            if area > max_area:
                yield ValidationError(
                    f"Rectangle with area {area} exceeds max area of {max_area}"
                )

Note that the validator operates on raw ASDF tagged nodes, and not the custom
Python object that they'll be converted to.

In order to use this Validator, we'll need to create a simple extension
around it and install that extension:

.. code-block:: python

    import asdf
    from asdf.extension import Extension


    class ShapesExtension(Extension):
        extension_uri = "asdf://example.com/shapes/extensions/shapes-1.0.0"
        validators = [MaxAreaValidator()]
        tags = ["asdf://example.com/shapes/tags/rectangle-1.0.0"]


    asdf.get_config().add_extension(ShapesExtension())

Now we can include a ``max_area`` property in a schema and have it
restrict the area of a rectangle.
