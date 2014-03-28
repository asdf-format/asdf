PyFINF
======

Python library for reading and writing FINF files.

FINF (FINF is not FITS) is a next generation interchange format for
astronomical data.

Installation
------------
This package uses a ``git submodule`` to get the schema information
from the FINF standard itself.  Therefore, you need to run the
following once::

    git submodule init

and the every time you update the repository::

    git submodule update

[We'll try to automate this in a future revision].

To install::

    python setup.py install

Testing
-------
To run the unit tests::

    python setup.py test
