"""Real, server-verified authentication for the console.

Replaces the earlier "pick your name from a dropdown, the browser tells the
server who you are" reviewer selector -- which let anyone hitting the API
approve/reject as anyone, since the client-supplied `reviewer` string was
trusted outright. Now:

- Credentials live in a local SQLite store (`users.db`, gitignored), one row
  per person, password hashed with bcrypt. No self-registration; accounts
  are provisioned with `manage_users.py` (see that file for why).
- A successful login gets a signed, short-lived JWT in an HttpOnly, SameSite
  cookie. Every subsequent request re-verifies that JWT server-side --
  nothing about *who you are* ever comes from a request body again.
- Each user optionally maps to an Omnigraph Cedar actor (`actor_id`) --
  reviewers do, so their web login and their graph-level actor attribution
  are the same verified identity end to end. Viewer-only accounts have no
  actor_id and just get read access (dashboard reads already run as
  `act-admin` regardless of which human is looking, unchanged from before).

"SSO-ready": the pieces here (a `User` record, a session cookie carrying a
verified identity, a single `current_user` dependency gating every route)
are exactly what an OIDC/SAML integration would plug into later -- swap
`verify_password` for a callback that exchanges an IdP code for a verified
email, keep everything downstream the same. Not implemented here since a
real OIDC provider needs an app registration this POC can't create on its
own.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import bcrypt
import jwt
from fastapi import Cookie, Depends, HTTPException

DB_PATH = Path(__file__).resolve().parent / "users.db"
SESSION_SECRET_PATH = Path(__file__).resolve().parent / "session_secret.key"
SESSION_COOKIE = "session"
SESSION_TTL_SECONDS = 12 * 3600
JWT_ALGORITHM = "HS256"

ROLES = ("admin", "reviewer", "viewer")


def _session_secret() -> str:
    env = os.environ.get("SESSION_SECRET")
    if env:
        return env
    # Dev fallback only: persist a generated secret locally so sessions
    # survive a backend restart. In any real deployment set SESSION_SECRET
    # explicitly (and rotate it) -- a secret that lives in a file next to
    # the code it protects is not a production secrets story.
    if SESSION_SECRET_PATH.exists():
        return SESSION_SECRET_PATH.read_text(encoding="utf-8").strip()
    secret = os.urandom(32).hex()
    SESSION_SECRET_PATH.write_text(secret, encoding="utf-8")
    print(
        f"WARNING: SESSION_SECRET not set -- generated a dev-only secret at "
        f"{SESSION_SECRET_PATH}. Set SESSION_SECRET explicitly before deploying anywhere."
    )
    return secret


@dataclass
class User:
    username: str
    display_name: str
    role: str
    actor_id: str | None


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'reviewer', 'viewer')),
                actor_id TEXT
            )
            """
        )


def create_user(username: str, password: str, display_name: str, role: str, actor_id: str | None = None) -> None:
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}, got {role!r}")
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    with _db() as conn:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, display_name, role, actor_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                password_hash = excluded.password_hash,
                display_name = excluded.display_name,
                role = excluded.role,
                actor_id = excluded.actor_id
            """,
            (username, password_hash, display_name, role, actor_id),
        )


def user_exists(username: str) -> bool:
    with _db() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    return row is not None


def list_users() -> list[User]:
    with _db() as conn:
        rows = conn.execute("SELECT username, display_name, role, actor_id FROM users ORDER BY username").fetchall()
    return [User(r["username"], r["display_name"], r["role"], r["actor_id"]) for r in rows]


def verify_password(username: str, password: str) -> User | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT username, password_hash, display_name, role, actor_id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None:
        # Still run a bcrypt comparison against a dummy hash so a
        # nonexistent-username request takes the same time as a
        # wrong-password one (don't let response timing reveal which
        # usernames exist).
        bcrypt.checkpw(b"x", bcrypt.gensalt())
        return None
    if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return None
    return User(row["username"], row["display_name"], row["role"], row["actor_id"])


def create_session_token(user: User) -> str:
    now = int(time.time())
    payload = {
        "sub": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "actor_id": user.actor_id,
        "iat": now,
        "exp": now + SESSION_TTL_SECONDS,
    }
    return jwt.encode(payload, _session_secret(), algorithm=JWT_ALGORITHM)


def _decode_session_token(token: str) -> User | None:
    try:
        payload = jwt.decode(token, _session_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return User(payload["sub"], payload["display_name"], payload["role"], payload["actor_id"])


def current_user(session: str | None = Cookie(default=None)) -> User:
    """FastAPI dependency: require a valid session, return the verified User.

    Every route wrapped with `Depends(current_user)` re-verifies the JWT
    signature on every request -- there is no server-side session store to
    go stale or leak, and no path by which a client can claim an identity
    the cookie doesn't cryptographically back.
    """
    if session is None:
        raise HTTPException(401, "not authenticated")
    user = _decode_session_token(session)
    if user is None:
        raise HTTPException(401, "session invalid or expired")
    return user


def require_role(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"role '{user.role}' cannot perform this action")
        return user

    return dependency
