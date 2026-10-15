"""本地只读环境采集的短期授权令牌。"""

import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class EnvironmentAuthorizationGrant:
    """仅保存在当前进程内的短期授权。"""

    token: str
    expires_at: datetime


class EnvironmentAuthorizationService:
    """签发并校验短期 bearer token，不写入磁盘。"""

    def __init__(self, *, lifetime_seconds: int = 600) -> None:
        self.lifetime_seconds = lifetime_seconds
        self._tokens: dict[str, float] = {}
        self._lock = threading.Lock()

    def issue(self) -> EnvironmentAuthorizationGrant:
        token = secrets.token_urlsafe(32)
        expires_monotonic = time.monotonic() + self.lifetime_seconds
        with self._lock:
            self._remove_expired_locked()
            self._tokens[token] = expires_monotonic
        return EnvironmentAuthorizationGrant(
            token=token,
            expires_at=datetime.now(UTC) + timedelta(seconds=self.lifetime_seconds),
        )

    def validate(self, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            self._remove_expired_locked()
            return self._tokens.get(token, 0) > time.monotonic()

    def _remove_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [token for token, expires_at in self._tokens.items() if expires_at <= now]
        for token in expired:
            self._tokens.pop(token, None)
