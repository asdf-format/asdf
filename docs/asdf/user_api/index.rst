.. _user_api:

********
User API
********

The classes and functions documented here are the main interface for working
with ASDF files: opening, reading and writing them (see `asdf.open` and
`asdf.AsdfFile`), searching their trees, and configuring how ASDF output
behaves.

Developers who wish to support their own custom types and extensions should
also see the :ref:`developer_api`.

.. toctree::
    :maxdepth: 2
    :hidden:

    asdf_package.rst
    asdf_search.rst
    asdf_config.rst
    asdf_typing.rst

.. autosummary::

    asdf
    asdf.search
    asdf.config
    asdf.typing
