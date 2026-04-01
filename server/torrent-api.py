#!/usr/bin/env python3
"""
Torrent Directory API for LibreELEC/Linux
Returns directory listings as JSON for the torrent adder GUI
Proxies Transmission RPC so remote clients only need one endpoint
"""

import os
import json
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Default config - overridden by config.json if present
CONFIG = {
    "port": 8765,
    "directories": {
        "movies": "/media/lacie/Media/Movies",
        "tvshows": "/media/lacie/Media/TV Shows",
        "downloads": "/media/lacie/Downloads"
    },
    "transmission": {
        "host": "localhost",
        "port": 9091,
        "username": "",
        "password": ""
    }
}

def load_config():
    """Load config from config.json next to this script"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            loaded = json.load(f)
        # Deep merge transmission and directories
        for key in ("transmission", "directories"):
            if key in loaded:
                CONFIG.setdefault(key, {}).update(loaded[key])
                del loaded[key]
        CONFIG.update(loaded)

def transmission_request(method, arguments=None):
    """Make a request to Transmission RPC, handling the 409 session handshake"""
    tc = CONFIG["transmission"]
    url = f"http://{tc['host']}:{tc['port']}/transmission/rpc"
    payload = json.dumps({"method": method, "arguments": arguments or {}}).encode()

    headers = {"Content-Type": "application/json"}
    if tc.get("username") and tc.get("password"):
        cred = base64.b64encode(f"{tc['username']}:{tc['password']}".encode()).decode()
        headers["Authorization"] = f"Basic {cred}"

    session_id = getattr(transmission_request, "_session_id", None)
    if session_id:
        headers["X-Transmission-Session-Id"] = session_id

    req = Request(url, data=payload, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 409:
            transmission_request._session_id = e.headers.get("X-Transmission-Session-Id", "")
            return transmission_request(method, arguments)
        raise

class APIHandler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length) if length else b""

    def do_GET(self):
        path = urlparse(self.path).path
        dirs = CONFIG["directories"]

        if path == "/":
            self._json({"directories": dirs})

        elif path == "/tvshows":
            try:
                shows = sorted([
                    d for d in os.listdir(dirs["tvshows"])
                    if os.path.isdir(os.path.join(dirs["tvshows"], d))
                ])
                self._json({
                    "base": dirs["tvshows"],
                    "shows": shows,
                    "paths": [f"{dirs['tvshows']}/{s}" for s in shows]
                })
            except Exception as e:
                self._json({"error": str(e)}, 500)

        elif path == "/movies":
            self._json({"path": dirs["movies"]})

        elif path == "/downloads":
            self._json({"path": dirs["downloads"]})

        elif path == "/torrents":
            try:
                result = transmission_request("torrent-get", {
                    "fields": ["name", "hashString", "status", "percentDone", "downloadDir"]
                })
                torrents = result.get("arguments", {}).get("torrents", [])
                self._json({"torrents": torrents})
            except Exception as e:
                self._json({"error": str(e)}, 500)

        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/torrent/add":
            try:
                body = json.loads(self._read_body())
                args = {"paused": False}

                if body.get("magnet"):
                    args["filename"] = body["magnet"]
                elif body.get("metainfo"):
                    args["metainfo"] = body["metainfo"]
                else:
                    self._json({"error": "Provide 'magnet' or 'metainfo' (base64)"}, 400)
                    return

                if body.get("download_dir"):
                    args["download-dir"] = body["download_dir"]

                result = transmission_request("torrent-add", args)
                self._json(result.get("arguments", {}))
            except json.JSONDecodeError:
                self._json({"error": "Invalid JSON"}, 400)
            except Exception as e:
                self._json({"error": str(e)}, 500)
        else:
            self._json({"error": "Not found"}, 404)

    def log_message(self, *args):
        pass  # Suppress logging

if __name__ == "__main__":
    load_config()
    port = CONFIG.get("port", 8765)
    print(f"Torrent Directory API running on port {port}")
    print(f"Transmission: {CONFIG['transmission']['host']}:{CONFIG['transmission']['port']}")
    HTTPServer(("0.0.0.0", port), APIHandler).serve_forever()
