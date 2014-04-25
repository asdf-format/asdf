# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

# this contains imports plugins that configure py.test for astropy tests.
# by importing them here in conftest.py they are discoverable by py.test
# no matter how it is invoked within the source tree.

from astropy.tests.pytest_plugins import *

## Uncomment the following line to treat all DeprecationWarnings as
## exceptions
enable_deprecations_as_exceptions()


import os
import shutil
import tempfile
import threading

from astropy.extern import six
from astropy.tests.helper import pytest

from .extern.RangeHTTPServer import RangeHTTPRequestHandler


class HTTPServerThread(threading.Thread):
    handler_class = six.moves.SimpleHTTPServer.SimpleHTTPRequestHandler

    def __init__(self):
        super(HTTPServerThread, self).__init__()
        self.tmpdir = tmpdir = tempfile.mkdtemp()
        handler_class = self.handler_class

        class HTTPRequestHandler(self.handler_class):
            def translate_path(self, path):
                path = handler_class.translate_path(self, path)
                path = os.path.join(
                    tmpdir,
                    os.path.relpath(path, os.getcwd()))
                return path

        self._server = six.moves.socketserver.TCPServer(
            ("127.0.0.1", 0), HTTPRequestHandler)
        domain, port = self._server.server_address
        self.url = "http://{0}:{1}/".format(domain, port)

    def run(self):
        self._server.serve_forever()

    def stop(self):
        self._server.shutdown()
        shutil.rmtree(self.tmpdir)


class RangeHTTPServerThread(HTTPServerThread):
    handler_class = RangeHTTPRequestHandler


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
    server = HTTPServerThread()
    server.start()
    request.addfinalizer(server.stop)
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
    server = RangeHTTPServerThread()
    server.start()
    request.addfinalizer(server.stop)
    return server
