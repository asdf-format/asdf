.. _developer_api:

*************
Developer API
*************

The classes and functions documented here will be of use to developers who wish
to create their own custom ASDF types and extensions.

.. automodapi:: asdf.asdf
    :no-inheritance-diagram:
    :include: SerializationContext
    :skip: AsdfConversionWarning, AsdfDeprecationWarning, AsdfObject, AsdfSearchResult, AsdfWarning, DelimiterNotFoundError, Extension, ExtensionMetadata, ExtensionProxy, HistoryEntry, Software, ValidationError, Version

.. automodapi:: asdf.tagged

.. automodapi:: asdf.exceptions
    :skip: ValidationError

.. automodapi:: asdf.extension

.. automodapi:: asdf.resource

.. automodapi:: asdf.yamlutil

.. automodapi:: asdf.treeutil

.. automodapi:: asdf.util

.. automodapi:: asdf.versioning

.. automodapi:: asdf.schema

.. automodapi:: asdf.tags.core
    :skip: ExternalArrayReference
    :skip: IntegerType
    :no-inheritance-diagram:

.. automodapi:: asdf.testing.helpers

.. automodapi:: asdf.tests.helpers
