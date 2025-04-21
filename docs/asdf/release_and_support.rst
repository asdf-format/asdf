.. currentmodule:: asdf

.. _release_and_support:

*************************************************
Release Cycle and Major Dependency Support Policy
*************************************************

This document describes a general plan for releasing the asdf library, along with
how long we intend to support each release. Moreover, it also describes our policy
for how long we plan to support versions of CPython and NumPy. Note that this is
a living document, and may be updated at any time.

.. _backwards_compatibility:

Backwards Compatibility and Semantic Versioning
===============================================

We will maintain a backwards compatible API for all minor and patch versions.
Any breaking API changes will only be included in major releases (where the
major version number will be increased). We follow
`Semantic Versioning <https://semver.org/>`_.

.. _release_cycle:

Release Cycle
=============

As asdf is still under active development, it will continue to be developed on a
rolling release cycle. This means that asdf will not have a fixed release
schedule, but rather will be released as needed.

.. _dependency_support_policy:

Dependency Support Policy
=========================

As a scientific Python library, we follow
`SPEC 0 <https://scientific-python.org/specs/spec-0000/>`_.
