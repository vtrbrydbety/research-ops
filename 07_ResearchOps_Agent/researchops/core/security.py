"""Shared security primitives for credential-safe diagnostics."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [^-\r\n]*PRIVATE KEY-----.*?-----END [^-\r\n]*PRIVATE KEY-----",
    re.IGNORECASE | re.DOTALL,
)
_LABELED_SECRET_PATTERN = re.compile(
    r"(?im)(?P<prefix>\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|authorization|"
    r"secret|password|invitation[_-]?code|csrf[_-]?token|session[_-]?token|"
    r"TunnelSecret|cookie|set-cookie)\b[\"']?\s*[:=]\s*[\"']?)(?P<value>[^\r\n\"'#]+)(?P<suffix>[\"']?)"
)
_BEARER_PATTERN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~+/=-]{12,}")
_KNOWN_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})(?![A-Za-z0-9])"
)
_SENSITIVE_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "key",
    "password",
    "sig",
    "signature",
    "token",
}


def redact_sensitive_text(value: object) -> str:
    """Redact common credentials from log messages and formatted exceptions."""

    text = str(value)
    text = _PRIVATE_KEY_PATTERN.sub("[REDACTED:PRIVATE_KEY]", text)
    text = _LABELED_SECRET_PATTERN.sub(
        lambda match: f"{match.group('prefix')}[REDACTED:SECRET]{match.group('suffix')}",
        text,
    )
    text = _BEARER_PATTERN.sub(r"\1[REDACTED:TOKEN]", text)
    return _KNOWN_TOKEN_PATTERN.sub("[REDACTED:TOKEN]", text)


def redact_sensitive_url(value: object) -> str:
    """Remove URL credentials and redact well-known sensitive query values."""

    parts = urlsplit(str(value))
    hostname = parts.hostname or ""
    netloc = hostname
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    query = urlencode(
        [
            (key, "[REDACTED]" if key.casefold() in _SENSITIVE_QUERY_KEYS else item_value)
            for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, netloc, parts.path, query, parts.fragment))
