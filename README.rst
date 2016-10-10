asdf
====
.. image:: https://readthedocs.org/projects/pyasdf/badge/?version=latest
    :target: http://pyasdf.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://coveralls.io/repos/spacetelescope/asdf/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/spacetelescope/asdf?branch=master

.. image:: https://travis-ci.org/spacetelescope/asdf.svg?branch=master
    :target: https://travis-ci.org/spacetelescope/asdf

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org
    :alt: Powered by Astropy Badge

Python library for reading and writing ASDF files.


Advanced Scientific Data Format (ASDF) is a next generation
interchange format for scientific data.

Installation
------------

To clone the project from github and initialize the asdf-standard submodule::

    git clone https://github.com/spacetelescope/asdf.git
    cd asdf/asdf_standard
    git submodule init
    git submodule update

To install::

    python setup.py install


Testing
-------

To run the unit tests::

    python setup.py test
