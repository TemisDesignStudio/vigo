import hashlib
import hmac
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def database_path() -> Path:
    return Path(os.getenv("VIGO_DB_PATH", "/data/vigo.db"))


def now() -> str:
    return datetime.now(UTC).isoformat()


def password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def password_matches(password: str, stored_hash: str) -> bool:
    algorithm, salt_hex, digest_hex = stored_hash.split("$", maxsplit=2)
    if algorithm != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


def initialize_database() -> None:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role = 'admin'),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                requester_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                budget INTEGER NOT NULL CHECK (budget >= 0),
                objective TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewing', 'approved', 'active', 'completed', 'rejected')),
                created_by_user_id INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS collaboration_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                social_network TEXT NOT NULL,
                profile_url TEXT NOT NULL,
                activity_field TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'reviewing', 'approved', 'rejected')),
                created_by_user_id INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
            CREATE INDEX IF NOT EXISTS idx_collaboration_requests_status ON collaboration_requests(status);
            """
        )
        timestamp = now()
        if connection.execute("SELECT 1 FROM users WHERE username = ?", ("user",)).fetchone() is None:
            connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("user", password_hash("password"), "admin", timestamp, timestamp),
            )
        connection.execute("PRAGMA user_version = 1")


def connect() -> sqlite3.Connection:
    initialize_database()
    connection = sqlite3.connect(database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
