# Overview

Let's start by taking a look at a few basic ASDF use cases. This will
introduce you to some of the core features of ASDF and will show you how
to get started with using ASDF in your own projects.

To follow along with this tutorial, you will need to install the `asdf`
package. See `installation` for details.

## Hello World

At its core, ASDF is a way of saving nested data structures to YAML.
Here we save a `dict` with the key/value pair `'hello': 'world'`.

```pycon
>>> from asdf import AsdfFile

>>> # Make the tree structure, and create a AsdfFile from it.
>>> tree = {'hello': 'world'}
>>> ff = AsdfFile(tree)
>>> ff.write_to("test.asdf")

>>> # You can also make the AsdfFile first, and modify its tree directly:
>>> ff = AsdfFile()
>>> ff.tree['hello'] = 'world'
>>> ff.write_to("test.asdf")

```

``` yaml
#ASDF 1.0.0
#ASDF_STANDARD 1.6.0
%YAML 1.1
%TAG ! tag:stsci.edu:asdf/
--- !core/asdf-1.1.0
asdf_library: !core/software-1.0.0 {author: The ASDF Developers, homepage: 'http://github.com/asdf-format/asdf',
  name: asdf, version: 5.3.0}
history:
  extensions:
  - !core/extension_metadata-1.0.0
    extension_class: asdf.extension._manifest.ManifestExtension
    extension_uri: asdf://asdf-format.org/core/extensions/core-1.6.0
    manifest_software: !core/software-1.0.0 {name: asdf_standard, version: 1.5.0}
    software: !core/software-1.0.0 {name: asdf, version: 5.3.0}
hello: world
...
```

## Creating Files

--8<-- "README.md:create-file"

A rendering of the binary data contained in the file can be found below.
Observe that the value of `source` in the metadata corresponds to the
block number (e.g. `BLOCK 0`) of the block which contains the binary
data.

--8<-- "README.md:compress-file"

## Reading Files

--8<-- "README.md:read-file"
