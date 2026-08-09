#!/usr/bin/env python3
import base64
import html
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("CLINIC_DB", DATA_DIR / "clinic.sqlite"))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
SESSION_COOKIE = "cardio_vita_session"
SESSION_DAYS = 7
SECRET = os.environ.get("APP_SECRET", "change-this-secret-before-cloud-hosting")
DEFAULT_SECRET = "change-this-secret-before-cloud-hosting"
DEFAULT_ADMIN_PASSWORD = "ChangeMe2026!"
PRODUCTION = os.environ.get("APP_ENV") == "production"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "true" or PRODUCTION

BRANCHES = {"Տերյան", "Նարեկացի"}
BRANCH_PREFIXES = {"Տերյան": "T", "Նարեկացի": "N"}
STATUSES = {"Նշանակված", "Եկել է", "Չեղարկված", "Չի եկել"}
ID_TABLES = {"users", "patients", "appointments", "holters", "service_orders", "doctors", "audit_log", "doctor_notes"}

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if psycopg:
    DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sql_params(sql):
    return sql.replace("?", "%s") if DATABASE_URL else sql


def insert_table_name(sql):
    match = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", sql, re.IGNORECASE)
    return match.group(1) if match else None


class DbCursor:
    def __init__(self, cursor, lastrowid=None):
        self.cursor = cursor
        self.lastrowid = lastrowid

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


class PostgresConnection:
    def __init__(self):
        if not psycopg:
            raise RuntimeError("Install requirements.txt to use DATABASE_URL/Postgres.")
        self.conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def execute(self, sql, params=()):
        table = insert_table_name(sql)
        needs_id = table in ID_TABLES and "RETURNING" not in sql.upper()
        if needs_id:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        cur = self.conn.execute(sql_params(sql), params or ())
        lastrowid = None
        if needs_id:
            row = cur.fetchone()
            lastrowid = row["id"] if row else None
        return DbCursor(cur, lastrowid)

    def executemany(self, sql, params_seq):
        for params in params_seq:
            self.execute(sql, params)

    def executescript(self, script):
        for statement in [part.strip() for part in script.split(";") if part.strip()]:
            self.execute(statement)


def connect():
    if DATABASE_URL:
        return PostgresConnection()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 160_000)
    return base64.b64encode(salt + digest).decode("ascii")


def verify_password(password, stored):
    raw = base64.b64decode(stored.encode("ascii"))
    salt, expected = raw[:16], raw[16:]
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 160_000)
    return hmac.compare_digest(actual, expected)


def parse_date(value):
    if not value:
        raise ValueError("Ամսաթիվը պարտադիր է։")
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time(value):
    if not value:
        raise ValueError("Ժամը պարտադիր է։")
    return datetime.strptime(value, "%H:%M").time()


def branch_is_open(branch, day, at_time):
    weekday = day.weekday()
    if branch == "Տերյան":
        if weekday >= 5:
            return time(10, 0) <= at_time < time(18, 0)
        return time(8, 0) <= at_time < time(20, 0)
    if branch == "Նարեկացի":
        if weekday <= 4:
            return time(8, 0) <= at_time < time(20, 0)
        if weekday == 5:
            return time(9, 0) <= at_time < time(18, 0)
        return False
    return False


def row_dict(row):
    return dict(row) if row else None


def clean_phone(value):
    value = (value or "").strip()
    compact = value.replace(" ", "")
    if compact and not compact.lstrip("+").isdigit():
        raise ValueError("Հեռախոսը պետք է պարունակի միայն թվեր։")
    return value


def next_anketa_number(conn, branch):
    prefix = BRANCH_PREFIXES.get(branch, "CV")
    rows = conn.execute("SELECT anketa_number FROM patients WHERE branch = ?", (branch,)).fetchall()
    highest = 0
    for row in rows:
        value = str(row["anketa_number"] or "").strip()
        match = re.search(r"(\d+)$", value)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}-{highest + 1:06d}"


def ensure_column(conn, table, column, definition):
    if DATABASE_URL:
        rows = conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table,),
        ).fetchall()
    else:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    columns = {r["name"] for r in rows}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def ensure_users_support_doctors(conn):
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone()
    if not row or "CHECK(role IN ('admin','staff'))" not in row["sql"]:
        return
    conn.executescript(
        """
        ALTER TABLE users RENAME TO users_old;
        CREATE TABLE users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL,
          branch TEXT,
          doctor_name TEXT,
          active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL
        );
        INSERT INTO users (id, username, password_hash, role, branch, active, created_at)
        SELECT id, username, password_hash, role, branch, active, created_at FROM users_old;
        DROP TABLE users_old;
        """
    )


def ensure_sessions_reference_users(conn):
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'sessions'").fetchone()
    if not row or "users_old" not in row["sql"]:
        return
    conn.executescript(
        """
        ALTER TABLE sessions RENAME TO sessions_old;
        CREATE TABLE sessions (
          token TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          expires_at TEXT NOT NULL
        );
        INSERT INTO sessions (token, user_id, expires_at)
        SELECT token, user_id, expires_at FROM sessions_old;
        DROP TABLE sessions_old;
        """
    )


def ensure_doctor_notes_reference_users(conn):
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'doctor_notes'").fetchone()
    if not row or "users_old" not in row["sql"]:
        return
    conn.executescript(
        """
        ALTER TABLE doctor_notes RENAME TO doctor_notes_old;
        CREATE TABLE doctor_notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          anketa_number TEXT NOT NULL,
          doctor TEXT NOT NULL,
          diagnosis TEXT,
          prescription TEXT,
          notes TEXT,
          created_by INTEGER REFERENCES users(id),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        INSERT INTO doctor_notes
        (id, anketa_number, doctor, diagnosis, prescription, notes, created_by, created_at, updated_at)
        SELECT id, anketa_number, doctor, diagnosis, prescription, notes, created_by, created_at, updated_at
        FROM doctor_notes_old;
        DROP TABLE doctor_notes_old;
        """
    )


PRINT_STYLE = """
      body { font-family: Arial, "Noto Sans Armenian", sans-serif; color: #17343d; margin: 0; background: #eef4f6; }
      .page { width: 210mm; min-height: 297mm; margin: 0 auto; background: #fff; padding: 18mm; box-sizing: border-box; }
      .head { display: flex; justify-content: space-between; gap: 24px; border-bottom: 3px solid #176b87; padding-bottom: 14px; }
      .brand { display: flex; align-items: center; gap: 14px; }
      .brand img { width: 78px; height: auto; object-fit: contain; }
      h1 { margin: 0; color: #176b87; font-size: 28px; }
      h2 { margin: 22px 0 10px; color: #17343d; font-size: 18px; }
      .muted { color: #607780; }
      .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 9px 18px; margin-top: 16px; }
      .field { border: 1px solid #d8e4e8; border-radius: 8px; padding: 10px; }
      .field span { display: block; color: #607780; font-size: 12px; margin-bottom: 4px; }
      .field strong { white-space: pre-wrap; }
      .text { border: 1px solid #d8e4e8; border-radius: 8px; padding: 12px; min-height: 72px; white-space: pre-wrap; line-height: 1.5; }
      .signature { display: grid; grid-template-columns: 1fr 70mm; gap: 20px; margin-top: 32px; align-items: end; }
      .line { border-top: 1px solid #17343d; padding-top: 7px; text-align: center; }
      .actions { position: sticky; top: 0; padding: 10px; background: #17343d; text-align: center; }
      button { background: #176b87; color: #fff; border: 0; border-radius: 6px; padding: 10px 16px; font: inherit; cursor: pointer; }
      @media print { body { background: #fff; } .actions { display: none; } .page { width: auto; min-height: auto; margin: 0; padding: 0; } }
"""


def print_header(title, subtitle, created, record_id):
    return f"""
      <header class="head">
        <div class="brand">
          <img src="/logo.png" alt="Cardio Vita logo">
          <div>
            <h1>Cardio Vita</h1>
            <div class="muted">{subtitle}</div>
          </div>
        </div>
        <div>
          <strong>Ամսաթիվ՝ {created}</strong><br>
          <span class="muted">{title} #{record_id}</span>
        </div>
      </header>
"""


DOCTOR_DOCUMENT_TYPES = {
    "Ախտորոշում": "Ախտորոշում",
    "Էխոսրտագրության պատասխան": "Էխոսրտագրության պատասխան",
    "Հոլտերի եզրակացություն": "Հոլտերի եզրակացություն",
    "Ֆիզիկական ծանրաբեռնվածության թեստի պատասխան": "Ֆիզիկական ծանրաբեռնվածության թեստի պատասխան",
}


def init_db():
    if PRODUCTION and SECRET == DEFAULT_SECRET:
        raise RuntimeError("Set APP_SECRET before production hosting.")
    with connect() as conn:
        if DATABASE_URL:
            conn.executescript((BASE_DIR / "scripts" / "postgres_schema.sql").read_text(encoding="utf-8"))
            if not conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                password = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
                if PRODUCTION and password == DEFAULT_ADMIN_PASSWORD:
                    raise RuntimeError("Set ADMIN_PASSWORD before production hosting.")
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, branch, created_at) VALUES (?,?,?,?,?)",
                    ("admin", hash_password(password), "admin", None, now_iso()),
                )
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL,
              branch TEXT,
              doctor_name TEXT,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS patients (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              anketa_number TEXT NOT NULL UNIQUE,
              visit_date TEXT NOT NULL,
              branch TEXT NOT NULL,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              father_name TEXT,
              birth_date TEXT,
              passport TEXT,
              phone TEXT,
              email TEXT,
              status TEXT,
              payment TEXT,
              notes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS appointments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              appointment_date TEXT NOT NULL,
              appointment_time TEXT NOT NULL,
              branch TEXT NOT NULL,
              doctor TEXT NOT NULL,
              anketa_number TEXT,
              patient_name TEXT,
              passport TEXT,
              phone TEXT,
              status TEXT NOT NULL,
              notes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE (appointment_date, appointment_time, doctor)
            );
            CREATE TABLE IF NOT EXISTS holters (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              anketa_number TEXT NOT NULL,
              patient_name TEXT,
              phone TEXT,
              branch TEXT,
              provided_date TEXT NOT NULL,
              provided_time TEXT NOT NULL,
              duration_hours INTEGER NOT NULL CHECK(duration_hours IN (24,48,72)),
              return_at TEXT NOT NULL,
              provided_status TEXT,
              return_status TEXT,
              actual_return TEXT,
              notes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS service_orders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              anketa_number TEXT NOT NULL,
              kind TEXT NOT NULL CHECK(kind IN ('general','lab')),
              branch TEXT,
              doctor TEXT,
              category TEXT,
              service_name TEXT NOT NULL,
              price INTEGER NOT NULL DEFAULT 0,
              status TEXT,
              notes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS doctors (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              specialty TEXT,
              active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS audit_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              action TEXT NOT NULL,
              entity TEXT NOT NULL,
              entity_id TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS doctor_notes (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              anketa_number TEXT NOT NULL,
          doctor TEXT NOT NULL,
          note_type TEXT NOT NULL DEFAULT 'Ախտորոշում',
          complaints TEXT,
          diagnosis TEXT,
          prescription TEXT,
              notes TEXT,
              created_by INTEGER REFERENCES users(id),
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        ensure_users_support_doctors(conn)
        ensure_sessions_reference_users(conn)
        ensure_doctor_notes_reference_users(conn)
        ensure_column(conn, "users", "doctor_name", "TEXT")
        ensure_column(conn, "doctors", "specialty", "TEXT")
        ensure_column(conn, "doctor_notes", "note_type", "TEXT NOT NULL DEFAULT 'Ախտորոշում'")
        ensure_column(conn, "doctor_notes", "complaints", "TEXT")
        ensure_column(conn, "holters", "branch", "TEXT")
        ensure_column(conn, "holters", "patient_name", "TEXT")
        ensure_column(conn, "holters", "phone", "TEXT")
        ensure_column(conn, "patients", "passport", "TEXT")
        ensure_column(conn, "appointments", "passport", "TEXT")
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_patients_branch_visit ON patients(branch, visit_date);
            CREATE INDEX IF NOT EXISTS idx_appointments_branch_date ON appointments(branch, appointment_date);
            CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date_time ON appointments(doctor, appointment_date, appointment_time);
            CREATE INDEX IF NOT EXISTS idx_services_branch_kind ON service_orders(branch, kind);
            CREATE INDEX IF NOT EXISTS idx_holters_branch_return_at ON holters(branch, return_at);
            CREATE INDEX IF NOT EXISTS idx_holters_return_at ON holters(return_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
            CREATE INDEX IF NOT EXISTS idx_doctor_notes_anketa ON doctor_notes(anketa_number);
            CREATE INDEX IF NOT EXISTS idx_doctor_notes_doctor_created ON doctor_notes(doctor, created_at);
            """
        )
        doctors = [
            ("Ազնիվ Գևորգյան", "Սրտաբան"),
            ("Սիրանուշ Գրիգորյան", "Սրտաբան"),
            ("Բակուր Վարդանյան", "Բժիշկ"),
            ("Արմեն Շահբազյան", "Բժիշկ"),
            ("Ալլա Աբովյան", "Սրտաբան"),
            ("Սոֆյա Խաչատրյան", "Բժիշկ"),
            ("Մելինա Խաչատրյան", "Բժիշկ"),
            ("Լյուբա Արզումանյան", "Բժիշկ"),
            ("Արմինե Հովհաննիսյան", "Բժիշկ"),
            ("Մակարյան Գայանե", "Ռևմատոլոգ"),
            ("Ասլիկյան Աննա", "Բժիշկ-լաբորանտ"),
        ]
        conn.executemany("INSERT OR IGNORE INTO doctors (name, specialty) VALUES (?,?)", doctors)
        conn.executemany("UPDATE doctors SET specialty = ? WHERE name = ? AND (specialty IS NULL OR specialty = '')", [(specialty, name) for name, specialty in doctors])
        if not conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            password = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
            if PRODUCTION and password == DEFAULT_ADMIN_PASSWORD:
                raise RuntimeError("Set ADMIN_PASSWORD before production hosting.")
            conn.execute(
                "INSERT INTO users (username, password_hash, role, branch, created_at) VALUES (?,?,?,?,?)",
                ("admin", hash_password(password), "admin", None, now_iso()),
            )


def sign_session(token):
    sig = hmac.new(SECRET.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{token}.{sig}"


def unsign_session(value):
    try:
        token, sig = value.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(SECRET.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()
    return token if hmac.compare_digest(sig, expected) else None


class ClinicHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw or "{}")
        except json.JSONDecodeError:
            raise ValueError("Սխալ JSON տվյալ։")

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, markup, status=200):
        body = markup.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def error(self, message, status=400):
        self.send_json({"error": message}, status)

    def origin_allowed(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        return origin in {f"http://{host}", f"https://{host}"}

    def current_user(self):
        jar = cookies.SimpleCookie(self.headers.get("Cookie"))
        morsel = jar.get(SESSION_COOKIE)
        if not morsel:
            return None
        token = unsign_session(morsel.value)
        if not token:
            return None
        with connect() as conn:
            row = conn.execute(
                """
                SELECT u.* FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ? AND s.expires_at > ? AND u.active = 1
                """,
                (token, now_iso()),
            ).fetchone()
        return row_dict(row)

    def require_user(self):
        user = self.current_user()
        if not user:
            self.error("Login required.", 401)
            return None
        return user

    def audit(self, user, action, entity, entity_id=None):
        with connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id, action, entity, entity_id, created_at) VALUES (?,?,?,?,?)",
                (user["id"] if user else None, action, entity, str(entity_id or ""), now_iso()),
            )

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/healthz":
            self.health()
            return
        if parsed.path == "/api/me":
            user = self.current_user()
            self.send_json({"user": public_user(user)} if user else {"user": None})
            return
        user = self.require_user() if parsed.path.startswith("/api/") or parsed.path.startswith("/print/") else None
        if parsed.path == "/api/doctors" and user:
            self.list_doctors()
            return
        if parsed.path == "/api/users" and user:
            self.list_users(user)
            return
        if parsed.path == "/api/patients" and user:
            self.list_table("patients", user)
            return
        if parsed.path == "/api/patient" and user:
            self.find_patient(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/next-anketa" and user:
            self.next_anketa(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/patient-search" and user:
            self.search_patients(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/patient-lookup" and user:
            self.patient_lookup(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/patient-report" and user:
            self.patient_report(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/patient-profile" and user:
            self.patient_profile(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/appointments" and user:
            self.list_table("appointments", user)
            return
        if parsed.path == "/api/holters" and user:
            self.list_table("holters", user)
            return
        if parsed.path == "/api/service-orders" and user:
            self.list_table("service_orders", user)
            return
        if parsed.path == "/api/doctor-patients" and user:
            self.doctor_patients(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/doctor-notes" and user:
            self.list_doctor_notes(user, parse_qs(parsed.query))
            return
        if parsed.path == "/print/doctor-note" and user:
            self.print_doctor_note(user, parse_qs(parsed.query))
            return
        if parsed.path == "/print/holter" and user:
            self.print_holter(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/calendar" and user:
            self.calendar(user, parse_qs(parsed.query))
            return
        if parsed.path == "/api/summary" and user:
            self.summary(user)
            return
        if parsed.path == "/api/dashboard" and user:
            self.dashboard(user)
            return
        if parsed.path == "/api/export" and user:
            self.export_json(user)
            return
        return super().do_GET()

    def do_POST(self):
        if not self.origin_allowed():
            self.error("Origin not allowed.", 403)
            return
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/api/login":
                self.login()
                return
            if parsed.path == "/api/logout":
                self.logout()
                return
            user = self.require_user()
            if not user:
                return
            if parsed.path == "/api/patients":
                self.create_patient(user)
                return
            if parsed.path == "/api/appointments":
                self.create_appointment(user)
                return
            if parsed.path == "/api/holters":
                self.create_holter(user)
                return
            if parsed.path == "/api/service-orders":
                self.create_service_order(user)
                return
            if parsed.path == "/api/doctor-notes":
                self.create_doctor_note(user)
                return
            if parsed.path == "/api/users":
                self.create_user(user)
                return
            self.error("Unknown endpoint.", 404)
        except ValueError as exc:
            self.error(str(exc))

    def do_DELETE(self):
        if not self.origin_allowed():
            self.error("Origin not allowed.", 403)
            return
        parsed = urlparse(self.path)
        user = self.require_user()
        if not user:
            return
        parts = parsed.path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api":
            table_map = {"patients": "patients", "appointments": "appointments", "holters": "holters", "service-orders": "service_orders", "users": "users"}
            table = table_map.get(parts[1])
            if table:
                entity_id = unquote(parts[2])
                if table == "users" and user["role"] != "admin":
                    self.error("Միայն ադմինը կարող է ջնջել օգտատերեր։", 403)
                    return
                if table == "users" and str(user["id"]) == str(entity_id):
                    self.error("Չեք կարող ջնջել ձեր ընթացիկ օգտատերը։", 400)
                    return
                with connect() as conn:
                    if not self.can_delete_row(conn, user, table, entity_id):
                        self.error("No access to this record.", 403)
                        return
                    conn.execute(f"DELETE FROM {table} WHERE id = ?", (entity_id,))
                self.audit(user, "delete", table, entity_id)
                self.send_json({"ok": True})
                return
        self.error("Unknown endpoint.", 404)

    def login(self):
        try:
            data = self.json_body()
        except ValueError as exc:
            self.error(str(exc))
            return
        with connect() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ? AND active = 1", (data.get("username", ""),)).fetchone()
            if not user or not verify_password(data.get("password", ""), user["password_hash"]):
                self.error("Wrong username or password.", 401)
                return
            token = secrets.token_urlsafe(32)
            expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
            conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)", (token, user["id"], expires))
        cookie = cookies.SimpleCookie()
        cookie[SESSION_COOKIE] = sign_session(token)
        cookie[SESSION_COOKIE]["path"] = "/"
        cookie[SESSION_COOKIE]["httponly"] = True
        cookie[SESSION_COOKIE]["samesite"] = "Lax"
        if COOKIE_SECURE:
            cookie[SESSION_COOKIE]["secure"] = True
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", cookie.output(header="").strip())
        self.end_headers()
        self.wfile.write(json.dumps({"user": public_user(row_dict(user))}, ensure_ascii=False).encode("utf-8"))

    def logout(self):
        jar = cookies.SimpleCookie(self.headers.get("Cookie"))
        morsel = jar.get(SESSION_COOKIE)
        token = unsign_session(morsel.value) if morsel else None
        if token:
            with connect() as conn:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        cookie = cookies.SimpleCookie()
        cookie[SESSION_COOKIE] = ""
        cookie[SESSION_COOKIE]["path"] = "/"
        cookie[SESSION_COOKIE]["max-age"] = "0"
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Set-Cookie", cookie.output(header="").strip())
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8"))

    def scoped_branch(self, user, requested):
        if user["role"] == "admin":
            return requested if requested in BRANCHES else None
        return user["branch"]

    def health(self):
        with connect() as conn:
            conn.execute("SELECT 1").fetchone()
        self.send_json({"ok": True, "time": now_iso()})

    def can_delete_row(self, conn, user, table, entity_id):
        if user["role"] == "admin":
            return True
        columns = table_columns(table)
        if "branch" not in columns:
            return False
        row = conn.execute(f"SELECT branch FROM {table} WHERE id = ?", (entity_id,)).fetchone()
        return bool(row and row["branch"] == user["branch"])

    def list_table(self, table, user):
        query = parse_qs(urlparse(self.path).query)
        branch = self.scoped_branch(user, query.get("branch", [""])[0])
        where, params = [], []
        if branch and "branch" in table_columns(table):
            where.append("branch = ?")
            params.append(branch)
        sql = f"SELECT * FROM {table}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT 500"
        with connect() as conn:
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        self.send_json(rows)

    def list_doctors(self):
        with connect() as conn:
            rows = [dict(r) for r in conn.execute("SELECT id, name, specialty FROM doctors WHERE active = 1 ORDER BY name").fetchall()]
        self.send_json(rows)

    def find_patient(self, user, query):
        anketa_number = query.get("anketa_number", [""])[0].strip()
        if not anketa_number:
            self.error("Լրացրեք անկետա համարը։")
            return
        where = "anketa_number = ?"
        params = [anketa_number]
        if user["role"] != "admin":
            where += " AND branch = ?"
            params.append(user["branch"])
        with connect() as conn:
            row = conn.execute(
                f"""
                SELECT anketa_number, visit_date, branch, first_name, last_name, father_name,
                       birth_date, passport, phone, email, status
                FROM patients
                WHERE {where}
                """,
                params,
            ).fetchone()
        if not row:
            self.error("Այդ անկետա համարով պացիենտ չի գտնվել։", 404)
            return
        self.send_json(dict(row))

    def next_anketa(self, user, query):
        requested_branch = query.get("branch", [""])[0].strip()
        branch = self.scoped_branch(user, requested_branch)
        if branch not in BRANCHES:
            self.error("Ընտրեք մասնաճյուղ։")
            return
        with connect() as conn:
            self.send_json({"anketa_number": next_anketa_number(conn, branch), "branch": branch})

    def search_patients(self, user, query):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է տեսնել ընդհանուր պացիենտների պատմությունը։", 403)
            return
        term = query.get("q", [""])[0].strip()
        if not term:
            self.send_json([])
            return
        like = f"%{term}%"
        with connect() as conn:
            rows = [dict(r) for r in conn.execute(
                """
                SELECT anketa_number, visit_date, branch, first_name, last_name, father_name,
                       birth_date, passport, phone, email, status, payment
                FROM patients
                WHERE anketa_number LIKE ?
                   OR first_name LIKE ?
                   OR last_name LIKE ?
                   OR father_name LIKE ?
                   OR passport LIKE ?
                   OR phone LIKE ?
                   OR email LIKE ?
                ORDER BY visit_date DESC, id DESC
                LIMIT 50
                """,
                (like, like, like, like, like, like, like),
            ).fetchall()]
        self.send_json(rows)

    def patient_lookup(self, user, query):
        term = query.get("q", [""])[0].strip()
        requested_branch = query.get("branch", [""])[0].strip()
        branch = self.scoped_branch(user, requested_branch)
        if not term:
            self.send_json([])
            return
        like = f"%{term}%"
        where = """
            (anketa_number LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR
             father_name LIKE ? OR passport LIKE ? OR phone LIKE ? OR email LIKE ?)
        """
        params = [like, like, like, like, like, like, like]
        if branch:
            where += " AND branch = ?"
            params.append(branch)
        with connect() as conn:
            rows = [dict(r) for r in conn.execute(
                f"""
                SELECT anketa_number, visit_date, branch, first_name, last_name, father_name,
                       birth_date, passport, phone, email, status, payment
                FROM patients
                WHERE {where}
                ORDER BY visit_date DESC, id DESC
                LIMIT 12
                """,
                params,
            ).fetchall()]
        self.send_json(rows)

    def patient_report(self, user, query):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է տեսնել ընդհանուր պացիենտների պատմությունը։", 403)
            return
        term = query.get("q", [""])[0].strip()
        date_type = query.get("date_type", ["visit"])[0]
        patient_type = query.get("patient_type", ["all"])[0]
        date_from = query.get("from", [""])[0].strip()
        date_to = query.get("to", [""])[0].strip()
        if date_type not in {"visit", "registration", "service"}:
            self.error("Սխալ ամսաթվի տեսակ։")
            return
        if patient_type not in {"all", "new", "existing"}:
            self.error("Սխալ պացիենտի տեսակ։")
            return
        for value in [date_from, date_to]:
            if value:
                parse_date(value)
        where = []
        params = []
        if term:
            like = f"%{term}%"
            where.append(
                """(
                p.anketa_number LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR
                p.father_name LIKE ? OR p.passport LIKE ? OR p.phone LIKE ? OR p.email LIKE ?
                )"""
            )
            params.extend([like, like, like, like, like, like, like])
        if date_type == "visit":
            field = "p.visit_date"
        elif date_type == "registration":
            field = "substr(p.created_at, 1, 10)"
        else:
            field = "s.last_service_date"
            where.append("s.service_count > 0")
        if date_from:
            where.append(f"{field} >= ?")
            params.append(date_from)
        if date_to:
            where.append(f"{field} <= ?")
            params.append(date_to)
        if patient_type == "new":
            if date_from:
                where.append("substr(p.created_at, 1, 10) >= ?")
                params.append(date_from)
            if date_to:
                where.append("substr(p.created_at, 1, 10) <= ?")
                params.append(date_to)
        elif patient_type == "existing":
            where.append("s.service_count > 0")
            if date_from:
                where.append("substr(p.created_at, 1, 10) < ?")
                params.append(date_from)
        sql_where = "WHERE " + " AND ".join(where) if where else ""
        with connect() as conn:
            rows = [dict(r) for r in conn.execute(
                f"""
                SELECT p.anketa_number, p.visit_date, substr(p.created_at, 1, 10) registration_date,
                       p.branch, p.first_name, p.last_name, p.father_name, p.birth_date,
                       p.passport, p.phone, p.email, p.status, p.payment,
                       COALESCE(s.service_count, 0) service_count,
                       COALESCE(s.service_total, 0) service_total,
                       s.last_service_date
                FROM patients p
                LEFT JOIN (
                    SELECT anketa_number, COUNT(*) service_count, SUM(price) service_total,
                           MAX(substr(created_at, 1, 10)) last_service_date
                    FROM service_orders
                    GROUP BY anketa_number
                ) s ON s.anketa_number = p.anketa_number
                {sql_where}
                ORDER BY {field} DESC, p.id DESC
                LIMIT 500
                """,
                params,
            ).fetchall()]
        self.send_json(rows)

    def patient_profile(self, user, query):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է տեսնել ընդհանուր պացիենտների պատմությունը։", 403)
            return
        anketa_number = query.get("anketa_number", [""])[0].strip()
        if not anketa_number:
            self.error("Լրացրեք անկետա համարը։")
            return
        with connect() as conn:
            patient = conn.execute(
                """
                SELECT anketa_number, visit_date, branch, first_name, last_name, father_name,
                       birth_date, passport, phone, email, status, payment, notes, created_at, updated_at
                FROM patients
                WHERE anketa_number = ?
                """,
                (anketa_number,),
            ).fetchone()
            if not patient:
                self.error("Պացիենտը չգտնվեց։", 404)
                return
            appointments = [dict(r) for r in conn.execute(
                """
                SELECT appointment_date, appointment_time, branch, doctor, patient_name, passport, phone, status, notes, created_at
                FROM appointments
                WHERE anketa_number = ?
                ORDER BY appointment_date DESC, appointment_time DESC
                LIMIT 200
                """,
                (anketa_number,),
            ).fetchall()]
            services = [dict(r) for r in conn.execute(
                """
                SELECT kind, branch, doctor, category, service_name, price, status, notes, created_at
                FROM service_orders
                WHERE anketa_number = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 300
                """,
                (anketa_number,),
            ).fetchall()]
            holters = [dict(r) for r in conn.execute(
                """
                SELECT id, branch, patient_name, phone, provided_date, provided_time, duration_hours, return_at,
                       provided_status, return_status, actual_return, notes, created_at
                FROM holters
                WHERE anketa_number = ?
                ORDER BY provided_date DESC, provided_time DESC
                LIMIT 200
                """,
                (anketa_number,),
            ).fetchall()]
            doctor_notes = [dict(r) for r in conn.execute(
                """
                SELECT doctor, note_type, complaints, diagnosis, prescription, notes, created_at
                FROM doctor_notes
                WHERE anketa_number = ?
                ORDER BY created_at DESC
                LIMIT 200
                """,
                (anketa_number,),
            ).fetchall()]
        self.send_json({
            "patient": dict(patient),
            "appointments": appointments,
            "services": services,
            "holters": holters,
            "doctor_notes": doctor_notes,
        })

    def list_users(self, user):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է տեսնել օգտատերերը։", 403)
            return
        with connect() as conn:
            rows = [
                public_user(dict(r))
                for r in conn.execute("SELECT id, username, role, branch, doctor_name FROM users ORDER BY username").fetchall()
            ]
        self.send_json(rows)

    def create_user(self, user):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է ստեղծել օգտատեր։", 403)
            return
        data = self.json_body()
        username = data.get("username", "").strip()
        password = data.get("password", "")
        role = data.get("role", "staff")
        branch = data.get("branch") or None
        doctor_name = data.get("doctor_name", "").strip() or None
        if not username or len(password) < 8:
            self.error("Օգտանունը պարտադիր է, գաղտնաբառը՝ առնվազն 8 նիշ։")
            return
        if role not in {"admin", "staff", "doctor"}:
            self.error("Սխալ դեր։")
            return
        if role == "staff" and branch not in BRANCHES:
            self.error("Աշխատակցի համար ընտրեք մասնաճյուղ։")
            return
        if role == "doctor" and not doctor_name:
            self.error("Բժշկի օգտատիրոջ համար ընտրեք բժիշկ։")
            return
        if role == "admin":
            branch = None
            doctor_name = None
        if role == "doctor":
            branch = None
        if role != "doctor":
            doctor_name = None
        try:
            with connect() as conn:
                cur = conn.execute(
                    "INSERT INTO users (username, password_hash, role, branch, doctor_name, created_at) VALUES (?,?,?,?,?,?)",
                    (username, hash_password(password), role, branch, doctor_name, now_iso()),
                )
            self.audit(user, "create", "users", cur.lastrowid)
            self.send_json({"ok": True, "id": cur.lastrowid}, 201)
        except DB_INTEGRITY_ERRORS:
            self.error("Այդ օգտանունը արդեն կա։", 409)

    def doctor_name_for_user(self, user):
        if user["role"] == "doctor":
            return user.get("doctor_name") or user.get("username")
        return None

    def doctor_patients(self, user, query):
        doctor = self.doctor_name_for_user(user)
        if not doctor:
            self.error("Միայն բժիշկը կարող է բացել այս էջը։", 403)
            return
        term = query.get("q", [""])[0].strip()
        params = [doctor, doctor]
        where = ""
        if term:
            like = f"%{term}%"
            where = """
              AND (
                p.anketa_number LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR
                p.father_name LIKE ? OR p.phone LIKE ? OR p.passport LIKE ?
              )
            """
            params.extend([like, like, like, like, like, like])
        with connect() as conn:
            rows = [dict(r) for r in conn.execute(
                f"""
                SELECT p.anketa_number, p.visit_date, p.branch, p.first_name, p.last_name, p.father_name,
                       p.birth_date, p.passport, p.phone, p.email,
                       MAX(a.appointment_date) last_appointment_date,
                       MAX(substr(s.created_at, 1, 10)) last_service_date
                FROM patients p
                LEFT JOIN appointments a ON a.anketa_number = p.anketa_number AND a.doctor = ?
                LEFT JOIN service_orders s ON s.anketa_number = p.anketa_number AND s.doctor = ?
                WHERE (a.id IS NOT NULL OR s.id IS NOT NULL) {where}
                GROUP BY p.anketa_number
                ORDER BY COALESCE(last_appointment_date, last_service_date, p.visit_date) DESC
                LIMIT 100
                """,
                params,
            ).fetchall()]
        self.send_json(rows)

    def list_doctor_notes(self, user, query):
        doctor = self.doctor_name_for_user(user)
        if not doctor:
            self.error("Միայն բժիշկը կարող է բացել այս էջը։", 403)
            return
        anketa_number = query.get("anketa_number", [""])[0].strip()
        if not anketa_number:
            self.error("Ընտրեք պացիենտ։")
            return
        with connect() as conn:
            patient = conn.execute(
                """
                SELECT anketa_number, visit_date, branch, first_name, last_name, father_name,
                       birth_date, passport, phone, email
                FROM patients WHERE anketa_number = ?
                """,
                (anketa_number,),
            ).fetchone()
            notes = [dict(r) for r in conn.execute(
                """
                SELECT id, anketa_number, doctor, note_type, complaints, diagnosis, prescription, notes, created_at, updated_at
                FROM doctor_notes
                WHERE anketa_number = ? AND doctor = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (anketa_number, doctor),
            ).fetchall()]
            holters = [dict(r) for r in conn.execute(
                """
                SELECT id, anketa_number, branch, patient_name, phone, provided_date, provided_time,
                       duration_hours, return_at, provided_status, return_status, actual_return,
                       notes, created_at
                FROM holters
                WHERE anketa_number = ?
                ORDER BY provided_date DESC, provided_time DESC, id DESC
                LIMIT 100
                """,
                (anketa_number,),
            ).fetchall()]
        if not patient:
            self.error("Պացիենտը չգտնվեց։", 404)
            return
        self.send_json({"patient": dict(patient), "notes": notes, "holters": holters})

    def create_doctor_note(self, user):
        doctor = self.doctor_name_for_user(user)
        if not doctor:
            self.error("Միայն բժիշկը կարող է գրել ախտորոշում և նշանակում։", 403)
            return
        data = self.json_body()
        anketa_number = data.get("anketa_number", "").strip()
        note_type = data.get("note_type", "Ախտորոշում").strip() or "Ախտորոշում"
        complaints = data.get("complaints", "").strip()
        diagnosis = data.get("diagnosis", "").strip()
        prescription = data.get("prescription", "").strip()
        notes = data.get("notes", "").strip()
        if note_type not in DOCTOR_DOCUMENT_TYPES:
            self.error("Ընտրեք փաստաթղթի ճիշտ տեսակ։")
            return
        if not anketa_number:
            self.error("Ընտրեք պացիենտ։")
            return
        if not diagnosis:
            self.error("Լրացրեք ախտորոշումը։")
            return
        if note_type != "Ախտորոշում" and not prescription and not notes:
            self.error("Լրացրեք պատասխանը կամ եզրակացությունը։")
            return
        with connect() as conn:
            patient = conn.execute("SELECT 1 FROM patients WHERE anketa_number = ?", (anketa_number,)).fetchone()
            if not patient:
                self.error("Պացիենտը չգտնվեց։", 404)
                return
            cur = conn.execute(
                """
                INSERT INTO doctor_notes
                (anketa_number, doctor, note_type, complaints, diagnosis, prescription, notes, created_by, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (anketa_number, doctor, note_type, complaints, diagnosis, prescription, notes, user["id"], now_iso(), now_iso()),
            )
        self.audit(user, "create", "doctor_notes", cur.lastrowid)
        self.send_json({"ok": True, "id": cur.lastrowid}, 201)

    def print_doctor_note(self, user, query):
        note_id = query.get("id", [""])[0].strip()
        if not note_id.isdigit():
            self.error("Սխալ գրառում։")
            return
        with connect() as conn:
            row = conn.execute(
                """
                SELECT n.id, n.anketa_number, n.doctor, n.note_type, n.complaints, n.diagnosis, n.prescription, n.notes, n.created_at,
                       p.first_name, p.last_name, p.father_name, p.birth_date, p.passport, p.phone,
                       d.specialty
                FROM doctor_notes n
                LEFT JOIN patients p ON p.anketa_number = n.anketa_number
                LEFT JOIN doctors d ON d.name = n.doctor
                WHERE n.id = ?
                """,
                (note_id,),
            ).fetchone()
        if not row:
            self.error("Գրառումը չգտնվեց։", 404)
            return
        note = dict(row)
        if user["role"] == "doctor" and note["doctor"] != self.doctor_name_for_user(user):
            self.error("Չեք կարող տպել այլ բժշկի գրառումը։", 403)
            return
        if user["role"] not in {"admin", "doctor"}:
            self.error("Տպելու թույլտվություն չկա։", 403)
            return
        def esc(value):
            return html.escape(str(value or ""))
        patient_name = " ".join(part for part in [note.get("first_name"), note.get("last_name"), note.get("father_name")] if part)
        created = esc(note.get("created_at", "")[:16].replace("T", " "))
        note_type = note.get("note_type") or "Ախտորոշում"
        is_diagnosis = note_type == "Ախտորոշում"
        if is_diagnosis:
            content_sections = f"""
      <h2>Գանգատներ</h2>
      <div class="text">{esc(note.get("complaints"))}</div>
      <h2>Ախտորոշում</h2>
      <div class="text">{esc(note.get("diagnosis"))}</div>
      <h2>Նշանակում / դեղատոմս</h2>
      <div class="text">{esc(note.get("prescription"))}</div>
      <h2>Լրացուցիչ նշումներ</h2>
      <div class="text">{esc(note.get("notes"))}</div>
      """
        else:
            content_sections = f"""
      <h2>Գանգատներ</h2>
      <div class="text">{esc(note.get("complaints"))}</div>
      <h2>Ախտորոշում</h2>
      <div class="text">{esc(note.get("diagnosis"))}</div>
      <h2>{esc(note_type)}</h2>
      <div class="text">{esc(note.get("prescription"))}</div>
      <h2>Լրացուցիչ նշումներ</h2>
      <div class="text">{esc(note.get("notes"))}</div>
      """
        markup = f"""<!doctype html>
<html lang="hy">
  <head>
    <meta charset="utf-8">
    <title>Cardio Vita - {esc(note_type)}</title>
    <style>
      body {{ font-family: Arial, "Noto Sans Armenian", sans-serif; color: #17343d; margin: 0; background: #eef4f6; }}
      .page {{ width: 210mm; min-height: 297mm; margin: 0 auto; background: #fff; padding: 18mm; box-sizing: border-box; }}
      .head {{ display: flex; justify-content: space-between; gap: 24px; border-bottom: 3px solid #176b87; padding-bottom: 14px; }}
      .brand {{ display: flex; align-items: center; gap: 14px; }}
      .brand img {{ width: 78px; height: auto; object-fit: contain; }}
      h1 {{ margin: 0; color: #176b87; font-size: 28px; }}
      h2 {{ margin: 22px 0 10px; color: #17343d; font-size: 18px; }}
      .muted {{ color: #607780; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 9px 18px; margin-top: 16px; }}
      .field {{ border: 1px solid #d8e4e8; border-radius: 8px; padding: 10px; }}
      .field span {{ display: block; color: #607780; font-size: 12px; margin-bottom: 4px; }}
      .field strong {{ white-space: pre-wrap; }}
      .text {{ border: 1px solid #d8e4e8; border-radius: 8px; padding: 12px; min-height: 72px; white-space: pre-wrap; line-height: 1.5; }}
      .signature {{ display: grid; grid-template-columns: 1fr 70mm; gap: 20px; margin-top: 32px; align-items: end; }}
      .line {{ border-top: 1px solid #17343d; padding-top: 7px; text-align: center; }}
      .actions {{ position: sticky; top: 0; padding: 10px; background: #17343d; text-align: center; }}
      button {{ background: #176b87; color: #fff; border: 0; border-radius: 6px; padding: 10px 16px; font: inherit; cursor: pointer; }}
      @media print {{ body {{ background: #fff; }} .actions {{ display: none; }} .page {{ width: auto; min-height: auto; margin: 0; padding: 0; }} }}
    </style>
  </head>
  <body>
    <div class="actions"><button onclick="window.print()">Տպել / պահպանել PDF</button></div>
    <main class="page">
      <header class="head">
        <div class="brand">
          <img src="/logo.png" alt="Cardio Vita logo">
          <div>
            <h1>Cardio Vita</h1>
            <div class="muted">Կլինիկայի բժշկական փաստաթուղթ</div>
          </div>
        </div>
        <div>
          <strong>Ամսաթիվ՝ {created}</strong><br>
          <span class="muted">Գրառում #{esc(note.get("id"))}</span>
        </div>
      </header>
      <h2>{esc(note_type)}</h2>
      <section class="grid">
        <div class="field"><span>Պացիենտ</span><strong>{esc(patient_name or note.get("anketa_number"))}</strong></div>
        <div class="field"><span>Անկետա #</span><strong>{esc(note.get("anketa_number"))}</strong></div>
        <div class="field"><span>Ծննդյան ամսաթիվ</span><strong>{esc(note.get("birth_date"))}</strong></div>
        <div class="field"><span>Հեռախոս</span><strong>{esc(note.get("phone"))}</strong></div>
        <div class="field"><span>Անձնագիր</span><strong>{esc(note.get("passport"))}</strong></div>
        <div class="field"><span>Բժիշկ</span><strong>{esc(note.get("specialty") or "Բժիշկ")}՝ {esc(note.get("doctor"))}</strong></div>
      </section>
      {content_sections}
      <footer class="signature">
        <div class="muted">Փաստաթուղթը ստեղծվել է Cardio Vita գրանցման համակարգից։</div>
        <div class="line">Բժշկի ստորագրություն</div>
      </footer>
    </main>
  </body>
</html>"""
        self.send_html(markup)

    def print_holter(self, user, query):
        holter_id = query.get("id", [""])[0].strip()
        if not holter_id.isdigit():
            self.error("Սխալ հոլտերի գրառում։")
            return
        with connect() as conn:
            row = conn.execute(
                """
                SELECT h.id, h.anketa_number, h.patient_name, h.phone, h.branch, h.provided_date,
                       h.provided_time, h.duration_hours, h.return_at, h.provided_status,
                       h.return_status, h.actual_return, h.notes, h.created_at,
                       p.first_name, p.last_name, p.father_name, p.birth_date, p.passport
                FROM holters h
                LEFT JOIN patients p ON p.anketa_number = h.anketa_number
                WHERE h.id = ?
                """,
                (holter_id,),
            ).fetchone()
        if not row:
            self.error("Հոլտերի գրառումը չգտնվեց։", 404)
            return
        holter = dict(row)
        if user["role"] == "doctor":
            doctor = self.doctor_name_for_user(user)
            with connect() as conn:
                can_access = conn.execute(
                    """
                    SELECT 1
                    FROM patients p
                    LEFT JOIN appointments a ON a.anketa_number = p.anketa_number AND a.doctor = ?
                    LEFT JOIN service_orders s ON s.anketa_number = p.anketa_number AND s.doctor = ?
                    WHERE p.anketa_number = ? AND (a.id IS NOT NULL OR s.id IS NOT NULL)
                    LIMIT 1
                    """,
                    (doctor, doctor, holter.get("anketa_number")),
                ).fetchone()
            if not can_access:
                self.error("Տպելու թույլտվություն չկա։", 403)
                return
        elif user["role"] != "admin" and holter.get("branch") != user.get("branch"):
            self.error("Տպելու թույլտվություն չկա։", 403)
            return
        def esc(value):
            return html.escape(str(value or ""))
        patient_name = holter.get("patient_name") or " ".join(part for part in [holter.get("first_name"), holter.get("last_name"), holter.get("father_name")] if part)
        created = esc((holter.get("created_at") or "")[:16].replace("T", " "))
        markup = f"""<!doctype html>
<html lang="hy">
  <head>
    <meta charset="utf-8">
    <title>Cardio Vita - Հոլտերի պատասխան</title>
    <style>{PRINT_STYLE}</style>
  </head>
  <body>
    <div class="actions"><button onclick="window.print()">Տպել / պահպանել PDF</button></div>
    <main class="page">
      {print_header("Հոլտերի պատասխան", "Հոլտերի հետազոտության փաստաթուղթ", created, esc(holter.get("id")))}
      <section class="grid">
        <div class="field"><span>Պացիենտ</span><strong>{esc(patient_name or holter.get("anketa_number"))}</strong></div>
        <div class="field"><span>Անկետա #</span><strong>{esc(holter.get("anketa_number"))}</strong></div>
        <div class="field"><span>Ծննդյան ամսաթիվ</span><strong>{esc(holter.get("birth_date"))}</strong></div>
        <div class="field"><span>Հեռախոս</span><strong>{esc(holter.get("phone"))}</strong></div>
        <div class="field"><span>Անձնագիր</span><strong>{esc(holter.get("passport"))}</strong></div>
        <div class="field"><span>Մասնաճյուղ</span><strong>{esc(holter.get("branch"))}</strong></div>
        <div class="field"><span>Տրման ամսաթիվ և ժամ</span><strong>{esc(holter.get("provided_date"))} {esc(holter.get("provided_time"))}</strong></div>
        <div class="field"><span>Տևողություն</span><strong>{esc(holter.get("duration_hours"))} ժամ</strong></div>
        <div class="field"><span>Վերադարձի ամսաթիվ և ժամ</span><strong>{esc(holter.get("return_at"))}</strong></div>
        <div class="field"><span>Փաստացի վերադարձ</span><strong>{esc(holter.get("actual_return"))}</strong></div>
        <div class="field"><span>Տրման կարգավիճակ</span><strong>{esc(holter.get("provided_status"))}</strong></div>
        <div class="field"><span>Վերադարձի կարգավիճակ</span><strong>{esc(holter.get("return_status"))}</strong></div>
      </section>
      <h2>Հոլտերի պատասխան / եզրակացություն</h2>
      <div class="text">{esc(holter.get("notes"))}</div>
      <footer class="signature">
        <div class="muted">Փաստաթուղթը ստեղծվել է Cardio Vita գրանցման համակարգից։</div>
        <div class="line">Պատասխանատուի ստորագրություն</div>
      </footer>
    </main>
  </body>
</html>"""
        self.send_html(markup)

    def create_patient(self, user):
        data = self.json_body()
        branch = data.get("branch")
        if branch not in BRANCHES:
            self.error("Ընտրեք մասնաճյուղ։")
            return
        if user["role"] != "admin" and branch != user["branch"]:
            self.error("No access to this branch.", 403)
            return
        required = ["visit_date", "first_name", "last_name"]
        if any(not str(data.get(k, "")).strip() for k in required):
            self.error("Լրացրեք պարտադիր դաշտերը։")
            return
        try:
            parse_date(data["visit_date"])
            birth_date = data.get("birth_date", "").strip()
            if birth_date:
                parse_date(birth_date)
            phone = clean_phone(data.get("phone"))
        except ValueError as exc:
            self.error(str(exc))
            return
        anketa_number = data.get("anketa_number", "").strip()
        try:
            with connect() as conn:
                if not anketa_number:
                    anketa_number = next_anketa_number(conn, branch)
                values = (
                    anketa_number, data["visit_date"], branch,
                    data["first_name"].strip(), data["last_name"].strip(),
                    data.get("father_name", "").strip(), birth_date,
                    data.get("passport", "").strip(), phone, data.get("email", "").strip(),
                    data.get("status", "Նոր"), data.get("payment", ""), data.get("notes", ""),
                    now_iso(), now_iso(),
                )
                cur = conn.execute(
                    """
                    INSERT INTO patients
                    (anketa_number, visit_date, branch, first_name, last_name, father_name, birth_date,
                     passport, phone, email, status, payment, notes, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    values,
                )
            self.audit(user, "create", "patients", cur.lastrowid)
            self.send_json({"ok": True, "id": cur.lastrowid, "anketa_number": anketa_number}, 201)
        except DB_INTEGRITY_ERRORS:
            self.error("Անկետա համարը արդեն կա։", 409)

    def create_appointment(self, user):
        data = self.json_body()
        branch = data.get("branch")
        doctor_values = data.get("doctors") or [data.get("doctor", "")]
        doctors = []
        for value in doctor_values:
            doctor = str(value).strip()
            if doctor and doctor not in doctors:
                doctors.append(doctor)
        try:
            day = parse_date(data.get("appointment_date"))
            at = parse_time(data.get("appointment_time"))
            phone = clean_phone(data.get("phone"))
        except ValueError as exc:
            self.error(str(exc))
            return
        if branch not in BRANCHES or not doctors:
            self.error("Ընտրեք մասնաճյուղ և բժիշկ։")
            return
        if user["role"] != "admin" and branch != user["branch"]:
            self.error("No access to this branch.", 403)
            return
        if not branch_is_open(branch, day, at):
            self.error("Մասնաճյուղը այդ ժամին չի աշխատում։", 400)
            return
        try:
            with connect() as conn:
                ids = []
                for doctor in doctors:
                    cur = conn.execute(
                        """
                        INSERT INTO appointments
                        (appointment_date, appointment_time, branch, doctor, anketa_number, patient_name, passport, phone, status, notes, created_at, updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            day.isoformat(), at.strftime("%H:%M"), branch, doctor,
                            data.get("anketa_number", "").strip(), data.get("patient_name", "").strip(),
                            data.get("passport", "").strip(), phone, data.get("status", "Նշանակված"),
                            data.get("notes", ""), now_iso(), now_iso(),
                        ),
                    )
                    ids.append(cur.lastrowid)
            self.audit(user, "create", "appointments", ",".join(str(i) for i in ids))
            self.send_json({"ok": True, "ids": ids, "count": len(ids)}, 201)
        except DB_INTEGRITY_ERRORS:
            self.error("Ընտրված բժիշկներից մեկը նույն օրը և ժամին արդեն զբաղված է։", 409)

    def create_holter(self, user):
        data = self.json_body()
        branch = data.get("branch")
        if branch not in BRANCHES:
            self.error("Ընտրեք մասնաճյուղ։")
            return
        if user["role"] != "admin" and branch != user["branch"]:
            self.error("No access to this branch.", 403)
            return
        try:
            day = parse_date(data.get("provided_date"))
            at = parse_time(data.get("provided_time"))
            duration = int(data.get("duration_hours", 24))
            phone = clean_phone(data.get("phone"))
        except ValueError as exc:
            self.error(str(exc))
            return
        if duration not in {24, 48, 72}:
            self.error("Տևողությունը պետք է լինի 24, 48 կամ 72։")
            return
        return_at = datetime.combine(day, at) + timedelta(hours=duration)
        with connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO holters
                (anketa_number, patient_name, phone, branch, provided_date, provided_time, duration_hours, return_at, provided_status,
                 return_status, actual_return, notes, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    data.get("anketa_number", "").strip(), data.get("patient_name", "").strip(), phone,
                    branch, day.isoformat(), at.strftime("%H:%M"),
                    duration, return_at.strftime("%Y-%m-%d %H:%M"), data.get("provided_status", ""),
                    data.get("return_status", ""), data.get("actual_return", ""), data.get("notes", ""),
                    now_iso(), now_iso(),
                ),
            )
        self.audit(user, "create", "holters", cur.lastrowid)
        self.send_json({"ok": True, "id": cur.lastrowid, "return_at": return_at.strftime("%Y-%m-%d %H:%M")}, 201)

    def create_service_order(self, user):
        data = self.json_body()
        kind = data.get("kind")
        if kind not in {"general", "lab"}:
            self.error("Wrong service type.")
            return
        branch = data.get("branch", "")
        if branch not in BRANCHES:
            self.error("Ընտրեք մասնաճյուղ։")
            return
        if user["role"] != "admin" and branch != user["branch"]:
            self.error("No access to this branch.", 403)
            return
        anketa_number = data.get("anketa_number", "").strip()
        if not anketa_number:
            self.error("Լրացրեք անկետա համարը։")
            return
        service_rows = data.get("services") or [{
            "category": data.get("category", ""),
            "service_name": data.get("service_name", ""),
            "price": data.get("price", 0),
            "doctor": data.get("doctor", ""),
        }]
        cleaned = []
        for row in service_rows:
            service_name = row.get("service_name", "").strip()
            if not service_name:
                continue
            doctor = row.get("doctor", "").strip()
            if not doctor:
                self.error("Յուրաքանչյուր ծառայության համար ընտրեք բժիշկ։")
                return
            try:
                price = int(row.get("price") or 0)
            except ValueError:
                self.error("Գինը պետք է լինի թիվ։")
                return
            cleaned.append((row.get("category", "").strip(), service_name, price, doctor))
        if not cleaned:
            self.error("Ավելացրեք առնվազն մեկ ծառայություն։")
            return
        with connect() as conn:
            ids = []
            for category, service_name, price, doctor in cleaned:
                cur = conn.execute(
                    """
                    INSERT INTO service_orders
                    (anketa_number, kind, branch, doctor, category, service_name, price, status, notes, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        anketa_number, kind, branch, doctor, category, service_name,
                        price, data.get("status", ""), data.get("notes", ""), now_iso(), now_iso(),
                    ),
                )
                ids.append(cur.lastrowid)
        self.audit(user, "create", "service_orders", ",".join(str(i) for i in ids))
        self.send_json({"ok": True, "ids": ids, "count": len(ids)}, 201)

    def calendar(self, user, query):
        branch = self.scoped_branch(user, query.get("branch", [""])[0]) or "Տերյան"
        doctor = query.get("doctor", [""])[0]
        try:
            start = parse_date(query.get("week", [date.today().isoformat()])[0])
        except ValueError as exc:
            self.error(str(exc))
            return
        days = [start + timedelta(days=i) for i in range(7)]
        slots = []
        current = time(8, 0)
        while current < time(20, 0):
            slots.append(current.strftime("%H:%M"))
            dt = datetime.combine(date.today(), current)
            dt += timedelta(minutes=30 if current < time(18, 0) else 10)
            current = dt.time()
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM appointments
                WHERE appointment_date BETWEEN ? AND ?
                  AND doctor = ?
                """,
                (days[0].isoformat(), days[-1].isoformat(), doctor),
            ).fetchall()
        by_key = {(r["appointment_date"], r["appointment_time"]): dict(r) for r in rows}
        grid = []
        for slot in slots:
            row = {"time": slot, "days": []}
            at = parse_time(slot)
            for day in days:
                appt = by_key.get((day.isoformat(), slot))
                row["days"].append({
                    "date": day.isoformat(),
                    "status": "Փակ" if not branch_is_open(branch, day, at) else ("Զբաղված" if appt else "Ազատ"),
                    "appointment": appt,
                })
            grid.append(row)
        self.send_json({"branch": branch, "doctor": doctor, "days": [d.isoformat() for d in days], "slots": grid})

    def summary(self, user):
        branch = self.scoped_branch(user, "")
        where = "WHERE branch = ?" if branch else ""
        params = [branch] if branch else []
        today_value = date.today().isoformat()
        week_end = (date.today() + timedelta(days=7)).isoformat()
        month_start = date.today().replace(day=1).isoformat()
        with connect() as conn:
            patients = conn.execute(f"SELECT COUNT(*) c FROM patients {where}", params).fetchone()["c"]
            appointments = conn.execute(f"SELECT COUNT(*) c FROM appointments {where}", params).fetchone()["c"]
            services = conn.execute(f"SELECT COUNT(*) c FROM service_orders {where}", params).fetchone()["c"]
            holters = conn.execute(f"SELECT COUNT(*) c FROM holters {where}", params).fetchone()["c"]
            today_patients = conn.execute(
                f"SELECT COUNT(*) c FROM patients WHERE visit_date = ? {'AND branch = ?' if branch else ''}",
                [today_value] + params,
            ).fetchone()["c"]
            today_appointments = conn.execute(
                f"SELECT COUNT(*) c FROM appointments WHERE appointment_date = ? {'AND branch = ?' if branch else ''}",
                [today_value] + params,
            ).fetchone()["c"]
            service_where = "WHERE branch = ?" if branch else ""
            revenue = conn.execute(f"SELECT kind, SUM(price) total FROM service_orders {service_where} GROUP BY kind", params).fetchall()
            month_revenue = conn.execute(
                f"SELECT COALESCE(SUM(price), 0) c FROM service_orders WHERE substr(created_at, 1, 10) >= ? {'AND branch = ?' if branch else ''}",
                [month_start] + params,
            ).fetchone()["c"]
            status_rows = conn.execute(
                f"SELECT status, COUNT(*) count FROM appointments {where} GROUP BY status ORDER BY count DESC",
                params,
            ).fetchall()
            branch_rows = conn.execute(
                """
                SELECT b.branch,
                       COALESCE(p.count, 0) patients,
                       COALESCE(a.count, 0) appointments,
                       COALESCE(s.revenue, 0) revenue
                FROM (SELECT 'Տերյան' branch UNION SELECT 'Նարեկացի' branch) b
                LEFT JOIN (SELECT branch, COUNT(*) count FROM patients GROUP BY branch) p ON p.branch = b.branch
                LEFT JOIN (SELECT branch, COUNT(*) count FROM appointments GROUP BY branch) a ON a.branch = b.branch
                LEFT JOIN (SELECT branch, SUM(price) revenue FROM service_orders GROUP BY branch) s ON s.branch = b.branch
                WHERE (? = '' OR b.branch = ?)
                ORDER BY b.branch
                """,
                (branch or "", branch or ""),
            ).fetchall()
            upcoming_holters = conn.execute(
                f"""
                SELECT anketa_number, patient_name, branch, return_at, return_status
                FROM holters
                WHERE substr(return_at, 1, 10) >= ? {'AND branch = ?' if branch else ''}
                ORDER BY return_at
                LIMIT 6
                """,
                [today_value] + params,
            ).fetchall()
            recent_appointments = conn.execute(
                f"""
                SELECT appointment_date, appointment_time, branch, doctor, patient_name, status
                FROM appointments
                {'WHERE branch = ?' if branch else ''}
                ORDER BY appointment_date DESC, appointment_time DESC
                LIMIT 6
                """,
                params,
            ).fetchall()
        self.send_json({
            "today": today_value,
            "branch": branch,
            "patients": patients,
            "appointments": appointments,
            "services": services,
            "holters": holters,
            "today_patients": today_patients,
            "today_appointments": today_appointments,
            "month_revenue": month_revenue,
            "revenue": [dict(r) for r in revenue],
            "by_status": [dict(r) for r in status_rows],
            "by_branch": [dict(r) for r in branch_rows],
            "upcoming_holters": [dict(r) for r in upcoming_holters],
            "recent_appointments": [dict(r) for r in recent_appointments],
        })

    def dashboard(self, user):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է տեսնել վահանակը։", 403)
            return
        today_value = date.today().isoformat()
        week_end = (date.today() + timedelta(days=7)).isoformat()
        month_start = date.today().replace(day=1).isoformat()
        with connect() as conn:
            totals = {
                "patients": conn.execute("SELECT COUNT(*) c FROM patients").fetchone()["c"],
                "appointments": conn.execute("SELECT COUNT(*) c FROM appointments").fetchone()["c"],
                "services": conn.execute("SELECT COUNT(*) c FROM service_orders").fetchone()["c"],
                "holters": conn.execute("SELECT COUNT(*) c FROM holters").fetchone()["c"],
                "today_patients": conn.execute("SELECT COUNT(*) c FROM patients WHERE visit_date = ?", (today_value,)).fetchone()["c"],
                "today_appointments": conn.execute("SELECT COUNT(*) c FROM appointments WHERE appointment_date = ?", (today_value,)).fetchone()["c"],
                "month_revenue": conn.execute("SELECT COALESCE(SUM(price), 0) c FROM service_orders WHERE substr(created_at, 1, 10) >= ?", (month_start,)).fetchone()["c"],
                "total_revenue": conn.execute("SELECT COALESCE(SUM(price), 0) c FROM service_orders").fetchone()["c"],
            }
            by_branch = [dict(r) for r in conn.execute(
                """
                SELECT b.branch,
                       COALESCE(p.count, 0) patients,
                       COALESCE(a.count, 0) appointments,
                       COALESCE(s.revenue, 0) revenue
                FROM (SELECT 'Տերյան' branch UNION SELECT 'Նարեկացի' branch) b
                LEFT JOIN (SELECT branch, COUNT(*) count FROM patients GROUP BY branch) p ON p.branch = b.branch
                LEFT JOIN (SELECT branch, COUNT(*) count FROM appointments GROUP BY branch) a ON a.branch = b.branch
                LEFT JOIN (SELECT branch, SUM(price) revenue FROM service_orders GROUP BY branch) s ON s.branch = b.branch
                ORDER BY b.branch
                """
            ).fetchall()]
            by_status = [dict(r) for r in conn.execute(
                "SELECT status, COUNT(*) count FROM appointments GROUP BY status ORDER BY count DESC"
            ).fetchall()]
            by_doctor = [dict(r) for r in conn.execute(
                """
                SELECT doctor, COUNT(*) count
                FROM appointments
                WHERE appointment_date BETWEEN ? AND ?
                GROUP BY doctor
                ORDER BY count DESC
                LIMIT 8
                """,
                (today_value, week_end),
            ).fetchall()]
            by_service = [dict(r) for r in conn.execute(
                "SELECT kind, COUNT(*) count, COALESCE(SUM(price), 0) revenue FROM service_orders GROUP BY kind ORDER BY kind"
            ).fetchall()]
            upcoming_holters = [dict(r) for r in conn.execute(
                """
                SELECT anketa_number, return_at, return_status
                FROM holters
                WHERE substr(return_at, 1, 10) >= ?
                ORDER BY return_at
                LIMIT 8
                """,
                (today_value,),
            ).fetchall()]
            recent_appointments = [dict(r) for r in conn.execute(
                """
                SELECT appointment_date, appointment_time, branch, doctor, patient_name, status
                FROM appointments
                ORDER BY appointment_date DESC, appointment_time DESC
                LIMIT 8
                """
            ).fetchall()]
        self.send_json({
            "today": today_value,
            "totals": totals,
            "by_branch": by_branch,
            "by_status": by_status,
            "by_doctor": by_doctor,
            "by_service": by_service,
            "upcoming_holters": upcoming_holters,
            "recent_appointments": recent_appointments,
        })

    def export_json(self, user):
        if user["role"] != "admin":
            self.error("Միայն ադմինը կարող է ներբեռնել ամբողջ պահուստը։", 403)
            return
        with connect() as conn:
            data = {}
            for table in ["patients", "appointments", "holters", "service_orders", "doctors", "doctor_notes"]:
                data[table] = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
        self.send_json(data)


def table_columns(table):
    with connect() as conn:
        if DATABASE_URL:
            rows = conn.execute(
                """
                SELECT column_name AS name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = ?
                """,
                (table,),
            ).fetchall()
        else:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {r["name"] for r in rows}


def public_user(user):
    if not user:
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "branch": user.get("branch"),
        "doctor_name": user.get("doctor_name"),
    }


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Cardio Vita cloud app running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), ClinicHandler).serve_forever()
