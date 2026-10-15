"""Recoverable, bounded storage for Human review sessions.

The cache is intentionally local to the ResearchOps API host.  It retains the
already bounded MaterialBundle and typed Rule/AI artifacts required for a
feedback reassessment, but never stores credentials, prompts, or raw provider
responses.  Values are encoded as tagged JSON with a restricted ResearchOps
class allowlist; arbitrary Python objects are never deserialized.
"""

from __future__ import annotations

import base64
import binascii
import importlib
import json
import os
import time
from collections.abc import Callable
from copy import deepcopy
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel

from researchops.core.access_context import current_access
from researchops.core.config import Settings, get_settings

_FORMAT_VERSION = 1
_ALLOWED_CLASS_MODULES = (
    "researchops.schemas",
    "researchops.services.environment_facts",
    "researchops.services.human_review",
    "researchops.services.local_evidence_finding_rules",
    "researchops.services.paper_materials",
    "researchops.services.repository_materials",
)


class AssessmentReviewStore(Protocol):
    """Storage port used by the Human review boundary."""

    def save(self, session: Any) -> None: ...

    def get(self, assessment_id: UUID) -> Any | None: ...


class AssessmentReviewStoreError(RuntimeError):
    """A retained review session could not be encoded or restored safely."""


class DurableAssessmentReviewStore:
    """File-backed, TTL-bounded review cache with sliding expiration."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        directory: Path | str | None = None,
        ttl_seconds: float | None = None,
        max_entries: int | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        config = settings or get_settings()
        self.directory = Path(directory or config.assessment_review_store_dir).resolve()
        self.ttl_seconds = ttl_seconds or config.assessment_review_ttl_seconds
        self.max_entries = max_entries or config.llm_analysis_run_max_entries
        self._clock = clock
        self._lock = RLock()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._restrict_permissions(self.directory, 0o700)

    def save(self, session: Any) -> None:
        assessment_id = self._assessment_id(session)
        with self._lock:
            now = self._clock()
            self._prune(now, keep=assessment_id)
            self._write(session, expires_at=now + self.ttl_seconds)
            self._enforce_capacity(keep=assessment_id)

    def get(self, assessment_id: UUID) -> Any | None:
        with self._lock:
            now = self._clock()
            self._prune(now)
            path = self._path(assessment_id)
            if not path.is_file():
                return None
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                if document.get("version") != _FORMAT_VERSION:
                    raise AssessmentReviewStoreError("Unsupported review cache format.")
                expires_at = float(document["expires_at"])
                if expires_at <= now:
                    path.unlink(missing_ok=True)
                    self._forget_ownership(path)
                    return None
                session = _decode(document["session"])
                if self._assessment_id(session) != assessment_id:
                    raise AssessmentReviewStoreError("Review cache identity does not match.")
            except (
                AssessmentReviewStoreError,
                AttributeError,
                ImportError,
                KeyError,
                OSError,
                TypeError,
                UnicodeError,
                ValueError,
                binascii.Error,
                json.JSONDecodeError,
            ):
                # A corrupt cache entry must not become a partially trusted review graph.
                path.unlink(missing_ok=True)
                self._forget_ownership(path)
                return None

            # Active viewing and feedback extend the retention window.  The
            # absolute cap remains bounded by the configured TTL after the
            # most recent successful access.
            self._write(session, expires_at=now + self.ttl_seconds)
            return deepcopy(session)

    def _write(self, session: Any, *, expires_at: float) -> None:
        assessment_id = self._assessment_id(session)
        path = self._path(assessment_id)
        temporary = self.directory / f".{assessment_id}.{uuid4().hex}.tmp"
        existing_path = self._path(assessment_id)
        created_at = self._clock()
        if existing_path.is_file():
            previous = json.loads(existing_path.read_text())
            created_at = float(previous.get("created_at", existing_path.stat().st_mtime))
        if current_access.get():
            expires_at = min(expires_at, created_at + self.ttl_seconds)
        document = {
            "created_at": created_at,
            "version": _FORMAT_VERSION,
            "assessment_id": str(assessment_id),
            "expires_at": expires_at,
            "session": _encode(session),
        }
        try:
            temporary.write_text(
                json.dumps(document, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            self._restrict_permissions(temporary, 0o600)
            os.replace(temporary, path)
            self._restrict_permissions(path, 0o600)
        finally:
            temporary.unlink(missing_ok=True)

    def _prune(self, now: float, *, keep: UUID | None = None) -> None:
        for path in self.directory.glob("*.json"):
            if keep is not None and path.stem == str(keep):
                continue
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                if float(document["expires_at"]) <= now:
                    path.unlink(missing_ok=True)
                    self._forget_ownership(path)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
                path.unlink(missing_ok=True)
                self._forget_ownership(path)

    def _enforce_capacity(self, *, keep: UUID) -> None:
        paths = sorted(
            self.directory.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
        )
        while len(paths) > self.max_entries:
            victim = next((item for item in paths if item.stem != str(keep)), None)
            if victim is None:
                return
            victim.unlink(missing_ok=True)
            self._forget_ownership(victim)
            paths.remove(victim)

    def _path(self, assessment_id: UUID) -> Path:
        return self.directory / f"{assessment_id}.json"

    def _forget_ownership(self, path):
        context = current_access.get()
        if context:
            context.store.forget_resource("assessment", path.stem)

    @staticmethod
    def _assessment_id(session: Any) -> UUID:
        assessment_id = getattr(session, "assessment_id", None)
        if not isinstance(assessment_id, UUID):
            raise AssessmentReviewStoreError("Review session has no valid Assessment ID.")
        return assessment_id

    @staticmethod
    def _restrict_permissions(path: Path, mode: int) -> None:
        try:
            path.chmod(mode)
        except OSError:
            # The cache remains inside the local app directory even on a file
            # system that cannot express POSIX-compatible permission bits.
            pass


def _encode(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, UUID):
        return {"$kind": "uuid", "value": str(value)}
    if isinstance(value, datetime):
        return {"$kind": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"$kind": "date", "value": value.isoformat()}
    if isinstance(value, bytes):
        return {"$kind": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Path):
        return {"$kind": "path", "value": str(value)}
    if isinstance(value, BaseModel):
        return {
            "$kind": "pydantic",
            "class": _class_ref(type(value)),
            # JSON mode normalizes Pydantic network/secret wrapper classes;
            # model_validate restores the declared field types on recovery.
            "value": _encode(value.model_dump(mode="json")),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "$kind": "dataclass",
            "class": _class_ref(type(value)),
            "value": {item.name: _encode(getattr(value, item.name)) for item in fields(value)},
        }
    if isinstance(value, dict):
        return {
            "$kind": "dict",
            "value": [[_encode(key), _encode(item)] for key, item in value.items()],
        }
    if isinstance(value, list):
        return {"$kind": "list", "value": [_encode(item) for item in value]}
    if isinstance(value, tuple):
        return {"$kind": "tuple", "value": [_encode(item) for item in value]}
    raise AssessmentReviewStoreError(
        f"Review state contains unsupported value type {type(value).__name__}."
    )


def _decode(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if not isinstance(value, dict) or "$kind" not in value:
        raise AssessmentReviewStoreError("Review cache contains an invalid tagged value.")
    kind = value["$kind"]
    payload = value.get("value")
    if kind == "uuid":
        return UUID(payload)
    if kind == "datetime":
        return datetime.fromisoformat(payload)
    if kind == "date":
        return date.fromisoformat(payload)
    if kind == "bytes":
        return base64.b64decode(payload, validate=True)
    if kind == "path":
        return Path(payload)
    if kind == "dict":
        return {_decode(key): _decode(item) for key, item in payload}
    if kind == "list":
        return [_decode(item) for item in payload]
    if kind == "tuple":
        return tuple(_decode(item) for item in payload)
    if kind in {"pydantic", "dataclass"}:
        cls = _load_class(value.get("class"))
        decoded = (
            _decode(payload)
            if kind == "pydantic"
            else {key: _decode(item) for key, item in payload.items()}
        )
        if kind == "pydantic":
            if not issubclass(cls, BaseModel):
                raise AssessmentReviewStoreError("Stored class is not a Pydantic model.")
            return cls.model_validate(decoded)
        if not is_dataclass(cls):
            raise AssessmentReviewStoreError("Stored class is not a dataclass.")
        return cls(**decoded)
    raise AssessmentReviewStoreError(f"Unknown review cache value kind {kind!r}.")


def _class_ref(cls: type) -> str:
    if not _module_allowed(cls.__module__):
        raise AssessmentReviewStoreError(
            f"Review state class {cls.__module__}.{cls.__qualname__} is not allowed."
        )
    return f"{cls.__module__}:{cls.__qualname__}"


def _load_class(reference: object) -> type:
    if not isinstance(reference, str) or ":" not in reference:
        raise AssessmentReviewStoreError("Review cache class reference is invalid.")
    module_name, qualname = reference.split(":", 1)
    if not _module_allowed(module_name):
        raise AssessmentReviewStoreError("Review cache class module is not allowed.")
    module = importlib.import_module(module_name)
    target: Any = module
    for part in qualname.split("."):
        if part.startswith("_"):
            raise AssessmentReviewStoreError("Private review cache classes are not allowed.")
        target = getattr(target, part, None)
        if target is None:
            raise AssessmentReviewStoreError("Review cache class could not be resolved.")
    if not isinstance(target, type):
        raise AssessmentReviewStoreError("Review cache class reference is not a type.")
    return target


def _module_allowed(module_name: str) -> bool:
    return any(
        module_name == allowed or module_name.startswith(f"{allowed}.")
        for allowed in _ALLOWED_CLASS_MODULES
    )
