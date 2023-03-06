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

  - ``remove-hdu``: Remove ASDF extension from ASDF-in-FITS file (requires
    :ref:`astropy:getting-started`, see :ref:`asdf-in-fits`).
    This command is deprecated as part of ASDF dropping support for
    ASDF-in-FITS. See :ref:`asdf-in-fits` for migration information.

  - ``info``: Print a rendering of an ASDF tree.

  - ``extensions``: Show information about installed extensions (see
    :ref:`other_packages`).

  - ``tags``: List currently available tags.

  - ``to_yaml``: Inline all of the data in an ASDF file so that it is
    pure YAML.

Run ``asdftool --help`` for more information.
