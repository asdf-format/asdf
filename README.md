ASDF - Advanced Scientific Data Format
======================================

[![Build Status](https://travis-ci.org/spacetelescope/asdf.svg?branch=master)](https://travis-ci.org/spacetelescope/asdf)
[![Documentation Status](https://readthedocs.org/projects/asdf/badge/?version=latest)](http://asdf.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/spacetelescope/asdf/badge.svg?branch=master)](https://coveralls.io/github/spacetelescope/asdf?branch=master)
[![stsci](https://img.shields.io/badge/powered%20by-STScI-blue.svg?colorA=707170&colorB=3e8ddd&style=flat)](http://www.stsci.edu)
[![astropy](http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat)](http://www.astropy.org/)

![STScI Logo](docs/_static/stsci_logo.png)


The **A**dvanced **S**cientific **D**ata **F**ormat (ASDF) is a next-generation
interchange format for scientific data. This package contains the Python
implementation of the ASDF Standard.

> If you are looking for the **A**daptable **S**eismic **D**ata **F**ormat,
> information can be found [here](https://seismic-data.org/).


Installation
------------

To clone the project from github and initialize the asdf-standard submodule::

```
$ git clone https://github.com/spacetelescope/asdf.git
$ cd asdf/asdf_standard
$ git submodule update --init
```

To install:

```
$ python setup.py install
```

Testing
-------

To run the unit tests::

```
$ python setup.py test
```

Please note that you must have [astropy](https://github.com/astropy/astropy)
package installed to run the tests.

Contributing Code, Documentation or Feedback
--------------------------------------------
We welcome feedback and contributions to the project. Please follow the
[contributing guidelines](CONTRIBUTING.md) to submit an issue or a pull request.

We strive to provide a welcoming community to all of our users by abiding to the
[Code of Conduct](CODE_OF_CONDUCT.md).
