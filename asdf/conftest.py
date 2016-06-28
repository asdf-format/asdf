# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

# this contains imports plugins that configure py.test for asdf tests.
# by importing them here in conftest.py they are discoverable by py.test
# no matter how it is invoked within the source tree.

from astropy.tests.pytest_plugins import *

import multiprocessing
import os
import shutil
import tempfile

import pytest

import six

from .extern.RangeHTTPServer import RangeHTTPRequestHandler

# This is to figure out the affiliated package version, rather than
# using Astropy's
from . import version

packagename = os.path.basename(os.path.dirname(__file__))
TESTED_VERSIONS[packagename] = version.version


# Uncomment the following line to treat all DeprecationWarnings as
# exceptions
enable_deprecations_as_exceptions()

try:
    PYTEST_HEADER_MODULES['Astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['jsonschema'] = 'jsonschema'
    PYTEST_HEADER_MODULES['pyyaml'] = 'yaml'
    PYTEST_HEADER_MODULES['six'] = 'six'
    del PYTEST_HEADER_MODULES['h5py']
    del PYTEST_HEADER_MODULES['Matplotlib']
    del PYTEST_HEADER_MODULES['Scipy']
except (NameError, KeyError):
    pass




def run_server(queue, tmpdir, handler_class):  # pragma: no cover
    """
    Runs an HTTP server serving files from given tmpdir in a separate
    process.  When it's ready, it sends a URL to the server over a
    queue so the main process (the HTTP client) can start making
    requests of it.
    """
    class HTTPRequestHandler(handler_class):
        def translate_path(self, path):
            path = handler_class.translate_path(self, path)
            path = os.path.join(
                tmpdir,
                os.path.relpath(path, os.getcwd()))
            return path

    server = six.moves.socketserver.TCPServer(
        ("127.0.0.1", 0), HTTPRequestHandler)
    domain, port = server.server_address
    url = "http://{0}:{1}/".format(domain, port)

    queue.put(url)

    server.serve_forever()


class HTTPServer(object):
    handler_class = six.moves.SimpleHTTPServer.SimpleHTTPRequestHandler

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()

        q = multiprocessing.Queue()
        self.process = multiprocessing.Process(
            target=run_server,
            args=(q, self.tmpdir, self.handler_class))
        self.process.start()
        self.url = q.get()

    def finalize(self):
        self.process.terminate()
        shutil.rmtree(self.tmpdir)


class RangeHTTPServer(HTTPServer):
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
