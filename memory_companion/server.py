"""A single-user loopback UI; no arbitrary file, shell, or network tools."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import urlsplit, parse_qs

from . import __version__
from .model import Model, messages_for, suggest, citation_check
from .store import Store, Conflict, text


STATIC = Path(__file__).parent / "static"


def make_server(store, model, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, *args):
            # Requests can refer to sensitive memories; no access/body logs.
            pass

        def trusted(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            host = self.headers.get("Host", "")
            if host not in allowed:
                raise PermissionError("Open the companion through its displayed loopback address.")
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + host:
                raise PermissionError("Cross-origin requests are not allowed.")
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                raise PermissionError("Cross-site requests are not allowed.")

        def send(self, code, body, content_type="application/json; charset=utf-8"):
            encoded = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(encoded)

        def error(self, error):
            if isinstance(error, PermissionError):
                self.send(403, {"error": str(error)})
            elif isinstance(error, Conflict):
                self.send(409, {"error": str(error)})
            elif isinstance(error, (ValueError, KeyError, TypeError, sqlite3.Error)):
                message = str(error) if isinstance(error, ValueError) else "Invalid request or conflicting data; check the fields."
                self.send(400, {"error": message})
            else:
                self.send(500, {"error": "Operation failed. Saved data remains subject to transaction checks."})

        def do_GET(self):
            try:
                self.trusted()
                parsed = urlsplit(self.path)
                if parsed.path == "/api/state":
                    project = parse_qs(parsed.query).get("project", [None])[0]
                    self.send(200, {"version": __version__, "token": token, "projects": store.projects(),
                                    "memories": store.list(project, True) if project else [],
                                    "proposals": store.proposals(), "model": model.info()})
                elif parsed.path == "/api/export":
                    if not secrets.compare_digest(self.headers.get("X-Companion-Token", ""), token):
                        raise PermissionError("Refresh the page before exporting.")
                    self.send(200, store.export())
                else:
                    name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}.get(parsed.path)
                    if name is None:
                        self.send(404, {"error": "Not found."})
                        return
                    mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[Path(name).suffix]
                    self.send(200, (STATIC / name).read_bytes(), mime + "; charset=utf-8")
            except Exception as error:
                self.error(error)

        def do_POST(self):
            try:
                self.trusted()
                if not secrets.compare_digest(self.headers.get("X-Companion-Token", ""), token):
                    raise PermissionError("Refresh the page before changing data.")
                if self.headers.get_content_type() != "application/json":
                    raise ValueError("Send JSON content.")
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 1_000_000 or self.headers.get("Transfer-Encoding"):
                    raise ValueError("Request body must be 1 byte–1 MB with a fixed length.")
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("JSON body must be an object.")
                route = urlsplit(self.path).path
                if route == "/api/project":
                    result = store.project(body["id"], body["name"], body.get("aliases", []))
                elif route == "/api/save":
                    result = store.put(**body)
                elif route == "/api/forget":
                    result = store.forget(body["id"], body["expected_revision"])
                elif route == "/api/select":
                    result = store.select(body["project"], body["question"])
                    if body.get("use_memory", True) is False:
                        result = {**result, "records": [], "characters": 0}
                elif route == "/api/chat":
                    question = text(body["question"], "Question", 12000)
                    selection = store.select(body["project"], question)
                    if body.get("use_memory", True) is False:
                        selection = {**selection, "records": [], "characters": 0}
                    messages = messages_for(question, selection)
                    answer = model.complete(messages)
                    result = {"answer": answer, "selection": selection, "request_messages": messages,
                              "citation_check": citation_check(answer, selection)}
                elif route == "/api/suggest":
                    result = suggest(model, store, body["project"], body["statement"])
                elif route == "/api/review":
                    result = store.review(body["id"], body["approve"])
                elif route == "/api/step":
                    result = store.step(body["id"], body["index"], body["state"], body.get("evidence", ""), body["expected_revision"])
                elif route == "/api/import":
                    result = store.import_data(body["document"], body.get("apply", False))
                elif route == "/api/backup":
                    name = "memory-" + secrets.token_hex(8) + ".sqlite"
                    result = store.backup(store.path.parent / "backups" / name)
                else:
                    self.send(404, {"error": "Not found."})
                    return
                self.send(200, result)
            except Exception as error:
                self.error(error)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(path, port=8765):
    store = Store(path)
    model = Model()
    server = make_server(store, model, port)
    print(f"Memory Companion {__version__}: http://127.0.0.1:{server.server_port}", flush=True)
    print("Single-user loopback app. Ctrl+C stops it. Memories remain in your data directory.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
