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
implementation of the ASDF Standard. More information on the ASDF Standard
itself can be found [here](https://asdf-standard.readthedocs.io).

> If you are looking for the **A**daptable **S**eismic **D**ata **F**ormat,
> information can be found [here](https://seismic-data.org/).

ASDF is under active development [on
github](https://github.com/spacetelescope/asdf). More information on
contributing can be found [below](#contributing).

Installation
------------

Stable releases of the ASDF Python package are registered [at
PyPi](https://pypi.python.org/pypi/asdf). The latest stable version can be
installed using `pip`:

```
$ pip install asdf
```

The latest development version of ASDF is available from the `master` branch on
github. To clone the project:

```
$ git clone https://github.com/spacetelescope/asdf
```

To install:

```
$ cd asdf
$ python setup.py install
```

To install in [development mode](https://packaging.python.org/tutorials/distributing-packages/#working-in-development-mode):

```
$ python setup.py develop
```

**NOTE**: The source repository makes use of a git submodules for referencing
the schemas provided by the ASDF standard. While this submodule is automatically
initialized when installing the package (including in development mode), it may
be necessary during the course of development to update the submodule manually.
See the [documentation on git
submodules](https://git-scm.com/docs/git-submodule) for more information.


Testing
-------

To run the unit tests::

```
$ python setup.py test
```

Please note that you must have [astropy](https://github.com/astropy/astropy)
package installed to run the tests.

Contributing
------------
We welcome feedback and contributions to the project. Contributions of code,
documentation, or general feedback are all appreciated. Please follow the
[contributing guidelines](CONTRIBUTING.md) to submit an issue or a pull request.

We strive to provide a welcoming community to all of our users by abiding to the
[Code of Conduct](CODE_OF_CONDUCT.md).
