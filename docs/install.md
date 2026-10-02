# Installation

There are several different ways to install the
[`asdf`][asdf] package. Each is described in detail
below.

## Requirements

The [`asdf`][asdf] package has several dependencies
which are listed in the project's build configuration `pyproject.toml`.
All dependencies are available on pypi and will be automatically
installed along with [`asdf`][asdf].

Support for units, time, and transform tags requires an implementation
of these types. One recommended option is the
[asdf-astropy](https://asdf-astropy.readthedocs.io/en/latest/) package.

Optional support for
[lz4](https://en.wikipedia.org/wiki/LZ4_(compression_algorithm))
compression is provided by the [lz4](https://python-lz4.readthedocs.io/)
package.

## Installing with pip

--8<-- "README.md:pip-install"

## Installing with conda

[`asdf`][asdf] is also distributed as a
[conda](https://conda.io/docs/) package via the
[conda-forge](https://conda-forge.org/) channel. It is also available
through the [astroconda](https://astroconda.readthedocs.io/en/latest/)
channel.

To install [`asdf`][asdf] within an existing conda
environment:

    $ conda install -c conda-forge asdf

To create a new conda environment and install `asdf`:

    $ conda create -n new-env-name -c conda-forge python asdf

## Building from source

--8<-- "README.md:source-install"

## Running the tests

--8<-- "README.md:testing"
