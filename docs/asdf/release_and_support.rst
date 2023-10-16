.. currentmodule:: asdf

.. _release_and_support:

*************************************************
Release Cycle and Major Dependency Support Policy
*************************************************

This document describes a general plan for releasing the ASDF library, along with
how long we intend to support each release. Moreover, it also describes our policy
for how long we plan to support versions of CPython and NumPy. Note that this is
a living document, and may be updated at any time.

.. _backwards_compatibility:

Backwards Compatibility and Semantic Versioning
===============================================

ASDF will maintain a backwards compatible API for all minor and patch versions.
Any breaking API changes will only be included in major releases (where the
major version number will be increased). We follow
`Semantic Versioning <https://semver.org/>`_.

.. note::

   We are planning to clean up the public API following the 2.15 release. We
   will attempt to do so with the smallest number of major version changes. If
   there are portions of the ASDF API that you are using that are not documented
   in the :ref:`user_api` or :ref:`developer_api` please
   `open an issue <https://github.com/asdf-format/asdf/issues/new>`_.

.. _release_cycle:

Release Cycle
=============

As ASDF is still under active development, it will continue to be developed on a
rolling release cycle. This means that ASDF will not have a fixed release
schedule, but rather will be released as needed.

.. _dependency_support_policy:

Dependency Support Policy
=========================

ASDF primarily depends on CPython and NumPy. As a scientific Python library, we
have chosen to abide by the policy laid out in
`NEP 29 <https://numpy.org/neps/nep-0029-deprecation_policy.html>`_.
The following table summarizes this policy:

============ ====== =====
Date         Python NumPy
------------ ------ -----
Jan 31, 2023 3.8+   1.21+
Apr 14, 2023 3.9+   1.21+
Jun 23, 2023 3.9+   1.22+
Jan 01, 2024 3.9+   1.23+
Apr 05, 2024 3.10+  1.23+
Jun 22, 2024 3.10+  1.24+
Dec 18, 2024 3.10+  1.25+
Apr 04, 2025 3.11+  1.25+
Apr 24, 2026 3.12+  1.25+
============ ====== =====

.. _drop_schedule:

CPython and NumPy Drop Schedule
-------------------------------

::

  On Jan 31, 2023 drop support for NumPy 1.20 (initially released on Jan 31, 2021)
  On Apr 14, 2023 drop support for Python 3.8 (initially released on Oct 14, 2019)
  On Jun 23, 2023 drop support for NumPy 1.21 (initially released on Jun 22, 2021)
  On Jan 01, 2024 drop support for NumPy 1.22 (initially released on Dec 31, 2021)
  On Apr 05, 2024 drop support for Python 3.9 (initially released on Oct 05, 2020)
  On Jun 22, 2024 drop support for NumPy 1.23 (initially released on Jun 22, 2022)
  On Dec 18, 2024 drop support for NumPy 1.24 (initially released on Dec 18, 2022)
  On Apr 04, 2025 drop support for Python 3.10 (initially released on Oct 04, 2021)
  On Apr 24, 2026 drop support for Python 3.11 (initially released on Oct 24, 2022)

.. _support_for_other_dependencies:

Support for Other Dependencies
------------------------------

ASDF also depends on several other Python packages. We currently do not have a
formal policy for how long we intend to support these dependencies. However, we
will try to support as many versions of these dependencies as possible.

In general, we will pin each of these dependencies from below with the oldest
version that we guarantee will work with ASDF. We will also try to test against
the latest version of each of these dependencies and release bugfixes to supported
versions of ASDF on an as-needed basis. We will try our best to announce when we
need to bump the support of these dependencies, and will always record doing so
(and why) in the changelog.

If you find any issues with ASDF dependencies which affect a currently-supported
version of ASDF, please open an issue in the ASDF repository.
