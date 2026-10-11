#!/usr/bin/env python3
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", "/tmp/doctor-bye-bye.db"))
FLAG_FILE = Path(os.environ.get("FLAG_FILE", "/tmp/flag"))
SQLITE_VALUE_LIMIT = 1024 * 1024
SQLITE_SQL_LIMIT = 2048
SQLITE_VM_BUDGET = 50_000


def validate_flag(flag):
    if not (flag.startswith("FortID{") and flag.endswith("}")):
        raise SystemExit("FLAG must use the FortID{...} format")
    if len(flag) > 128:
        raise SystemExit("FLAG must be at most 128 characters")
    if any(ord(character) < 32 or ord(character) > 126 for character in flag):
        raise SystemExit("FLAG must contain printable ASCII characters only")


def load_flag():
    try:
        return FLAG_FILE.read_text()
    finally:
        FLAG_FILE.unlink(missing_ok=True)


def initialize_database(flag):
    DATABASE.unlink(missing_ok=True)
    connection = sqlite3.connect(DATABASE)
    try:
        connection.executescript(
            """
            CREATE TABLE doctors (
                id INTEGER PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                specialty TEXT NOT NULL,
                room TEXT NOT NULL,
                listed INTEGER NOT NULL CHECK (listed IN (0, 1)),
                farewell_note TEXT
            );

            INSERT INTO doctors VALUES
                (10, 'ada-pulse', 'Dr. Ada Pulse', 'Cardiology', 'C-101', 1, NULL),
                (30, 'max-well', 'Dr. Max Well', 'Radiology', 'R-204', 1, NULL),
                (50, 'paige-turner', 'Dr. Paige Turner', 'Neurology', 'N-303', 1, NULL),
                (70, 'ella-ment', 'Dr. Ella Ment', 'Pathology', 'P-118', 1, NULL),
                (90, 'zoe-last', 'Dr. Zoe Last', 'Emergency medicine', 'E-001', 1, NULL);
            """,
        )
        connection.execute(
            "INSERT INTO doctors VALUES (?, ?, ?, ?, ?, ?, ?)",
            (404, "doctor-bye-bye", "Dr. Bye Bye", "Retired", "-", 0, flag),
        )
        connection.commit()
    finally:
        connection.close()


def select_on_call(order_expression):
    query = f"""
        SELECT name, specialty, room
        FROM doctors
        WHERE listed = 1
        ORDER BY {order_expression}
        LIMIT 1
    """
    connection = sqlite3.connect(DATABASE)
    try:
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, SQLITE_VALUE_LIMIT)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, SQLITE_SQL_LIMIT)
        operations_left = SQLITE_VM_BUDGET

        def enforce_budget():
            nonlocal operations_left
            operations_left -= 1_000
            return operations_left <= 0

        connection.set_progress_handler(enforce_budget, 1_000)
        row = connection.execute(query).fetchone()
    finally:
        connection.close()
    if row is None:
        raise LookupError("no on-call doctor")
    return {"name": row[0], "specialty": row[1], "room": row[2]}


class Handler(BaseHTTPRequestHandler):
    server_version = "StCodds/1.0"

    def send_body(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        request = urlsplit(self.path)
        if request.path == "/":
            body = (ROOT / "templates" / "index.html").read_bytes()
            self.send_body(200, "text/html; charset=utf-8", body)
            return

        if request.path == "/static/style.css":
            body = (ROOT / "static" / "style.css").read_bytes()
            self.send_body(200, "text/css; charset=utf-8", body)
            return

        if request.path == "/api/on-call":
            parameters = parse_qs(request.query, keep_blank_values=True)
            order_expression = parameters.get("sort", ["name"])[0]
            if not order_expression or len(order_expression) > 600:
                self.send_json(400, {"error": "Invalid schedule preference."})
                return
            try:
                doctor = select_on_call(order_expression)
            except (sqlite3.Error, LookupError):
                # Query errors deliberately do not expose database details.
                self.send_json(400, {"error": "The on-call board could not be updated."})
                return
            self.send_json(200, {"doctor": doctor})
            return

        self.send_body(404, "text/plain; charset=utf-8", b"Not found\n")

    def send_json(self, status, value):
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_body(status, "application/json; charset=utf-8", body)

    def log_message(self, message, *args):
        print(f"{self.address_string()} - {message % args}")


if __name__ == "__main__":
    flag = load_flag()
    validate_flag(flag)
    initialize_database(flag)
    port = int(os.environ.get("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
