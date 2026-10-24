#!/usr/bin/env python3
"""Magic Wand live monitor: a read-only local page over Wand Receiver's own files.

Run from the magic-wand folder:  python3 debug/server.py
Then open http://127.0.0.1:8770/

The installed Wand Receiver is the wand's only Bluetooth owner. This server never
opens Bluetooth, never signals or restarts the receiver, never writes its files and
never posts input. It serves a fixed set of page files and one JSON snapshot.
"""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor import DEFAULT_SUPPORT, RECEIVER_PROCESS, Monitor, ProcessProbe  # noqa: E402

HERE = Path(__file__).resolve().parent
FONTS = HERE.parents[1] / "docs" / "fonts"
DEFAULT_PORT = 8770
BIND = "127.0.0.1"

# A fixed allowlist: request paths never reach the filesystem directly.
STATIC = {
    "/": (HERE / "index.html", "text/html; charset=utf-8"),
    "/index.html": (HERE / "index.html", "text/html; charset=utf-8"),
    "/app.js": (HERE / "app.js", "text/javascript; charset=utf-8"),
    "/styles.css": (HERE / "styles.css", "text/css; charset=utf-8"),
    "/fonts/display.woff2": (FONTS / "big-shoulders-display.woff2", "font/woff2"),
    "/fonts/body.woff2": (FONTS / "atkinson-hyperlegible-next.woff2", "font/woff2"),
    "/fonts/mono.woff2": (FONTS / "atkinson-hyperlegible-mono.woff2", "font/woff2"),
}
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; "
                               "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'",
}


def make_handler(monitor: Monitor, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "MagicWandMonitor/1"
        sys_version = ""

        def _send(self, code: int, body: bytes, content_type: str, head: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def _refuse(self, code: int, message: str, head: bool = False) -> None:
            self._send(code, (message + "\n").encode(), "text/plain; charset=utf-8", head)

        def _get(self, head: bool) -> None:
            # Rejecting other Host names stops a remote page from reading this
            # over DNS rebinding, even though the socket only listens locally.
            if self.headers.get("Host", "") not in allowed_hosts:
                self._refuse(403, "Open this monitor at http://127.0.0.1:%d/" % port, head)
                return
            path = self.path.split("?", 1)[0]
            if path == "/api/state":
                body = json.dumps(monitor.snapshot(), allow_nan=False, separators=(",", ":")).encode()
                self._send(200, body, "application/json; charset=utf-8", head)
                return
            entry = STATIC.get(path)
            if entry is None:
                self._refuse(404, "Not found", head)
                return
            try:
                body = entry[0].read_bytes()
            except OSError:
                self._refuse(404, "Not found", head)
                return
            self._send(200, body, entry[1], head)

        def do_GET(self) -> None:  # noqa: N802
            self._get(head=False)

        def do_HEAD(self) -> None:  # noqa: N802
            self._get(head=True)

        def _read_only(self) -> None:
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            for name, value in SECURITY_HEADERS.items():
                self.send_header(name, value)
            self.end_headers()

        do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only  # noqa: N815

        def log_message(self, *_args) -> None:
            pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Magic Wand monitor on 127.0.0.1.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="local port (default %(default)s; 0 picks a free port)")
    parser.add_argument("--support-dir", type=Path, default=DEFAULT_SUPPORT,
                        help="folder holding status.json and receiver.log (default: Wand Receiver's own folder)")
    parser.add_argument("--process-name", default=RECEIVER_PROCESS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    monitor = Monitor(args.support_dir, ProcessProbe(expected=args.process_name))
    try:
        server = ThreadingHTTPServer((BIND, args.port), make_handler(monitor, args.port))
    except OSError as error:
        print("Couldn’t listen on %s:%d: %s" % (BIND, args.port, error.strerror or error), file=sys.stderr)
        return 1
    port = server.server_address[1]
    if args.port == 0:
        server.RequestHandlerClass = make_handler(monitor, port)
    server.daemon_threads = True
    print("Magic Wand monitor: http://%s:%d/" % (BIND, port), flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
