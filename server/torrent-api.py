#!/usr/bin/env python3
"""
Torrent Directory API for LibreELEC/Linux
Returns directory listings as JSON for the torrent adder GUI
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Configure your media paths here
MEDIA_BASE = "/media/lacie/Media"
DIRS = {
    "movies": f"{MEDIA_BASE}/Movies",
    "tvshows": f"{MEDIA_BASE}/TV Shows",
    "downloads": "/media/lacie/Downloads"
}

class APIHandler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/":
            self._json({"directories": DIRS})
        
        elif path == "/tvshows":
            try:
                shows = sorted([
                    d for d in os.listdir(DIRS["tvshows"])
                    if os.path.isdir(os.path.join(DIRS["tvshows"], d))
                ])
                self._json({
                    "base": DIRS["tvshows"],
                    "shows": shows,
                    "paths": [f"{DIRS['tvshows']}/{s}" for s in shows]
                })
            except Exception as e:
                self._json({"error": str(e)}, 500)
        
        elif path == "/movies":
            self._json({"path": DIRS["movies"]})
        
        elif path == "/downloads":
            self._json({"path": DIRS["downloads"]})
        
        else:
            self._json({"error": "Not found"}, 404)
    
    def log_message(self, *args):
        pass  # Suppress logging

if __name__ == "__main__":
    port = 8765
    print(f"Torrent Directory API running on port {port}")
    HTTPServer(("0.0.0.0", port), APIHandler).serve_forever()
