import sqlite3

import pytest

from app import config
from app.services.auth_service import authenticate, create_user, initialize_auth_db


@pytest.fixture
def auth_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AUTH_DB_PATH", tmp_path / "users.sqlite3")
    initialize_auth_db()
    return config.AUTH_DB_PATH


def test_create_user_stores_password_hash_and_authenticates(auth_db):
    create_user("TripPlanner", "long-secure-password")

    assert authenticate("tripplanner", "long-secure-password") == "TripPlanner"
    assert authenticate("TripPlanner", "wrong-password") is None

    with sqlite3.connect(auth_db) as connection:
        stored_hash = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?", ("TripPlanner",)
        ).fetchone()[0]

    assert stored_hash.startswith("pbkdf2_sha256$")
    assert stored_hash != "long-secure-password"


def test_duplicate_usernames_are_rejected_case_insensitively(auth_db):
    create_user("TripPlanner", "long-secure-password")

    with pytest.raises(ValueError, match="already exists"):
        create_user("tripplanner", "another-secure-password")


def test_user_creation_rejects_short_passwords(auth_db):
    with pytest.raises(ValueError, match="at least 12 characters"):
        create_user("TripPlanner", "short")


def test_user_creation_rejects_invalid_usernames(auth_db):
    with pytest.raises(ValueError, match="Username must be"):
        create_user("not a username", "long-secure-password")


def test_authentication_of_unknown_user_fails(auth_db):
    assert authenticate("unknown", "long-secure-password") is None
