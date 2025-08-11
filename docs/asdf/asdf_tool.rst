.. _asdf_tool:

Command line tool
-----------------

`asdf` includes a command-line tool, ``asdftool`` that performs a number of
useful operations:

  - ``explode``: Convert a self-contained ASDF file into exploded form (see
    :ref:`exploded`).

  - ``implode``: Convert an ASDF file in exploded form into a
    self-contained file.

  - ``defragment``: Remove unused blocks and extra space.

  - ``diff``: Report differences between two ASDF files.

  - ``edit``: Edit the YAML portion of an ASDF file.

  - ``info``: Print a rendering of an ASDF tree.

  - ``search``: Search an ASDF file.

  - ``extensions``: Show information about installed extensions (see
    :ref:`other_packages`).

  - ``tags``: List currently available tags.

  - ``to_yaml``: Inline all of the data in an ASDF file so that it is
    pure YAML.

  - ``validate``: Validate an ASDF file's blocks and schema.

Run ``asdftool --help`` for more information.
