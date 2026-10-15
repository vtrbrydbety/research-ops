"""将不同形式的目标输入规范化为统一 ResolvedTarget。"""

import difflib
import os
import re
import threading
import time
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlparse

import httpx

from researchops.core.outbound import outbound_client
from researchops.schemas import (
    ResolvedTarget,
    TargetCandidate,
    TargetResolutionRequest,
    TargetResolutionResponse,
)

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
ARXIV_PATTERN = re.compile(
    r"^(?:arxiv:)?(?P<identifier>(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PaperMetadata:
    """公开书目检索返回的最小论文身份。"""

    title: str
    description: str
    doi: str | None = None
    arxiv_id: str | None = None


class PaperMetadataSearch(Protocol):
    """论文标题只读候选检索接口。"""

    def search(self, title: str) -> tuple[PaperMetadata, ...]: ...


class PaperMetadataSearchError(RuntimeError):
    """公开书目元数据端点发生技术失败。"""


class CrossrefPaperMetadataSearch:
    """通过固定 Crossref REST 端点查询公开 DOI 元数据。"""

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

    def search(self, title: str) -> tuple[PaperMetadata, ...]:
        try:
            response = _get_metadata_response(
                self.client,
                "https://api.crossref.org/works",
                params={
                    "query.title": title,
                    "rows": "2",
                    "select": "DOI,title,author,published-print,published-online",
                },
                max_attempts=self.max_attempts,
            )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise PaperMetadataSearchError("Crossref metadata request failed") from exc

        message = payload.get("message") if isinstance(payload, dict) else None
        items = message.get("items") if isinstance(message, dict) else None
        if not isinstance(items, list):
            return ()

        results: list[PaperMetadata] = []
        seen_dois: set[str] = set()
        for item in items[:2]:
            if not isinstance(item, dict):
                continue
            doi = item.get("DOI")
            titles = item.get("title")
            candidate_title = titles[0] if isinstance(titles, list) and titles else None
            if not isinstance(doi, str) or not isinstance(candidate_title, str):
                continue
            if not _titles_are_relevant(title, candidate_title):
                continue
            normalized_doi = doi.strip().lower()
            if not normalized_doi or normalized_doi in seen_dois:
                continue
            seen_dois.add(normalized_doi)
            results.append(
                PaperMetadata(
                    title=" ".join(candidate_title.split())[:500],
                    doi=normalized_doi[:500],
                    description=self._description(item)[:1000],
                )
            )
        return tuple(results)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    @staticmethod
    def _description(item: dict[str, object]) -> str:
        authors = item.get("author")
        author_names: list[str] = []
        if isinstance(authors, list):
            for author in authors[:3]:
                if not isinstance(author, dict):
                    continue
                name = " ".join(
                    str(author.get(key, "")).strip() for key in ("given", "family")
                ).strip()
                if name:
                    author_names.append(name)

        year = None
        for key in ("published-print", "published-online"):
            date = item.get(key)
            parts = date.get("date-parts") if isinstance(date, dict) else None
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                year = parts[0][0]
                break
        author_text = ", ".join(author_names) if author_names else "Authors unavailable"
        year_text = str(year) if year is not None else "Year unavailable"
        return f"{author_text} · {year_text} · Crossref DOI metadata"


class ArxivPaperMetadataSearch:
    """通过 arXiv Atom API 查询高相关论文标题候选。"""

    atom_namespace = {"atom": "http://www.w3.org/2005/Atom"}
    title_stop_words = frozenset(
        {
            "a",
            "an",
            "and",
            "for",
            "from",
            "in",
            "of",
            "on",
            "the",
            "to",
            "via",
            "with",
        }
    )

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

    def search(self, title: str) -> tuple[PaperMetadata, ...]:
        try:
            response = _get_metadata_response(
                self.client,
                "https://export.arxiv.org/api/query",
                params={
                    "search_query": self._title_query(title),
                    "start": "0",
                    "max_results": "5",
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                },
                max_attempts=self.max_attempts,
            )
            root = ET.fromstring(response.content)
        except (httpx.HTTPError, ET.ParseError) as exc:
            raise PaperMetadataSearchError("arXiv metadata request failed") from exc

        results: list[PaperMetadata] = []
        for entry in root.findall("atom:entry", self.atom_namespace):
            candidate_title = self._text(entry, "atom:title")
            entry_url = self._text(entry, "atom:id")
            identifier = re.sub(r"v\d+$", "", entry_url.rsplit("/", 1)[-1])
            if (
                not candidate_title
                or not identifier
                or not _titles_are_relevant(
                    title,
                    candidate_title,
                )
            ):
                continue
            authors = [
                self._text(author, "atom:name")
                for author in entry.findall("atom:author", self.atom_namespace)[:3]
            ]
            published = self._text(entry, "atom:published")
            year = published[:4] if len(published) >= 4 else "Year unavailable"
            author_text = ", ".join(author for author in authors if author) or "Authors unavailable"
            results.append(
                PaperMetadata(
                    title=candidate_title[:500],
                    arxiv_id=identifier,
                    description=f"{author_text} · {year} · arXiv metadata"[:1000],
                )
            )
        return tuple(results)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    @classmethod
    def _text(cls, element: ET.Element, path: str) -> str:
        child = element.find(path, cls.atom_namespace)
        return " ".join(child.text.split()) if child is not None and child.text else ""

    @classmethod
    def _title_query(cls, title: str) -> str:
        """Build an arXiv-compatible token query; quoted full titles return false empty feeds."""

        folded = unicodedata.normalize("NFKD", title).casefold()
        tokens = [
            token for token in re.findall(r"[a-z0-9]+", folded) if token not in cls.title_stop_words
        ]
        distinctive_tokens = tuple(dict.fromkeys(tokens))[:8]
        if not distinctive_tokens:
            distinctive_tokens = tuple(dict.fromkeys(re.findall(r"[a-z0-9]+", folded)))[:8]
        return " AND ".join(f"ti:{token}" for token in distinctive_tokens)


def _get_metadata_response(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, str],
    max_attempts: int,
) -> httpx.Response:
    """Retry only transient transport/server failures on fixed metadata endpoints."""

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


class PublicPaperMetadataSearch:
    """优先使用 DOI 元数据，Crossref 无高相关结果时回退到 arXiv。"""

    def __init__(
        self,
        crossref: PaperMetadataSearch | None = None,
        arxiv: PaperMetadataSearch | None = None,
    ) -> None:
        self.crossref = crossref or CrossrefPaperMetadataSearch()
        self.arxiv = arxiv or ArxivPaperMetadataSearch()

    def search(self, title: str) -> tuple[PaperMetadata, ...]:
        crossref_failed = False
        try:
            crossref_results = self.crossref.search(title)
        except PaperMetadataSearchError:
            crossref_failed = True
            crossref_results = ()
        if crossref_results:
            return crossref_results
        try:
            return self.arxiv.search(title)
        except PaperMetadataSearchError:
            if crossref_failed:
                raise PaperMetadataSearchError("Public paper metadata requests failed") from None
            raise


def _titles_are_relevant(query: str, candidate: str) -> bool:
    """拒绝仅共享少量主题词的候选，避免强迫用户在错误论文间选择。"""

    def normalize(value: str) -> str:
        folded = unicodedata.normalize("NFKD", value).casefold()
        return " ".join(re.findall(r"[a-z0-9]+", folded))

    query_normalized = normalize(query)
    candidate_normalized = normalize(candidate)
    if not query_normalized or not candidate_normalized:
        return False
    if query_normalized == candidate_normalized:
        return True
    query_tokens = set(query_normalized.split())
    candidate_tokens = set(candidate_normalized.split())
    coverage = len(query_tokens & candidate_tokens) / len(query_tokens)
    similarity = difflib.SequenceMatcher(None, query_normalized, candidate_normalized).ratio()
    return coverage >= 0.75 and similarity >= 0.72


class TargetResolutionService:
    """规范化确定性标识，并通过公开元数据检索论文标题候选。"""

    def __init__(
        self,
        paper_metadata_search: PaperMetadataSearch | None = None,
        *,
        candidate_cache_seconds: int = 300,
    ) -> None:
        self.paper_metadata_search = paper_metadata_search or PublicPaperMetadataSearch()
        self.candidate_cache_seconds = candidate_cache_seconds
        self._paper_candidate_cache: dict[str, tuple[float, tuple[PaperMetadata, ...]]] = {}
        self._cache_lock = threading.Lock()

    def resolve(self, request: TargetResolutionRequest) -> TargetResolutionResponse:
        """根据入口类型选择对应的规范化策略。"""

        entry = request.target_entry.strip()
        if request.target_type == "repository":
            return self._resolve_repository(entry)
        if request.target_type == "project_page":
            return self._resolve_project_page(entry)
        if request.target_type == "doi":
            return self._resolve_doi(entry)
        if request.target_type == "arxiv":
            return self._resolve_arxiv(entry)
        return self._resolve_paper_title(entry)

    def _resolve_repository(self, entry: str) -> TargetResolutionResponse:
        parsed = urlparse(entry)
        path_parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"github.com", "www.github.com"}
            or len(path_parts) < 2
        ):
            return self._unresolved(entry)

        owner, repository = path_parts[:2]
        repository = repository.removesuffix(".git")
        canonical_url = f"https://github.com/{owner}/{repository}"
        return self._identified(
            entry=entry,
            target_type="repository",
            display_name=f"{owner}/{repository}",
            canonical_id=f"github:{owner}/{repository}",
            canonical_url=canonical_url,
            method="direct_url",
        )

    def _resolve_project_page(self, entry: str) -> TargetResolutionResponse:
        parsed = urlparse(entry)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return self._unresolved(entry)

        clean_path = parsed.path.rstrip("/")
        canonical_url = f"{parsed.scheme}://{parsed.netloc}{clean_path}"
        display_name = f"{parsed.hostname}{clean_path}" or entry
        return self._identified(
            entry=entry,
            target_type="project_page",
            display_name=display_name,
            canonical_id=f"project:{parsed.hostname}{clean_path}",
            canonical_url=canonical_url,
            method="direct_url",
        )

    def _resolve_doi(self, entry: str) -> TargetResolutionResponse:
        normalized = re.sub(
            r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
            "",
            entry,
            flags=re.IGNORECASE,
        ).strip()
        if not DOI_PATTERN.match(normalized):
            return self._unresolved(entry)

        return self._identified(
            entry=entry,
            target_type="doi",
            display_name=normalized,
            canonical_id=f"doi:{normalized.lower()}",
            canonical_url=f"https://doi.org/{normalized}",
            method="normalized_identifier",
        )

    def _resolve_arxiv(self, entry: str) -> TargetResolutionResponse:
        normalized = re.sub(
            r"^https?://arxiv\.org/(?:abs|pdf)/",
            "",
            entry,
            flags=re.IGNORECASE,
        ).removesuffix(".pdf")
        match = ARXIV_PATTERN.match(normalized.strip())
        if not match:
            return self._unresolved(entry)

        identifier = match.group("identifier")
        return self._identified(
            entry=entry,
            target_type="arxiv",
            display_name=f"arXiv:{identifier}",
            canonical_id=f"arxiv:{identifier.lower()}",
            canonical_url=f"https://arxiv.org/abs/{identifier}",
            method="normalized_identifier",
        )

    def _resolve_paper_title(self, entry: str) -> TargetResolutionResponse:
        """查询公开书目元数据，并在有歧义时要求用户确认。"""

        normalized_title = " ".join(entry.split())
        try:
            metadata = self._paper_metadata(normalized_title)
        except PaperMetadataSearchError:
            return self._unresolved(
                entry,
                data_mode="live_metadata",
                analysis_state="acquisition_failure",
            )
        candidates = [
            self._paper_candidate(entry, item, index) for index, item in enumerate(metadata)
        ]
        if len(candidates) == 1:
            return TargetResolutionResponse(
                status="identified",
                data_mode="live_metadata",
                source_entry=entry,
                resolved_target=candidates[0].resolved_target,
            )
        if not candidates:
            return self._unresolved(entry, data_mode="live_metadata")
        return TargetResolutionResponse(
            status="requires_confirmation",
            data_mode="live_metadata",
            source_entry=entry,
            candidates=candidates,
        )

    def _paper_metadata(self, normalized_title: str) -> tuple[PaperMetadata, ...]:
        key = normalized_title.casefold()
        now = time.monotonic()
        with self._cache_lock:
            cached = self._paper_candidate_cache.get(key)
            if cached is not None and cached[0] > now:
                return cached[1]

        metadata = self.paper_metadata_search.search(normalized_title)
        if metadata and self.candidate_cache_seconds > 0:
            with self._cache_lock:
                self._paper_candidate_cache[key] = (
                    now + self.candidate_cache_seconds,
                    metadata,
                )
        return metadata

    @staticmethod
    def _paper_candidate(entry: str, metadata: PaperMetadata, index: int) -> TargetCandidate:
        if metadata.doi:
            canonical_id = f"doi:{metadata.doi}"
            canonical_url = f"https://doi.org/{metadata.doi}"
            source = f"crossref-{index + 1}-{metadata.doi}"
        elif metadata.arxiv_id:
            canonical_id = f"arxiv:{metadata.arxiv_id}"
            canonical_url = f"https://arxiv.org/abs/{metadata.arxiv_id}"
            source = f"arxiv-{index + 1}-{metadata.arxiv_id}"
        else:
            raise PaperMetadataSearchError("Paper metadata candidate has no stable identifier")
        return TargetCandidate(
            candidate_id=source[:100],
            label=metadata.title,
            description=metadata.description,
            resolved_target=ResolvedTarget(
                target_type="paper_title",
                source_entry=entry,
                display_name=metadata.title,
                canonical_id=canonical_id,
                canonical_url=canonical_url,
                resolution_method="title_candidate",
            ),
        )

    @staticmethod
    def _identified(
        *,
        entry: str,
        target_type: str,
        display_name: str,
        canonical_id: str,
        canonical_url: str,
        method: str,
    ) -> TargetResolutionResponse:
        return TargetResolutionResponse(
            status="identified",
            data_mode="deterministic",
            source_entry=entry,
            resolved_target=ResolvedTarget(
                target_type=target_type,
                source_entry=entry,
                display_name=display_name,
                canonical_id=canonical_id,
                canonical_url=canonical_url,
                resolution_method=method,
            ),
        )

    @staticmethod
    def _unresolved(
        entry: str,
        *,
        data_mode: Literal["deterministic", "live_metadata"] = "deterministic",
        analysis_state: Literal["acquisition_failure"] | None = None,
    ) -> TargetResolutionResponse:
        return TargetResolutionResponse(
            status="unresolved",
            data_mode=data_mode,
            source_entry=entry,
            analysis_state=analysis_state,
        )
