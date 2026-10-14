"""DEV ONLY: static server for app/ with a larger accept queue than `python3 -m http.server` (which drops connections
when the headless checks open many files at once). Usage: python3 app/dev/serve.py [port]"""
import functools, http.server, sys
from pathlib import Path


class S(http.server.ThreadingHTTPServer):
    request_queue_size = 256
    daemon_threads = True


H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parents[1]))
H.log_message = lambda *a: None
S(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
