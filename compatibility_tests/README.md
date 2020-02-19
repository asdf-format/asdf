ASDF file compatibility tests
=============================
These tests confirm that files produced by the latest library code can be
read by earlier releases of the library, and vice versa.  The tests obtain
a list of released versions from pypi.org and install each tested version
into a virtualenv, so an internet connection is required to run them.

The tests in this directory are excluded from the normal test suite, but
can be run (from the repo root directory) with
`pytest compatibility_tests/ --remote-data`.