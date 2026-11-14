"""Serve the local assembly viewer directly from the working tree."""

import argparse
import os
import plistlib
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VIEWER_PATH = "/magic-wand/hardware/carbon-rod-holders/assembly/"
SERVICE_LABEL = "com.ethansk.magic-wand-assembly-viewer"
LIVE_SUFFIXES = {".html", ".css", ".js", ".mjs", ".json"}


class AssemblyHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = Path(self.translate_path(self.path))
        self.serve_fresh = path.suffix in LIVE_SUFFIXES or path.is_dir()
        if self.serve_fresh:
            # The default handler can return 304 for different bytes saved in the same second.
            del self.headers["If-Modified-Since"]
        return super().send_head()

    def end_headers(self):
        if getattr(self, "serve_fresh", False):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def install_service(port: int, directory: Path) -> None:
    """Let macOS own the server so ending a chat cannot end the viewer."""
    if sys.platform != "darwin":
        raise SystemExit("Automatic login startup requires macOS; run without --install elsewhere.")
    log_directory = Path.home() / "Library/Logs/MagicWandAssemblyViewer"
    log_directory.mkdir(parents=True, exist_ok=True)
    plist_path = Path.home() / "Library/LaunchAgents" / f"{SERVICE_LABEL}.plist"
    arguments = [sys.executable, str(Path(__file__).resolve())]
    if port != 8849:
        arguments += ["--port", str(port)]
    if directory.resolve() != REPO_ROOT:
        arguments += ["--directory", str(directory.resolve())]
    config = {
        "Label": SERVICE_LABEL,
        "ProgramArguments": arguments,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "StandardOutPath": str(log_directory / "stdout.log"),
        "StandardErrorPath": str(log_directory / "stderr.log"),
    }
    # Preserve another checkout's service instead of silently taking over its port.
    if plist_path.exists() and plistlib.loads(plist_path.read_bytes()) != config:
        raise SystemExit(f"Existing {SERVICE_LABEL} settings differ; inspect them before replacing.")
    if not plist_path.exists():
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        with plist_path.open("xb") as output:
            plistlib.dump(config, output)
        plist_path.chmod(0o600)
    domain = f"gui/{os.getuid()}"
    target = f"{domain}/{SERVICE_LABEL}"
    loaded = subprocess.run(["launchctl", "print", target], capture_output=True).returncode == 0
    command = ["launchctl", "kickstart", target] if loaded else ["launchctl", "bootstrap", domain, str(plist_path)]
    subprocess.run(command, check=True)
    print(f"http://127.0.0.1:{port}{VIEWER_PATH}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8849)
    parser.add_argument("--directory", type=Path, default=REPO_ROOT)
    parser.add_argument("--install", action="store_true", help="Keep the viewer running with a macOS login service")
    args = parser.parse_args()
    if args.install:
        install_service(args.port, args.directory)
        return
    handler = partial(AssemblyHandler, directory=args.directory)
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"http://127.0.0.1:{server.server_port}{VIEWER_PATH}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
