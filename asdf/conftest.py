# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

# This contains pytest fixtures used in asdf tests.
# by importing them here in conftest.py they are discoverable by pytest
# no matter how it is invoked within the source tree.


import pytest

from .tests.httpserver import HTTPServer, RangeHTTPServer


@pytest.fixture()
def httpserver(request):
    """
    The returned ``httpserver`` provides a threaded HTTP server
    instance.  It serves content from a temporary directory (available
    as the attribute tmpdir) at randomly assigned URL (available as
    the attribute url).

    * ``tmpdir`` - path to the tmpdir that it's serving from (str)
    * ``url`` - the base url for the server
    """
    server = HTTPServer()
    request.addfinalizer(server.finalize)
    return server


@pytest.fixture()
def rhttpserver(request):
    """
    The returned ``httpserver`` provides a threaded HTTP server
    instance.  It serves content from a temporary directory (available
    as the attribute tmpdir) at randomly assigned URL (available as
    the attribute url).  The server supports HTTP Range headers.

    * ``tmpdir`` - path to the tmpdir that it's serving from (str)
    * ``url`` - the base url for the server
    """
    server = RangeHTTPServer()
    request.addfinalizer(server.finalize)
    return server
