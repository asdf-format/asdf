.. currentmodule:: asdf

.. _release_and_support:

*************************************************
Release Cycle and Major Dependency Support Policy
*************************************************

This document describes the general plan for releases of the ASDF library, along
with how long we intend to support each release. Moreover, it also describes our
policy for how long we support versions of CPython and Numpy. Note that this is
a living document, and may be updated at any time.

.. _release_cycle:

Release Cycle
=============

ASDF is and will continue to be developed on a rolling release cycle, as ASDF is
still under active development. This means that ASDF will not have a fixed release
schedule, but rather will be released as needed.

However, we do intend to create and maintain designated "long-term support" (LTS)
branches for at least major version of ASDF in a similar way as what is described
for ``astropy`` in `APE 2 <https://github.com/astropy/astropy-APEs/blob/main/APE2.rst>`_.
This means that for every new major version of ASDF, say version ``a.0`` we will
designate and maintain ``a.0.x`` as the LTS branch of ASDF for at least one year.
During this time we will try to ensure that the LTS branch receives bugfixes and
has regular releases. After one year, we may decide to designate a new LTS branch
for ASDF if no new major versions of ASDF have been released; otherwise, we will
cease to maintain the old LTS branch in favor of the newer one(s). Aside from the
LTS version(s), we will also maintain a rolling current version of ASDF. This support
for these rolling versions will end when the next non-LTS version of ASDF is released.

.. note::

    Since this policy has not yet been implemented, we do not yet formally declared
    a LTS version for ASDF. Our plan is to declare ``2.15`` as an LTS version when it
    is released and move forward to actively working on ASDF ``3.0`` as our main development.
    Once ``3.0`` is released, it will also become a second LTS version of ASDF and we
    will continue to release bugfixes for ASDF ``2.15`` and ``3.0`` for at least one
    year past their release dates.
