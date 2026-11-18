.. _glossary:

********
Glossary
********

.. glossary::

    tag
        A YAML tag identifying the type of a :term:`tree node`, such as
        ``tag:stsci.edu:asdf/core/ndarray-1.1.0``.  Tags select the schema
        a node is validated against and the converter used to turn it into
        a Python object.  See :ref:`extending_uris`.

    tagged tree
        A :term:`tree` made up only of basic Python data types (`dict`,
        `list`, `str` and numbers), wrapped in `asdf.tagged.Tagged`
        subclasses that record each node's :term:`tag`.  This is the
        intermediate form between YAML and custom Python objects, and is
        the form in which the tree is validated against schemas.  See
        `asdf.tagged` and `asdf.yamlutil`.

    tree
        The structured, YAML-encoded content of an ASDF file: a nested
        combination of mappings, sequences and scalars.  In Python the tree
        is a `dict` at the top level, available as `asdf.AsdfFile.tree`, and
        may contain objects of any type supported by an installed extension.
        See :ref:`data-model`.

    tree node
        Any value within a :term:`tree`, from the top-level mapping down to
        an individual string or number, including the objects converters
        create for :term:`tagged <tag>` nodes, such as numpy arrays.
