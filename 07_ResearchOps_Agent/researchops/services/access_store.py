"""Transactional control state. No raw invitation or session tokens are retained."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import secrets
import sqlite3
import stat
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from researchops.core.config import Settings


class AccessError(RuntimeError):
    def __init__(self, code: str, message: str, status: int = 403, retry_after: int = 60):
        super().__init__(message)
        self.code, self.status, self.retry_after = code, status, retry_after


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AccessStore:
    """Small single-host SQLite ledger with bounded expiry and immediate revocation."""

    def __init__(self, settings: Settings, *, clock=time.time):
        self.settings, self.clock = settings, clock
        self.directory = settings.security_store_dir.resolve()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._private(self.directory, 0o700)
        self.path = self.directory / "control.sqlite3"
        self._instance_file = None
        if self.path.exists():
            self._private(self.path, 0o600)
        # Restrictive creation, including SQLite journal files, without global umask changes.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self.transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in {0, 1}:
                raise RuntimeError("Unsupported security database version")
            statements = [
                "CREATE TABLE IF NOT EXISTS invitations (id TEXT PRIMARY KEY, hash TEXT UNIQUE, "
                "label TEXT NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, "
                "daily_limit INTEGER NOT NULL, created REAL NOT NULL)",
                "CREATE TABLE IF NOT EXISTS sessions (hash TEXT PRIMARY KEY, principal TEXT NOT NULL, "
                "csrf TEXT NOT NULL, expires REAL NOT NULL, created REAL NOT NULL)",
                "CREATE TABLE IF NOT EXISTS owners (kind TEXT, resource TEXT, principal TEXT NOT NULL, "
                "expires REAL NOT NULL, PRIMARY KEY(kind,resource))",
                "CREATE TABLE IF NOT EXISTS usage (day TEXT, principal TEXT, kind TEXT, "
                "count INTEGER NOT NULL, PRIMARY KEY(day,principal,kind))",
                "CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, principal TEXT NOT NULL, "
                "day TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, started REAL, "
                "attempts INTEGER NOT NULL DEFAULT 0, snapshot TEXT)",
                "CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, created REAL NOT NULL, "
                "event TEXT NOT NULL, principal TEXT, resource TEXT)",
                "CREATE TABLE IF NOT EXISTS rate (key TEXT PRIMARY KEY, count INTEGER, expires REAL)",
                "CREATE INDEX IF NOT EXISTS operations_active ON operations(principal,state)",
            ]
            for statement in statements:
                db.execute(statement)
            db.execute("PRAGMA user_version=1")
        self.cleanup()

    @staticmethod
    def _private(path: Path, mode: int):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
            raise PermissionError("Unsafe security state ownership")
        path.chmod(mode)
        if stat.S_IMODE(path.stat().st_mode) != mode:
            raise PermissionError("Security permissions could not be enforced")

    @contextmanager
    def transaction(self):
        if not self.path.is_file() or self.path.is_symlink():
            raise RuntimeError("Security state unavailable")
        self._private(self.path, 0o600)
        db = sqlite3.connect(self.path, timeout=3, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=3000")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def acquire_instance(self):
        if self._instance_file is not None:
            return
        path = self.directory / "instance.lock"
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        self._instance_file = os.fdopen(fd, "a")
        try:
            fcntl.flock(self._instance_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._instance_file.close()
            self._instance_file = None
            raise RuntimeError("Another API execution instance is already running") from None
        with self.transaction() as db:
            db.execute(
                "UPDATE operations SET state='interrupted' WHERE state IN ('queued','running')"
            )

    def release_instance(self):
        if self._instance_file:
            self._instance_file.close()
            self._instance_file = None

    def _audit(self, db, event, principal=None, resource=None):
        db.execute(
            "INSERT INTO audit(created,event,principal,resource) VALUES (?,?,?,?)",
            (self.clock(), event, principal, resource),
        )

    def create_invitation(self, label: str, *, days: int | None = None, limit: int | None = None):
        if not label or len(label) > 100:
            raise ValueError("Label must contain 1..100 characters")
        days = self.settings.invitation_days if days is None else days
        limit = self.settings.invitation_daily_limit if limit is None else limit
        if not 1 <= days <= 365 or not 1 <= limit <= 10000:
            raise ValueError("Invalid invitation duration or daily limit")
        token, principal = secrets.token_urlsafe(32), str(uuid4())
        with self.transaction() as db:
            db.execute(
                "INSERT INTO invitations VALUES (?,?,?,?,0,?,?)",
                (principal, digest(token), label, self.clock() + days * 86400, limit, self.clock()),
            )
            self._audit(db, "invitation.created", principal)
        return principal, token

    def list_invitations(self):
        with self.transaction() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,label,expires,revoked,daily_limit,created FROM invitations ORDER BY created"
                )
            ]

    def update_invitation(self, principal: str, *, revoke=False, limit=None, days=None):
        if limit is not None and not 1 <= limit <= 10000:
            raise ValueError("Invalid quota")
        if days is not None and not 1 <= days <= 365:
            raise ValueError("Invalid duration")
        with self.transaction() as db:
            if not db.execute("SELECT id FROM invitations WHERE id=?", (principal,)).fetchone():
                raise ValueError("Unknown invitation ID")
            if limit is not None:
                db.execute("UPDATE invitations SET daily_limit=? WHERE id=?", (limit, principal))
            if days is not None:
                db.execute(
                    "UPDATE invitations SET expires=? WHERE id=?",
                    (self.clock() + days * 86400, principal),
                )
            if revoke:
                db.execute("UPDATE invitations SET revoked=1 WHERE id=?", (principal,))
                db.execute("DELETE FROM sessions WHERE principal=?", (principal,))
            self._audit(db, "invitation.updated", principal)

    def _invitation(self, db, principal):
        row = db.execute("SELECT * FROM invitations WHERE id=?", (principal,)).fetchone()
        if not row or row["revoked"] or row["expires"] <= self.clock():
            raise AccessError("ACCESS_REQUIRED", "邀请码无效或已过期。", 401)
        return row

    def exchange(self, token: str):
        with self.transaction() as db:
            row = db.execute("SELECT id FROM invitations WHERE hash=?", (digest(token),)).fetchone()
            if not row:
                raise AccessError("ACCESS_REQUIRED", "邀请码无效或已过期。", 401)
            invitation = self._invitation(db, row["id"])
            session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            expiry = min(self.clock() + self.settings.session_seconds, invitation["expires"])
            db.execute("DELETE FROM sessions WHERE expires<=?", (self.clock(),))
            # At most ten sessions per invitation; new logins replace the oldest.
            db.execute(
                "DELETE FROM sessions WHERE hash IN (SELECT hash FROM sessions "
                "WHERE principal=? ORDER BY created DESC LIMIT -1 OFFSET 9)",
                (row["id"],),
            )
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?)",
                (digest(session), row["id"], csrf, expiry, self.clock()),
            )
            self._audit(db, "session.created", row["id"])
            return session, {"principal_id": row["id"], "csrf_token": csrf, "expires_at": expiry}

    def authenticate(self, token: str | None):
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM sessions WHERE hash=?", (digest(token or ""),)
            ).fetchone()
            if not row or row["expires"] <= self.clock():
                raise AccessError("ACCESS_REQUIRED", "请先输入邀请码。", 401)
            self._invitation(db, row["principal"])
            return {
                "principal_id": row["principal"],
                "csrf_token": row["csrf"],
                "expires_at": row["expires"],
            }

    def logout(self, token):
        with self.transaction() as db:
            db.execute("DELETE FROM sessions WHERE hash=?", (digest(token or ""),))

    def bind(self, kind: str, resource, principal: str, *, expires=None):
        with self.transaction() as db:
            self._invitation(db, principal)
            db.execute(
                "INSERT INTO owners VALUES (?,?,?,?)",
                (
                    kind,
                    str(resource),
                    principal,
                    expires or self.clock() + self.settings.assessment_review_ttl_seconds,
                ),
            )
            self._audit(db, "resource.bound", principal, str(resource))

    def authorize(self, kind: str, resource, principal: str):
        with self.transaction() as db:
            self._invitation(db, principal)
            row = db.execute(
                "SELECT principal,expires FROM owners WHERE kind=? AND resource=?",
                (kind, str(resource)),
            ).fetchone()
            if not row or row["principal"] != principal or row["expires"] <= self.clock():
                raise AccessError("RESOURCE_NOT_FOUND", "资源不存在或已过期。", 404)

    def forget_resource(self, kind, resource):
        with self.transaction() as db:
            db.execute("DELETE FROM owners WHERE kind=? AND resource=?", (kind, str(resource)))

    def rate_limit(self, rules: list[tuple[str, int, int]]):
        with self.transaction() as db:
            now = self.clock()
            db.execute("DELETE FROM rate WHERE expires<=?", (now,))
            for key, limit, seconds in rules:
                row = db.execute("SELECT * FROM rate WHERE key=?", (key,)).fetchone()
                if row and row["count"] >= limit:
                    raise AccessError(
                        "RATE_LIMITED",
                        "请求过于频繁，请稍后再试。",
                        429,
                        max(1, int(row["expires"] - now) + 1),
                    )
                if not row:
                    if db.execute("SELECT COUNT(*) FROM rate").fetchone()[0] >= 10000:
                        raise AccessError("RATE_LIMITED", "请求过于频繁，请稍后再试。", 429)
                    db.execute("INSERT INTO rate VALUES (?,1,?)", (key, now + seconds))
                else:
                    db.execute("UPDATE rate SET count=count+1 WHERE key=?", (key,))

    def _day(self):
        return datetime.fromtimestamp(self.clock(), ZoneInfo("Asia/Shanghai")).date().isoformat()

    def _consume(self, db, principal, kind, limit, *, day=None):
        day = day or self._day()
        count = db.execute(
            "SELECT count FROM usage WHERE day=? AND principal=? AND kind=?", (day, principal, kind)
        ).fetchone()
        if count and count[0] >= limit:
            raise AccessError("BUDGET_EXHAUSTED", "今日使用额度已用完。", 429, 3600)
        db.execute(
            "INSERT INTO usage VALUES (?,?,?,1) ON CONFLICT(day,principal,kind) "
            "DO UPDATE SET count=count+1",
            (day, principal, kind),
        )

    def reserve(self, principal: str):
        with self.transaction() as db:
            invitation = self._invitation(db, principal)
            total = db.execute(
                "SELECT COUNT(*) FROM operations WHERE state IN ('queued','running')"
            ).fetchone()[0]
            active = db.execute(
                "SELECT COUNT(*) FROM operations WHERE principal=? "
                "AND state IN ('queued','running')",
                (principal,),
            ).fetchone()[0]
            if total >= self.settings.execution_concurrency + self.settings.execution_queue_size:
                raise AccessError("EXECUTION_CAPACITY_EXCEEDED", "任务繁忙，请稍后再试。", 503)
            if active:
                raise AccessError("PRINCIPAL_BUSY", "已有任务正在处理，请等待完成。", 429)
            self._consume(db, principal, "operations", invitation["daily_limit"])
            self._consume(db, "*", "operations", self.settings.global_daily_limit)
            operation = str(uuid4())
            db.execute(
                "INSERT INTO operations(id,principal,day,state,created) VALUES (?,?,?,'queued',?)",
                (operation, principal, self._day(), self.clock()),
            )
            return operation

    def start(self, operation):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if not row or row["state"] != "queued":
                raise AccessError("OPERATION_STOPPED", "任务已停止。", 409)
            self._invitation(db, row["principal"])
            if self.clock() - row["created"] >= self.settings.execution_queue_seconds:
                raise AccessError("QUEUE_TIMEOUT", "等待超时，请稍后重试。", 503)
            db.execute(
                "UPDATE operations SET state='running',started=? WHERE id=?",
                (self.clock(), operation),
            )

    def attempt(self, operation, request_bytes: int):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if not row or row["state"] != "running":
                raise AccessError("OPERATION_STOPPED", "任务已停止。", 409)
            self._invitation(db, row["principal"])
            remaining = self.settings.execution_timeout_seconds - (self.clock() - row["started"])
            if remaining <= 0:
                raise AccessError("EXECUTION_TIMEOUT", "任务执行超时。", 504)
            if request_bytes > self.settings.model_request_max_bytes:
                raise AccessError("MODEL_INPUT_TOO_LARGE", "模型输入超出限制。", 413)
            if row["attempts"] >= self.settings.operation_model_attempts:
                raise AccessError("BUDGET_EXHAUSTED", "本次任务模型调用额度已用完。", 429)
            self._consume(db, "*", "model_attempts", self.settings.global_daily_model_attempts)
            db.execute("UPDATE operations SET attempts=attempts+1 WHERE id=?", (operation,))
            return remaining

    def check_operation(self, operation):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if not row or row["state"] != "running":
                raise AccessError("OPERATION_STOPPED", "任务已停止。", 409)
            self._invitation(db, row["principal"])
            remaining = self.settings.execution_timeout_seconds - (self.clock() - row["started"])
            if remaining <= 0:
                raise AccessError("EXECUTION_TIMEOUT", "任务执行超时。", 504)
            return remaining

    def finish(self, operation, state="completed"):
        if state not in {"completed", "failed", "interrupted"}:
            raise ValueError("Invalid operation state")
        with self.transaction() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (operation,)).fetchone()
            if not row or row["state"] not in {"queued", "running"}:
                return
            if row["state"] == "queued":
                for principal in (row["principal"], "*"):
                    db.execute(
                        "UPDATE usage SET count=MAX(0,count-1) "
                        "WHERE day=? AND principal=? AND kind='operations'",
                        (row["day"], principal),
                    )
            db.execute("UPDATE operations SET state=? WHERE id=?", (state, operation))
            self._audit(db, "operation." + state, row["principal"], operation)

    def save_snapshot(self, operation, snapshot):
        with self.transaction() as db:
            db.execute(
                "UPDATE operations SET snapshot=? WHERE id=?", (json.dumps(snapshot), operation)
            )

    def operation(self, operation):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (str(operation),)).fetchone()
            return dict(row) if row else None

    def cleanup(self):
        with self.transaction() as db:
            now = self.clock()
            db.execute("DELETE FROM sessions WHERE expires<=?", (now,))
            db.execute("DELETE FROM owners WHERE expires<=?", (now,))
            db.execute("DELETE FROM rate WHERE expires<=?", (now,))
            db.execute("DELETE FROM audit WHERE created<?", (now - 30 * 86400,))
            db.execute(
                "DELETE FROM audit WHERE id NOT IN "
                "(SELECT id FROM audit ORDER BY id DESC LIMIT 10000)"
            )
            db.execute(
                "DELETE FROM operations WHERE state NOT IN ('queued','running') AND created<?",
                (now - 86400,),
            )
            cutoff = datetime.fromtimestamp(now - 90 * 86400, ZoneInfo("Asia/Shanghai")).date()
            db.execute("DELETE FROM usage WHERE day<?", (cutoff.isoformat(),))
