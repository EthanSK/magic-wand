"""A second read-only dashboard using the existing reader; never opens hardware."""
import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, page, **kwargs):
        self.page = page
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path in ('/', '/all-sensors.html'):
            data = self.page.read_bytes()
            status, content_type = 200, 'text/html; charset=utf-8'
        elif self.path == '/api/sample':
            try:
                with urlopen('http://127.0.0.1:8769/api/sample', timeout=2) as response:
                    data = response.read()
                status, content_type = 200, 'application/json'
            except (URLError, TimeoutError, OSError):
                data = json.dumps({'error': 'Existing sensor reader unavailable'}).encode()
                status, content_type = 502, 'application/json'
        else:
            self.send_error(404)
            return
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page', type=Path, default=Path(__file__).with_name('all-sensors.html'))
    parser.add_argument('--port', type=int, default=8770)
    options = parser.parse_args()
    page = options.page.resolve(strict=True)
    server = ThreadingHTTPServer(('127.0.0.1', options.port), partial(Handler, page=page))
    print(f'Control Hand all-six dashboard: http://127.0.0.1:{options.port}/', flush=True)
    print('Uses the existing sensor reader on port 8769. No hardware connections are opened.', flush=True)
    server.serve_forever()
