asdf
====

[![Build Status](https://travis-ci.org/spacetelescope/asdf.svg?branch=master)](https://travis-ci.org/spacetelescope/asdf) [![Documentation Status](https://readthedocs.org/projects/asdf/badge/?version=latest)](http://asdf.readthedocs.io/en/latest/?badge=latest) [![Coverage Status](https://coveralls.io/repos/github/spacetelescope/asdf/badge.svg?branch=master)](https://coveralls.io/github/spacetelescope/asdf?branch=master) [![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

Python library for reading and writing ASDF files.


Advanced Scientific Data Format (ASDF) is a next generation
interchange format for scientific data.

> This is the **A**dvanced **S**cientific **D**ata **F**ormat - if you are looking for the **A**daptable **S**eismic **D**ata **F**ormat, go here: http://seismic-data.org/


Installation
------------

To clone the project from github and initialize the asdf-standard submodule::

```python
    git clone https://github.com/spacetelescope/asdf.git
    cd asdf/asdf_standard
    git submodule update --init
```

To install::

```python
    python setup.py install
```

Testing
-------

To run the unit tests::

```python
    python setup.py test
```
