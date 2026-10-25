import hashlib
import hmac
import os
import re
import sqlite3

from app import config

_HASH_ALGORITHM = "pbkdf2_sha256"
_HASH_ITERATIONS = 600_000
_SALT_BYTES = 16
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")
_DUMMY_SALT = b"travel-itinerary-login-dummy-salt"
_DUMMY_HASH = hashlib.pbkdf2_hmac(
    "sha256", b"not-a-real-password", _DUMMY_SALT, _HASH_ITERATIONS
).hex()


def _connect() -> sqlite3.Connection:
    config.AUTH_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.AUTH_DB_PATH)


def initialize_auth_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not _USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3-64 characters: start with a letter or number, "
            "then use only letters, numbers, dots, underscores, or hyphens."
        )
    return normalized


def _hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _HASH_ITERATIONS
    )
    return f"{_HASH_ALGORITHM}${_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded_hash: str) -> bool:
    algorithm, iterations, salt_hex, expected_digest = encoded_hash.split("$", 3)
    if algorithm != _HASH_ALGORITHM:
        raise ValueError("Stored password hash uses an unsupported algorithm.")
    iteration_count = int(iterations)
    if not 100_000 <= iteration_count <= 2_000_000:
        raise ValueError("Stored password hash has an invalid work factor.")
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iteration_count
    ).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


def create_user(username: str, password: str) -> None:
    normalized = _normalize_username(username)
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    if len(password) > 1024:
        raise ValueError("Password must be no longer than 1024 characters.")

    initialize_auth_db()
    try:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (normalized, _hash_password(password)),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"User '{normalized}' already exists.") from exc


def authenticate(username: str, password: str) -> str | None:
    normalized = username.strip()
    if not normalized or not password:
        return None

    initialize_auth_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (normalized,),
        ).fetchone()

    if row is None:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _DUMMY_SALT, _HASH_ITERATIONS)
        return None
    return row[0] if _verify_password(password, row[1]) else None
