#!/usr/bin/env python3
"""Zyklus23: lokal starten mit Python >=3.10, ohne Zusatzinstallation."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import unittest
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import config
import demo
from planetarium import planet_state

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_bytes(self, code, content, mime):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def json(self, value, code=200):
        self.send_bytes(code, json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        u = urlsplit(self.path)
        args = parse_qs(u.query, keep_blank_values=True)
        arg = lambda name, default: args.get(name, [str(default)])[0]
        static = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
                  "/style.css": ("style.css", "text/css; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8")}
        if u.path in static:
            name, mime = static[u.path]
            self.send_bytes(200, (ROOT / "web" / name).read_bytes(), mime)
            return
        if u.path == "/favicon.ico":
            self.send_bytes(204, b"", "image/x-icon")
            return
        try:
            if u.path == "/api/overview":
                data = demo.overview()
            elif u.path == "/api/state":
                data = demo.state(int(arg("q", 0)), int(arg("group", config.DEFAULT_GROUP)))
            elif u.path == "/api/date":
                data = demo.date_state(arg("utc", ""), int(arg("group", config.DEFAULT_GROUP)))
            elif u.path == "/api/jump":
                data = demo.jump(int(arg("q", 0)), arg("unit", "quantum"), int(arg("delta", 1)), int(arg("group", config.DEFAULT_GROUP)))
            elif u.path == "/api/series":
                data = demo.series(arg("mode", "year"), int(arg("start", 0)), int(arg("count", 529)))
            elif u.path == "/api/checks":
                data = demo.checks()
            elif u.path == "/api/planets":
                data = planet_state(int(arg("q", 0)))
            else:
                self.json({"error": "Seite oder Endpunkt nicht gefunden."}, 404)
                return
            self.json(data)
        except (ValueError, OverflowError, TypeError) as exc:
            self.json({"error": str(exc)}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as exc:
            self.json({"error": f"Interner Fehler: {type(exc).__name__}: {exc}"}, 500)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=(1, 2), default=2, help="1: lokale Tests; 2: Viewer")
    parser.add_argument("--no-browser", action="store_true", help="Browser nicht automatisch öffnen")
    parser.add_argument("--port", type=int, default=config.PORT, help="Lokaler Port; 0 wählt einen freien Port")
    options = parser.parse_args(argv)
    if options.phase == 1:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        source_paths = sorted([*ROOT.glob("*.py"), *(ROOT / "tests").glob("test_*.py")])
        report = {"version": config.VERSION, "executed_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
                  "code_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
                  "checks": demo.checks(), "unittest": {"run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped)},
                  "passed": result.wasSuccessful() and demo.checks()["passed"]}
        output = ROOT / "nachweise" / "lokaler_test.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Prüfbericht: {output}")
        return 0 if report["passed"] else 1
    if not 0 <= options.port <= 65535:
        parser.error("Port muss zwischen0 und65535 liegen.")
    server = ThreadingHTTPServer((config.HOST, options.port), Handler)
    server.daemon_threads = True
    url = f"http://{config.HOST}:{server.server_port}/"
    print(f"Zyklus23 Demonstrator {config.VERSION}", flush=True)
    print(f"Viewer: {url}", flush=True)
    print("Zum Beenden Strg+C drücken. Laufzeit ohne Internet und ohne pip-Pakete.", flush=True)
    if not options.no_browser:
        def open_browser():
            try:
                webbrowser.open(url)
            except webbrowser.Error:
                pass
        threading.Thread(target=open_browser, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nViewer beendet.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

