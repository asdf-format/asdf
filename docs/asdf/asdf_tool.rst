Commandline tool
----------------

``asdf`` includes a command-line tool, ``asdftool`` that performs a
number of basic operations:

  - ``explode``: Convert a self-contained ASDF file into exploded form.

  - ``implode``: Convert an ASDF file in exploded form into a
    self-contained file.

  - ``to_yaml``: Inline all of the data in an ASDF file so that it is
    pure YAML.

  - ``defragment``: Remove unused blocks and extra space.

Run ``asdftool --help`` for more information.
