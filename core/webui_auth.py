"""Local administrator and session primitives for the update-manager control center."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any

from .adapters.storage import AtomicJsonStore, FileLeaseLock

PASSWORD_ITERATIONS = 600_000
PASSWORD_MIN_LENGTH = 8
SESSION_IDLE_SECONDS = 8 * 60 * 60
SESSION_ABSOLUTE_SECONDS = 24 * 60 * 60
ADMIN_ROLES = frozenset({"owner", "admin", "viewer"})
_USERNAME_LIMIT = 64


class WebUIAuthError(ValueError):
    """Expected validation/authentication failure without sensitive details."""


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    token: str
    admin_id: str
    username: str
    role: str
    created_at: float
    last_seen_at: float


class WebUIAuth:
    """Persist admins atomically and keep opaque sessions in memory only."""

    def __init__(self, store: AtomicJsonStore) -> None:
        self.store = store
        self._lock = threading.RLock()
        self._sessions: dict[str, AuthenticatedSession] = {}
        self._failed: dict[tuple[str, str], tuple[int, float]] = {}
        self._file_lock = FileLeaseLock(store.root / ".webui-admins.lock")

    def _read(self) -> list[dict[str, Any]]:
        try:
            value = self.store.read("webui-admins.json", [])
        except (OSError, TypeError, ValueError):
            return []
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _write(self, admins: list[dict[str, Any]]) -> None:
        self.store.write("webui-admins.json", admins)

    @staticmethod
    def _normal_username(value: Any) -> str:
        if not isinstance(value, str):
            raise WebUIAuthError("INVALID_USERNAME")
        username = value.strip()
        if (
            not username
            or len(username) > _USERNAME_LIMIT
            or any(char.isspace() for char in username)
        ):
            raise WebUIAuthError("INVALID_USERNAME")
        return username

    @staticmethod
    def _validate_password(value: Any) -> str:
        if not isinstance(value, str) or len(value) < PASSWORD_MIN_LENGTH:
            raise WebUIAuthError("PASSWORD_TOO_SHORT")
        if len(value) > 256:
            raise WebUIAuthError("PASSWORD_TOO_LONG")
        return value

    @staticmethod
    def _hash_password(password: str, salt: bytes | None = None) -> dict[str, Any]:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
        )
        return {
            "algorithm": "pbkdf2_sha256",
            "iterations": PASSWORD_ITERATIONS,
            "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
            "digest": base64.urlsafe_b64encode(digest).decode("ascii"),
        }

    @staticmethod
    def _verify_password(password: str, record: Any) -> bool:
        if not isinstance(record, dict):
            return False
        try:
            if record.get("algorithm") != "pbkdf2_sha256":
                return False
            iterations = int(record.get("iterations", 0))
            if iterations < 200_000 or iterations > 2_000_000:
                return False
            salt = base64.urlsafe_b64decode(str(record["salt"]).encode("ascii"))
            expected = base64.urlsafe_b64decode(str(record["digest"]).encode("ascii"))
        except (KeyError, TypeError, ValueError, base64.binascii.Error):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(record.get("id", "")),
            "username": str(record.get("username", "")),
            "role": str(record.get("role", "viewer")),
            "enabled": bool(record.get("enabled", False)),
            "created_at": record.get("created_at"),
            "last_login_at": record.get("last_login_at"),
            "locked": float(record.get("locked_until", 0) or 0) > time.time(),
        }

    def list_admins(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._public(item) for item in self._read()]

    def has_enabled_admin(self) -> bool:
        return any(item.get("enabled", False) for item in self._read())

    def create_admin(
        self, username: Any, password: Any, role: Any = "admin"
    ) -> dict[str, Any]:
        username = self._normal_username(username)
        password = self._validate_password(password)
        role = role if isinstance(role, str) else ""
        if role not in ADMIN_ROLES:
            raise WebUIAuthError("INVALID_ROLE")
        with self._lock:
            if not self._file_lock.acquire():
                raise WebUIAuthError("ADMIN_STORE_BUSY")
            try:
                admins = self._read()
                if any(
                    item.get("username", "").casefold() == username.casefold()
                    for item in admins
                ):
                    raise WebUIAuthError("USERNAME_EXISTS")
                if role == "owner" or not admins:
                    role = "owner" if not admins else role
                now = time.time()
                record = {
                    "id": secrets.token_hex(12),
                    "username": username,
                    "role": role,
                    "enabled": True,
                    "created_at": now,
                    "last_login_at": None,
                    "locked_until": 0.0,
                    "failed_count": 0,
                    "password": self._hash_password(password),
                }
                admins.append(record)
                self._write(admins)
                return self._public(record)
            finally:
                self._file_lock.release()

    def _find(
        self, admins: list[dict[str, Any]], username: str
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in admins
                if str(item.get("username", "")).casefold() == username.casefold()
            ),
            None,
        )

    def authenticate(self, username: Any, password: Any) -> AuthenticatedSession:
        username = self._normal_username(username)
        if not isinstance(password, str):
            raise WebUIAuthError("INVALID_CREDENTIALS")
        now = time.time()
        key = (username.casefold(), "login")
        with self._lock:
            attempts, retry_at = self._failed.get(key, (0, 0.0))
            if retry_at > now:
                raise WebUIAuthError("LOGIN_RATE_LIMITED")
            if not self._file_lock.acquire():
                raise WebUIAuthError("ADMIN_STORE_BUSY")
            try:
                admins = self._read()
                record = self._find(admins, username)
                valid = bool(
                    record and record.get("enabled", False)
                ) and self._verify_password(
                    password, record.get("password") if record else None
                )
                if not valid:
                    attempts += 1
                    delay = min(300.0, 2.0 ** min(attempts, 8))
                    self._failed[key] = (attempts, now + delay)
                    raise WebUIAuthError("INVALID_CREDENTIALS")
                self._failed.pop(key, None)
                record["last_login_at"] = now
                record["failed_count"] = 0
                self._write(admins)
            finally:
                self._file_lock.release()
            token = secrets.token_urlsafe(32)
            session = AuthenticatedSession(
                token=token,
                admin_id=str(record["id"]),
                username=str(record["username"]),
                role=str(record["role"]),
                created_at=now,
                last_seen_at=now,
            )
            self._sessions[token] = session
            return session

    def session(self, token: Any) -> AuthenticatedSession | None:
        if not isinstance(token, str) or not token:
            return None
        now = time.time()
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if (
                now - session.last_seen_at > SESSION_IDLE_SECONDS
                or now - session.created_at > SESSION_ABSOLUTE_SECONDS
            ):
                self._sessions.pop(token, None)
                return None
            record = next(
                (
                    item
                    for item in self._read()
                    if str(item.get("id", "")) == session.admin_id
                ),
                None,
            )
            if record is None or not record.get("enabled", False):
                self._sessions.pop(token, None)
                return None
            refreshed = AuthenticatedSession(
                token=session.token,
                admin_id=session.admin_id,
                username=str(record.get("username", session.username)),
                role=str(record.get("role", session.role)),
                created_at=session.created_at,
                last_seen_at=now,
            )
            self._sessions[token] = refreshed
            return refreshed

    def revoke(self, token: Any) -> None:
        if isinstance(token, str):
            with self._lock:
                self._sessions.pop(token, None)

    def change_admin(
        self,
        admin_id: Any,
        *,
        password: Any = None,
        role: Any = None,
        enabled: Any = None,
    ) -> dict[str, Any]:
        if not isinstance(admin_id, str) or not admin_id:
            raise WebUIAuthError("INVALID_ADMIN")
        if password is not None:
            password = self._validate_password(password)
        if role is not None and role not in ADMIN_ROLES:
            raise WebUIAuthError("INVALID_ROLE")
        with self._lock:
            if not self._file_lock.acquire():
                raise WebUIAuthError("ADMIN_STORE_BUSY")
            try:
                return self._change_admin_locked(
                    admin_id, password=password, role=role, enabled=enabled
                )
            finally:
                self._file_lock.release()

    def _change_admin_locked(
        self,
        admin_id: str,
        *,
        password: Any = None,
        role: Any = None,
        enabled: Any = None,
    ) -> dict[str, Any]:
        """Update one administrator while the process/file locks are held."""
        with self._lock:
            admins = self._read()
            record = next((item for item in admins if item.get("id") == admin_id), None)
            if record is None:
                raise WebUIAuthError("ADMIN_NOT_FOUND")
            if enabled is not None:
                if not isinstance(enabled, bool):
                    raise WebUIAuthError("INVALID_ENABLED")
                if not enabled and record.get("role") == "owner":
                    owners = [
                        item
                        for item in admins
                        if item.get("role") == "owner" and item.get("enabled")
                    ]
                    if len(owners) <= 1:
                        raise WebUIAuthError("LAST_OWNER_PROTECTED")
                record["enabled"] = enabled
            if role is not None:
                if role != "owner" and record.get("role") == "owner" and record.get("enabled"):
                    owners = [
                        item
                        for item in admins
                        if item is not record
                        and item.get("role") == "owner"
                        and item.get("enabled")
                    ]
                    if not owners:
                        raise WebUIAuthError("LAST_OWNER_PROTECTED")
                record["role"] = role
            if password is not None:
                record["password"] = self._hash_password(password)
            self._write(admins)
            if not record.get("enabled", False) or password is not None:
                for token, session in list(self._sessions.items()):
                    if session.admin_id == admin_id:
                        self._sessions.pop(token, None)
            return self._public(record)
