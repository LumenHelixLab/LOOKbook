#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("LOOKBOOK_LAB_PORT", "8042"))
if __name__ == "__main__":
    os.chdir(ROOT)
    url = f"http://127.0.0.1:{PORT}/demo-lab/index.html"
    print(f"Serving lookBOOK Demo Lab at {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    ThreadingHTTPServer(("127.0.0.1", PORT), SimpleHTTPRequestHandler).serve_forever()
