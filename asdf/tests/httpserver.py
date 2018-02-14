# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os
import shutil
import multiprocessing

import six
import tempfile

from ..extern.RangeHTTPServer import RangeHTTPRequestHandler


__all__ = ['HTTPServer', 'RangeHTTPServer']


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
