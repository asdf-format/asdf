import http.server
import os
import queue
import shutil
import socketserver
import tempfile
import threading

__all__ = ["HTTPServer"]


def run_server(tmp_path, handler_class, stop_event, queue):  # pragma: no cover
    """
    Runs an HTTP server serving files from given tmp_path in a separate
    process.  When it's ready, it sends a URL to the server over a
    queue so the main process (the HTTP client) can start making
    requests of it.
    """

    class HTTPRequestHandler(handler_class):
        def translate_path(self, path):
            path = handler_class.translate_path(self, path)
            return os.path.join(tmp_path, os.path.relpath(path, os.getcwd()))

    server = socketserver.TCPServer(("127.0.0.1", 0), HTTPRequestHandler)
    domain, port = server.server_address
    url = f"http://{domain}:{port}/"

    # Set a reasonable timeout so that invalid requests (which may occur during
    # testing) do not cause the entire test suite to hang indefinitely
    server.timeout = 0.1

    queue.put(url)

    # Using server.serve_forever does not work here since it ignores the
    # timeout value set above. Having an explicit loop also allows us to kill
    # the server from the parent thread.
    while not stop_event.is_set():
        server.handle_request()

    server.server_close()


class HTTPServer:
    handler_class = http.server.SimpleHTTPRequestHandler

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()

        q = queue.Queue()
        self.stop_event = threading.Event()

        args = (self.tmpdir, self.handler_class, self.stop_event, q)
        self.thread = threading.Thread(target=run_server, args=args)
        self.thread.start()

        self.url = q.get()

    def finalize(self):
        self.stop_event.set()
        self.thread.join()
        shutil.rmtree(self.tmpdir)
