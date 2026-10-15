"""通过公开书目端点采集论文的最小只读材料。"""

import html
import ipaddress
import os
import re
import socket
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol
from urllib.parse import quote, urljoin, urlparse

import httpx

from researchops.core.outbound import outbound_client
from researchops.schemas import ResolvedTarget

GITHUB_REPOSITORY_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PaperMaterials:
    """Readiness 判断可重新定位的最小论文材料。"""

    title: str
    identifier: str
    source_url: str
    publisher: str
    abstract: str | None
    fetched_at: datetime
    material_type: Literal["Paper", "Project Page"] = "Paper"
    repository_urls: tuple[str, ...] = ()


class PaperMaterialCollectionError(RuntimeError):
    """论文元数据无法通过公开端点取得。"""


class PaperMaterialCollector(Protocol):
    """论文材料采集接口。"""

    def collect(self, target: ResolvedTarget) -> PaperMaterials: ...


class CrossrefPaperMaterialCollector:
    """通过固定 Crossref REST 端点读取 DOI 元数据，不下载论文附件。"""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_attempts: int = 3,
        proxy: str | None = None,
    ) -> None:
        self._owns_client = client is None
        proxy_url = proxy if proxy is not None else os.getenv("RESEARCHOPS_HTTPS_PROXY")
        self.client = client or outbound_client(
            base_url="https://api.crossref.org",
            headers={"User-Agent": "ResearchOps-Agent/0.1 (mailto:researchops@example.invalid)"},
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
            proxy=proxy_url,
        )
        self.max_attempts = max(1, max_attempts)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def collect(self, target: ResolvedTarget) -> PaperMaterials:
        doi = self._target_doi(target)
        if doi is None:
            raise PaperMaterialCollectionError("Resolved paper target does not contain a DOI")

        try:
            response = _get_metadata_response(
                self.client,
                f"https://api.crossref.org/works/{quote(doi, safe='')}",
                max_attempts=self.max_attempts,
            )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaperMaterialCollectionError("Crossref paper metadata request failed") from exc

        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict):
            raise PaperMaterialCollectionError("Crossref returned no paper metadata record")
        titles = message.get("title")
        title = titles[0] if isinstance(titles, list) and titles else None
        if not isinstance(title, str) or not title.strip():
            raise PaperMaterialCollectionError("Crossref paper metadata has no usable title")

        abstract = message.get("abstract")
        clean_abstract = self._clean_markup(abstract) if isinstance(abstract, str) else None
        publisher = message.get("publisher")
        return PaperMaterials(
            title=" ".join(title.split())[:500],
            identifier=f"doi:{doi}",
            source_url=f"https://doi.org/{doi}",
            publisher=(publisher.strip()[:500] if isinstance(publisher, str) else "Crossref"),
            abstract=clean_abstract[:10_000] if clean_abstract else None,
            fetched_at=datetime.now(UTC),
            repository_urls=self._repository_urls(abstract if isinstance(abstract, str) else ""),
        )

    @staticmethod
    def _target_doi(target: ResolvedTarget) -> str | None:
        if target.canonical_id.casefold().startswith("doi:"):
            return target.canonical_id[4:].strip().lower() or None
        return None

    @staticmethod
    def _clean_markup(value: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", value)
        return " ".join(without_tags.split())

    @staticmethod
    def _repository_urls(value: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(GITHUB_REPOSITORY_URL_PATTERN.findall(value)))


class ArxivPaperMaterialCollector:
    """通过固定 arXiv Atom API 读取标题与摘要，不下载 PDF。"""

    atom_namespace = {"atom": "http://www.w3.org/2005/Atom"}

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_attempts: int = 3,
        proxy: str | None = None,
    ) -> None:
        self._owns_client = client is None
        proxy_url = proxy if proxy is not None else os.getenv("RESEARCHOPS_HTTPS_PROXY")
        self.client = client or outbound_client(
            headers={"User-Agent": "ResearchOps-Agent/0.1"},
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
            proxy=proxy_url,
        )
        self.max_attempts = max(1, max_attempts)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def collect(self, target: ResolvedTarget) -> PaperMaterials:
        identifier = self._target_identifier(target)
        if identifier is None:
            raise PaperMaterialCollectionError("Resolved paper target does not contain an arXiv ID")

        try:
            response = _get_metadata_response(
                self.client,
                "https://export.arxiv.org/api/query",
                params={"id_list": identifier, "max_results": "1"},
                max_attempts=self.max_attempts,
            )
            root = ET.fromstring(response.content)
        except (httpx.HTTPError, ET.ParseError) as exc:
            raise PaperMaterialCollectionError("arXiv paper metadata request failed") from exc

        entry = root.find("atom:entry", self.atom_namespace)
        if entry is None:
            raise PaperMaterialCollectionError("arXiv returned no paper metadata record")
        returned_url = self._element_text(entry, "atom:id")
        title = self._element_text(entry, "atom:title")
        abstract = self._element_text(entry, "atom:summary")
        returned_id = returned_url.rsplit("/", 1)[-1] if returned_url else ""
        if not title or self._base_identifier(returned_id.casefold()) != self._base_identifier(
            identifier.casefold()
        ):
            raise PaperMaterialCollectionError("arXiv response did not match the requested paper")

        return PaperMaterials(
            title=title[:500],
            identifier=f"arxiv:{identifier.lower()}",
            source_url=f"https://arxiv.org/abs/{identifier}",
            publisher="arXiv",
            abstract=abstract[:10_000] if abstract else None,
            fetched_at=datetime.now(UTC),
            repository_urls=CrossrefPaperMaterialCollector._repository_urls(abstract),
        )

    @staticmethod
    def _target_identifier(target: ResolvedTarget) -> str | None:
        if target.canonical_id.casefold().startswith("arxiv:"):
            return target.canonical_id[6:].strip() or None
        return None

    @classmethod
    def _element_text(cls, entry: ET.Element, path: str) -> str:
        element = entry.find(path, cls.atom_namespace)
        return " ".join(element.text.split()) if element is not None and element.text else ""

    @staticmethod
    def _base_identifier(identifier: str) -> str:
        return re.sub(r"v\d+$", "", identifier)


def _get_metadata_response(
    client: httpx.Client,
    url: str,
    *,
    max_attempts: int,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    """Retry transient failures while keeping metadata requests on fixed endpoints."""

    last_error: httpx.HTTPError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504}:
                raise
            last_error = exc
        except httpx.TransportError as exc:
            last_error = exc
        if attempt == max_attempts:
            break
    if last_error is None:  # pragma: no cover - defensive invariant
        raise RuntimeError("metadata request exhausted without a response")
    raise last_error


class PublicPaperMaterialCollector:
    """按规范化标识选择 Crossref 或 arXiv 公开元数据适配器。"""

    def __init__(
        self,
        crossref: PaperMaterialCollector | None = None,
        arxiv: PaperMaterialCollector | None = None,
        project_page: PaperMaterialCollector | None = None,
    ) -> None:
        self.crossref = crossref or CrossrefPaperMaterialCollector()
        self.arxiv = arxiv or ArxivPaperMaterialCollector()
        self.project_page = project_page or ProjectPageMaterialCollector()

    def collect(self, target: ResolvedTarget) -> PaperMaterials:
        if target.canonical_id.casefold().startswith("arxiv:"):
            return self.arxiv.collect(target)
        if target.target_type == "project_page":
            return self.project_page.collect(target)
        return self.crossref.collect(target)

    def close(self) -> None:
        """Close owned/default child collectors when used as a one-shot adapter."""
        for collector in (self.crossref, self.arxiv, self.project_page):
            close = getattr(collector, "close", None)
            if callable(close):
                close()


class ProjectPageMaterialCollector:
    """有界读取公网 Project Page 的标题和可见文本，不执行页面脚本。"""

    redirect_statuses = {301, 302, 303, 307, 308}

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_response_bytes: int = 750_000,
        max_redirects: int = 3,
    ) -> None:
        self._owns_client = client is None
        self.client = client or outbound_client(
            headers={"User-Agent": "ResearchOps-Agent/0.1"},
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
        )
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def collect(self, target: ResolvedTarget) -> PaperMaterials:
        if target.canonical_url is None:
            raise PaperMaterialCollectionError("Project Page target has no canonical URL")
        current_url = str(target.canonical_url)

        for redirect_count in range(self.max_redirects + 1):
            self._validate_public_url(current_url)
            try:
                with self.client.stream("GET", current_url) as response:
                    if response.status_code in self.redirect_statuses:
                        location = response.headers.get("location")
                        if not location or redirect_count >= self.max_redirects:
                            raise PaperMaterialCollectionError(
                                "Project Page redirect chain could not be resolved safely"
                            )
                        current_url = urljoin(current_url, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").casefold()
                    if not any(kind in content_type for kind in ("text/html", "text/plain")):
                        raise PaperMaterialCollectionError(
                            "Project Page did not return supported text content"
                        )
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        remaining = self.max_response_bytes - len(body)
                        if remaining <= 0:
                            break
                        body.extend(chunk[:remaining])
                    final_url = str(response.url)
            except httpx.HTTPError as exc:
                raise PaperMaterialCollectionError("Project Page request failed") from exc
            break
        else:  # pragma: no cover - loop exits through return, break, or explicit error
            raise PaperMaterialCollectionError("Project Page redirect limit exceeded")

        decoded = body.decode("utf-8", errors="replace")
        title_match = re.search(r"<title[^>]*>(.*?)</title>", decoded, re.I | re.S)
        title = self._clean_html(title_match.group(1)) if title_match else target.display_name
        visible_text = self._clean_html(decoded)
        if not visible_text:
            raise PaperMaterialCollectionError("Project Page contained no readable text")
        hostname = urlparse(final_url).hostname or "Project Page"
        return PaperMaterials(
            title=title[:500],
            identifier=target.canonical_id,
            source_url=final_url,
            publisher=hostname,
            abstract=visible_text[:10_000],
            fetched_at=datetime.now(UTC),
            material_type="Project Page",
            repository_urls=CrossrefPaperMaterialCollector._repository_urls(decoded),
        )

    @staticmethod
    def _clean_html(value: str) -> str:
        without_scripts = re.sub(
            r"<(script|style)\b[^>]*>.*?</\1>",
            " ",
            value,
            flags=re.I | re.S,
        )
        return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", without_scripts)).split())

    @staticmethod
    def _validate_public_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise PaperMaterialCollectionError("Project Page URL is not HTTP/HTTPS")
        if parsed.port not in {None, 80, 443}:
            raise PaperMaterialCollectionError("Project Page uses a non-standard network port")
        try:
            addresses = {
                result[4][0]
                for result in socket.getaddrinfo(
                    parsed.hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        except socket.gaierror as exc:
            raise PaperMaterialCollectionError(
                "Project Page hostname could not be resolved"
            ) from exc
        if not addresses or any(
            not ipaddress.ip_address(address).is_global for address in addresses
        ):
            raise PaperMaterialCollectionError(
                "Project Page hostname is not a public Internet host"
            )
