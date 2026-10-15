"""公开外部模型资产入口的受限只读核验。"""

import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urljoin, urlparse

import httpx

from researchops.core.outbound import outbound_client
from researchops.core.security import redact_sensitive_url

# GitHub release downloads may redirect to GitHub's signed object hosts.  These
# hosts are reachable only after the Rule layer has verified the release URL
# belongs to the collected official repository.
ALLOWED_ASSET_HOSTS = {
    "drive.google.com",
    "github.com",
    "github-releases.githubusercontent.com",
    "objects.githubusercontent.com",
}
INACCESSIBLE_MARKERS = (
    "access denied",
    "request access",
    "you need access",
    "file you have requested does not exist",
    "the requested url was not found",
    "couldn't find the requested file",
)
TITLE_PATTERN = re.compile(r"<title[^>]*>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class ExternalAssetProbeResult:
    """外部资产入口的可访问性核验结果。"""

    source_url: str
    final_url: str | None
    accessible: bool
    detail: str
    state: Literal["verified_public", "verified_inaccessible", "acquisition_failure"] | None = None

    @property
    def verification_state(
        self,
    ) -> Literal["verified_public", "verified_inaccessible", "acquisition_failure"]:
        """兼容测试探针，并明确区分事实性不可访问与技术获取失败。"""

        if self.state is not None:
            return self.state
        return "verified_public" if self.accessible else "verified_inaccessible"


class ExternalAssetProbe(Protocol):
    """Readiness Service 依赖的外部资产只读核验接口。"""

    def probe(self, url: str) -> ExternalAssetProbeResult:
        """核验公开入口是否可以在不登录的情况下读取。"""
        ...


class PublicExternalAssetProbe:
    """仅允许访问固定公共资产域名的轻量 HTTP Probe。"""

    redirect_statuses = {301, 302, 303, 307, 308}

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_response_bytes: int = 750_000,
        max_attempts: int = 3,
        cache_ttl_seconds: float = 300.0,
        proxy: str | None = None,
        max_redirects: int = 4,
    ) -> None:
        self._owns_client = client is None
        proxy_url = proxy if proxy is not None else self._configured_proxy()
        self.proxy_configured = proxy_url is not None
        self.client = client or outbound_client(
            headers={"User-Agent": "ResearchOps-Agent/0.1"},
            timeout=httpx.Timeout(15.0, connect=6.0),
            follow_redirects=False,
            # An explicit ResearchOps proxy remains authoritative. When none is
            # configured, allow httpx to reuse the host's standard HTTPS proxy
            # settings instead of forcing a direct connection that may be
            # unable to reach Google Drive on the user's network.
            trust_env=proxy_url is None,
            proxy=proxy_url,
        )
        self.max_response_bytes = max_response_bytes
        self.max_attempts = max(1, max_attempts)
        self.cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self.max_redirects = max(0, max_redirects)
        self._success_cache: dict[str, tuple[float, ExternalAssetProbeResult]] = {}
        self._cache_lock = threading.Lock()

    def close(self) -> None:
        """关闭由 Probe 自己创建的 HTTP Client。"""

        if self._owns_client:
            self.client.close()

    def probe(self, url: str) -> ExternalAssetProbeResult:
        """检查允许域名上的公开页面是否可直接读取。"""

        parsed = urlparse(url)
        is_drive = parsed.hostname == "drive.google.com"
        resource_key = self._drive_resource_key(parsed.path) if is_drive else None
        if not self._is_allowed_url(url) or (is_drive and resource_key is None):
            return ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=None,
                accessible=False,
                detail="External asset host is outside the read-only allowlist.",
                state="verified_inaccessible",
            )

        cached = self._cached_success(url)
        if cached is not None:
            return cached

        body: bytearray | None = None
        final_url: str | None = None
        current_url = url
        for redirect_count in range(self.max_redirects + 1):
            if not self._is_allowed_url(current_url):
                return ExternalAssetProbeResult(
                    source_url=redact_sensitive_url(url),
                    final_url=redact_sensitive_url(current_url),
                    accessible=False,
                    detail="External asset redirect was blocked before leaving the allowlist.",
                    state="verified_inaccessible",
                )
            redirected = False
            for attempt in range(1, self.max_attempts + 1):
                try:
                    with self.client.stream("GET", current_url) as response:
                        if response.status_code in self.redirect_statuses:
                            location = response.headers.get("location")
                            if not location or redirect_count >= self.max_redirects:
                                return ExternalAssetProbeResult(
                                    source_url=redact_sensitive_url(url),
                                    final_url=redact_sensitive_url(response.url),
                                    accessible=False,
                                    detail=(
                                        "External asset redirect chain could not be resolved safely."
                                    ),
                                    state="acquisition_failure",
                                )
                            current_url = urljoin(current_url, location)
                            redirected = True
                            break
                        response.raise_for_status()
                        body = bytearray()
                        for chunk in response.iter_bytes():
                            remaining = self.max_response_bytes - len(body)
                            if remaining <= 0:
                                break
                            body.extend(chunk[:remaining])
                        final_url = str(response.url)
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in {429, 500, 502, 503, 504}:
                        return ExternalAssetProbeResult(
                            source_url=redact_sensitive_url(url),
                            final_url=redact_sensitive_url(exc.response.url),
                            accessible=False,
                            detail=(
                                "External asset entry was reached but returned HTTP "
                                f"{exc.response.status_code}."
                            ),
                            state="verified_inaccessible",
                        )
                except httpx.RequestError:
                    pass
                if attempt < self.max_attempts:
                    time.sleep(0.2 * (2 ** (attempt - 1)))
            if redirected:
                continue
            break

        if body is None or final_url is None:
            return ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=None,
                accessible=False,
                detail=(
                    f"External asset acquisition failed after {self.max_attempts} attempts "
                    "for a transport or transient provider reason"
                    + (" while using the configured proxy." if self.proxy_configured else ".")
                ),
                state="acquisition_failure",
            )

        final_host = urlparse(final_url).hostname
        final_resource_key = self._drive_resource_key(urlparse(final_url).path)
        content = body.decode("utf-8", errors="replace").casefold()
        if final_host not in ALLOWED_ASSET_HOSTS:
            return ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                accessible=False,
                detail="External asset redirected outside the public asset host.",
                state="verified_inaccessible",
            )
        if not is_drive:
            result = ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                accessible=True,
                detail="Official release asset endpoint responded through the approved GitHub delivery path.",
                state="verified_public",
            )
            self._store_success(url, result)
            return result

        if any(marker in content for marker in INACCESSIBLE_MARKERS):
            return ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                accessible=False,
                detail="External asset page requires additional access approval.",
                state="verified_inaccessible",
            )

        if final_resource_key != resource_key:
            return ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                accessible=False,
                detail="The response did not preserve the requested Drive resource identity.",
                state="verified_inaccessible",
            )

        title_match = TITLE_PATTERN.search(content)
        title = re.sub(r"\s+", " ", title_match.group("title")).strip() if title_match else ""
        named_google_resource = bool(re.search(r"^.+\s+-\s+google(?:\s|$)", title, re.IGNORECASE))
        if not named_google_resource:
            return ExternalAssetProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                accessible=False,
                detail=(
                    "The requested Drive resource identity was preserved, but the response did "
                    "not expose a named public folder page."
                ),
                state="verified_inaccessible",
            )

        result = ExternalAssetProbeResult(
            source_url=redact_sensitive_url(url),
            final_url=redact_sensitive_url(final_url),
            accessible=True,
            detail="External asset page is publicly readable without an access prompt.",
            state="verified_public",
        )
        self._store_success(url, result)
        return result

    def _cached_success(self, url: str) -> ExternalAssetProbeResult | None:
        now = time.monotonic()
        with self._cache_lock:
            cached = self._success_cache.get(url)
            if cached is None or cached[0] <= now:
                self._success_cache.pop(url, None)
                return None
            result = cached[1]
        return ExternalAssetProbeResult(
            source_url=result.source_url,
            final_url=result.final_url,
            accessible=True,
            detail="Recent successful public access verification reused from the short-term cache.",
            state="verified_public",
        )

    def _store_success(self, url: str, result: ExternalAssetProbeResult) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        with self._cache_lock:
            self._success_cache[url] = (
                time.monotonic() + self.cache_ttl_seconds,
                result,
            )

    @staticmethod
    def _configured_proxy() -> str | None:
        """Reuse the explicit model proxy before falling back to the legacy alias."""
        return (
            os.getenv("RESEARCHOPS_EXTERNAL_ASSET_HTTPS_PROXY")
            or os.getenv("RESEARCHOPS_LLM_HTTPS_PROXY")
            or os.getenv("RESEARCHOPS_HTTPS_PROXY")
            or None
        )

    @staticmethod
    def _is_allowed_url(url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_ASSET_HOSTS
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )

    @staticmethod
    def _drive_resource_key(path: str) -> tuple[str, str] | None:
        parts = [part for part in path.split("/") if part]
        for marker in ("folders", "d"):
            if marker in parts:
                index = parts.index(marker)
                if index + 1 < len(parts) and parts[index + 1]:
                    return marker, parts[index + 1]
        return None
