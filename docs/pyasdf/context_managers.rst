.. _context-managers:

Context managers
================

`~pyasdf.AsdfFile` objects can be used as context managers to be used
with ``with`` statements to help ensure that the underlying files are
automatically closed.  There is no single pattern to recommend when
using `~pyasdf.AsdfFile` objects as context managers, but it will
instead depend on the context (no pun intended) in which they are
used.

For example, basic writing and reading of a file::

  >>> import pyasdf
  >>> tree = {'key': 'value'}
  >>> with pyasdf.AsdfFile(tree).write_to('test.asdf'):
  ...     pass

  >>> with pyasdf.AsdfFile.read('test.asdf') as ff:
  ...     print(ff.tree['key'])
  value

The reason that `~pyasdf.AsdfFile.write_to` and
`~pyasdf.AsdfFile.read` functions do not automatically close the file
(unless used with ``with`` statements), is to allow for updating the
file in-place later on.  For example::

  >>> with pyasdf.AsdfFile.read('test.asdf', mode='rw') as ff:
  ...     ff.tree['key'] = 'new value'
  ...     ff.update()

You may also want to write the same file, with small modifications, to
a number of different files on disk, in which case a context manager
can be used for each write.

  >>> ff = pyasdf.AsdfFile(tree)

  >>> with ff.write_to('a.asdf'):
  ...     pass

  >>> ff.tree['key'] = 'new value'
  >>> with ff.write_to('b.asdf'):
  ...     pass
