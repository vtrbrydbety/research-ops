"""Policy-controlled deterministic execution of AI-requested research tools."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from researchops.core.access_context import check_operation, current_access
from researchops.core.outbound import outbound_client
from researchops.core.security import redact_sensitive_text
from researchops.schemas import (
    CollectedMaterial,
    MaterialBundle,
    MaterialSource,
    ResearchToolExecutionResult,
    ResearchToolFailureCode,
    ResearchToolName,
    ResolvedTarget,
    TargetResolutionRequest,
    ToolRequest,
    ToolRequestExecutionResult,
)
from researchops.services.checkpoint_acquisition import OfficialCheckpointAcquisitionPolicy
from researchops.services.data_access import DatasetAccessProbe, PublicDatasetAccessProbe
from researchops.services.environment_facts import EnvironmentFactService
from researchops.services.external_assets import ExternalAssetProbe, PublicExternalAssetProbe
from researchops.services.huggingface_materials import (
    HuggingFaceMaterialCollector,
    PublicHuggingFaceMaterialCollector,
)
from researchops.services.material_context import MaterialBundleBuilder
from researchops.services.paper_materials import (
    PaperMaterialCollectionError,
    PaperMaterialCollector,
    ProjectPageMaterialCollector,
    PublicPaperMaterialCollector,
)
from researchops.services.repository_materials import (
    GitHubRepositoryMaterialCollector,
    RepositoryMaterialCollector,
)
from researchops.services.target_resolution import (
    ARXIV_PATTERN,
    DOI_PATTERN,
    PaperMetadata,
    TargetResolutionService,
)


class ResearchToolExecutionError(RuntimeError):
    """A deterministic connector could not complete its bounded read."""


class ResearchToolArgumentError(ResearchToolExecutionError):
    """A model-proposed tool argument does not satisfy the executable contract."""


@dataclass(frozen=True, slots=True)
class PublicSearchHit:
    """One bounded result returned by a configured read-only search connector."""

    title: str
    url: str
    snippet: str


class WebSearchConnector(Protocol):
    """Configured public-web search boundary; the executor never scrapes ad-hoc engines."""

    def search(self, query: str) -> tuple[PublicSearchHit, ...]: ...


class GitHubSearchConnector(Protocol):
    """Read-only GitHub repository search boundary."""

    def search(self, query: str) -> tuple[PublicSearchHit, ...]: ...


class _NoopPaperMetadataSearch:
    """Avoid constructing network search clients for deterministic direct-ID resolution."""

    def search(
        self, title: str
    ) -> tuple[PaperMetadata, ...]:  # pragma: no cover - never called here
        return ()


class GitHubRepositorySearch:
    """Bounded repository search through GitHub's fixed REST API endpoint."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_results: int = 5,
        github_token: str | None = None,
    ) -> None:
        self._owns_client = client is None
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ResearchOps-Agent/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = github_token if github_token is not None else os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = client or outbound_client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
            proxy=os.getenv("RESEARCHOPS_HTTPS_PROXY") or None,
        )
        self.max_results = min(max(1, max_results), 10)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def search(self, query: str) -> tuple[PublicSearchHit, ...]:
        try:
            response = self.client.get(
                "/search/repositories",
                params={"q": query[:1000], "per_page": str(self.max_results)},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ResearchToolExecutionError("GitHub repository search failed") from exc

        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise ResearchToolExecutionError("GitHub repository search returned no result list")
        results: list[PublicSearchHit] = []
        for item in items[: self.max_results]:
            if not isinstance(item, dict):
                continue
            full_name = item.get("full_name")
            html_url = item.get("html_url")
            description = item.get("description")
            if not isinstance(full_name, str) or not isinstance(html_url, str):
                continue
            parsed = urlparse(html_url)
            if parsed.scheme != "https" or parsed.hostname != "github.com":
                continue
            results.append(
                PublicSearchHit(
                    title=full_name[:500],
                    url=html_url[:2000],
                    snippet=(
                        description[:1000] if isinstance(description, str) else "No description"
                    ),
                )
            )
        return tuple(results)


class DeterministicResearchToolExecutor:
    """Authorize, run, bound, and audit tool requests without granting tools to AI."""

    def __init__(
        self,
        *,
        repository_collector: RepositoryMaterialCollector | None = None,
        paper_collector: PaperMaterialCollector | None = None,
        project_page_collector: PaperMaterialCollector | None = None,
        dataset_probe: DatasetAccessProbe | None = None,
        checkpoint_probe: ExternalAssetProbe | None = None,
        environment_service: EnvironmentFactService | None = None,
        github_search: GitHubSearchConnector | None = None,
        web_search: WebSearchConnector | None = None,
        huggingface_collector: HuggingFaceMaterialCollector | None = None,
        bundle_builder: MaterialBundleBuilder | None = None,
        checkpoint_acquisition_policy: OfficialCheckpointAcquisitionPolicy | None = None,
        allowed_tools: set[ResearchToolName] | None = None,
    ) -> None:
        # Network-capable defaults are created only when their specific request is
        # executed. Constructing an executor must not itself acquire resources.
        self.repository_collector = repository_collector
        self.paper_collector = paper_collector
        self.project_page_collector = project_page_collector
        self.dataset_probe = dataset_probe
        self.checkpoint_probe = checkpoint_probe
        self.environment_service = environment_service
        self.github_search = github_search
        self.web_search = web_search
        self.huggingface_collector = huggingface_collector
        self.bundle_builder = bundle_builder or MaterialBundleBuilder()
        self.checkpoint_acquisition_policy = (
            checkpoint_acquisition_policy or OfficialCheckpointAcquisitionPolicy()
        )
        self.allowed_tools = (
            {
                "search_web",
                "fetch_web_page",
                "search_github",
                "read_github_repository",
                "read_github_file",
                "read_huggingface_card",
                "fetch_paper",
                "probe_dataset_access",
                "probe_checkpoint_access",
                "inspect_local_environment",
            }
            if allowed_tools is None
            else set(allowed_tools)
        )

    def execute(
        self,
        requests: list[ToolRequest],
        bundle: MaterialBundle,
        *,
        local_environment_authorized: bool = False,
    ) -> ResearchToolExecutionResult:
        """Execute each request once and return an enriched bundle plus per-request audit."""
        check_operation()
        if current_access.get():
            local_environment_authorized = False
        sources = list(bundle.sources)
        known_source_ids = {source.source_id for source in sources}
        known_content_hashes = {source.content_sha256 for source in sources}
        new_source_ids: list[str] = []
        request_results: list[ToolRequestExecutionResult] = []

        ordered_requests, checkpoint_authorizations = self._ordered_requests(requests, bundle)
        official_release_verified = False
        for request in ordered_requests:
            started_at = datetime.now(UTC)
            checkpoint_authorization = checkpoint_authorizations.get(request.request_id)
            if checkpoint_authorization is not None:
                if checkpoint_authorization.kind == "denied":
                    request_results.append(
                        self._result(
                            request,
                            "denied",
                            checkpoint_authorization.detail,
                            started_at,
                            failure_code="policy_denied",
                        )
                    )
                    continue
                if checkpoint_authorization.kind == "readme_external" and official_release_verified:
                    request_results.append(
                        self._result(
                            request,
                            "skipped",
                            "Skipped: a prior official Release asset was verified publicly; README external fallback was not needed.",
                            started_at,
                            failure_code="not_needed",
                        )
                    )
                    continue
            if request.tool_name not in self.allowed_tools:
                request_results.append(
                    self._result(
                        request,
                        "denied",
                        "The requested tool is disabled by the executor policy.",
                        started_at,
                        failure_code="policy_denied",
                    )
                )
                continue
            if (
                request.tool_name == "read_huggingface_card"
                and not self._huggingface_card_is_declared(bundle, str(request.url))
            ):
                request_results.append(
                    self._result(
                        request,
                        "denied",
                        "Hugging Face card read denied: the exact public card URL is not present in the confirmed target or collected material.",
                        started_at,
                        failure_code="policy_denied",
                    )
                )
                continue
            if (
                request.tool_name == "inspect_local_environment"
                and not local_environment_authorized
            ):
                request_results.append(
                    self._result(
                        request,
                        "denied",
                        "Local environment inspection requires explicit current-user authorization.",
                        started_at,
                        failure_code="policy_denied",
                    )
                )
                continue
            if request.tool_name == "search_web" and self.web_search is None:
                request_results.append(
                    self._result(
                        request,
                        "not_configured",
                        "No audited public-web search provider is configured.",
                        started_at,
                        failure_code="provider_not_configured",
                    )
                )
                continue

            remaining_sources = 64 - len(sources)
            remaining_chars = 500_000 - sum(len(source.content) for source in sources)
            if remaining_sources <= 0 or remaining_chars <= 0:
                request_results.append(
                    self._result(
                        request,
                        "denied",
                        "The bounded MaterialBundle has no remaining source capacity.",
                        started_at,
                        failure_code="bounded_capacity_exhausted",
                    )
                )
                continue

            try:
                produced = self._execute_request(
                    request,
                    bundle,
                    remaining_sources=remaining_sources,
                    remaining_chars=remaining_chars,
                )
            except Exception as exc:
                failure_code = self._failure_code(exc)
                detail = redact_sensitive_text(
                    f"The deterministic tool request failed ({failure_code})."
                )
                request_results.append(
                    self._result(
                        request,
                        "failed",
                        detail,
                        started_at,
                        failure_code=failure_code,
                    )
                )
                continue

            accepted: list[MaterialSource] = []
            for source in produced:
                if (
                    source.source_id in known_source_ids
                    or source.content_sha256 in known_content_hashes
                ):
                    continue
                accepted.append(source)
                known_source_ids.add(source.source_id)
                known_content_hashes.add(source.content_sha256)
            sources.extend(accepted)
            accepted_ids = [source.source_id for source in accepted]
            new_source_ids.extend(accepted_ids)
            detail = (
                f"Deterministic read completed and added {len(accepted_ids)} bounded source(s)."
                if accepted_ids
                else "Deterministic read completed; all returned material was already present."
            )
            request_results.append(
                self._result(request, "succeeded", detail, started_at, accepted_ids)
            )
            if (
                checkpoint_authorization is not None
                and checkpoint_authorization.kind == "official_release"
                and self._checkpoint_probe_verified(produced)
            ):
                official_release_verified = True

        output_bundle = MaterialBundle(
            bundle_id=uuid4() if new_source_ids else bundle.bundle_id,
            target=bundle.target,
            assembled_at=datetime.now(UTC),
            sources=sources,
            human_review_context=(
                bundle.human_review_context.model_copy(deep=True)
                if bundle.human_review_context is not None
                else None
            ),
        )
        return ResearchToolExecutionResult(
            plan_id=uuid4(),
            input_bundle_id=bundle.bundle_id,
            output_bundle=output_bundle,
            input_source_ids=[source.source_id for source in bundle.sources],
            new_source_ids=new_source_ids,
            request_results=request_results,
        )

    def _ordered_requests(self, requests: list[ToolRequest], bundle: MaterialBundle):
        """Apply Rule-owned checkpoint authorization before connector invocation."""
        authorizations = {
            request.request_id: self.checkpoint_acquisition_policy.authorize(bundle, request)
            for request in requests
            if request.tool_name == "probe_checkpoint_access"
        }
        indexed = list(enumerate(requests))
        indexed.sort(
            key=lambda item: (
                1 if item[1].tool_name == "probe_checkpoint_access" else 0,
                authorizations[item[1].request_id].priority
                if item[1].tool_name == "probe_checkpoint_access"
                else 0,
                item[0],
            )
        )
        return [request for _, request in indexed], authorizations

    @staticmethod
    def _checkpoint_probe_verified(produced: list[MaterialSource]) -> bool:
        for source in produced:
            if source.material_type != "Checkpoint-Release":
                continue
            try:
                payload = json.loads(source.content)
            except json.JSONDecodeError:
                continue
            if payload.get("state") == "verified_public":
                return True
        return False

    def _execute_request(
        self,
        request: ToolRequest,
        bundle: MaterialBundle,
        *,
        remaining_sources: int,
        remaining_chars: int,
    ) -> list[MaterialSource]:
        builder = self._bounded_builder(remaining_sources, remaining_chars)
        if request.tool_name == "search_github":
            owned = self.github_search is None
            search = self.github_search or GitHubRepositorySearch()
            try:
                hits = search.search(request.query or "")
            finally:
                self._close_owned(search, owned)
            return self._search_material(builder, bundle, request, hits, "GitHub repository search")
        if request.tool_name == "search_web":
            if self.web_search is None:  # guarded in execute; defensive invariant
                raise ResearchToolExecutionError("public-web search is not configured")
            hits = self.web_search.search(request.query or "")
            return self._search_material(builder, bundle, request, hits, "Public web search")
        if request.tool_name == "read_github_repository":
            target = self._resolve_target("repository", str(request.url))
            owned = self.repository_collector is None
            collector = self.repository_collector or GitHubRepositoryMaterialCollector()
            try:
                materials = collector.collect(target)
            finally:
                self._close_owned(collector, owned)
            return list(builder.from_repository(bundle.target, materials).bundle.sources)
        if request.tool_name == "read_github_file":
            owned = self.repository_collector is None
            collector = self.repository_collector or GitHubRepositoryMaterialCollector()
            try:
                read_file_url = getattr(collector, "read_file_url", None)
                if not callable(read_file_url):
                    raise ResearchToolExecutionError(
                        "Configured repository collector cannot read an explicit GitHub file URL"
                    )
                material = read_file_url(str(request.url))
            finally:
                self._close_owned(collector, owned)
            if material is None:
                raise ResearchToolExecutionError("GitHub file is not readable bounded text")
            return self._github_file_material(builder, bundle, material)
        if request.tool_name == "read_huggingface_card":
            owned = self.huggingface_collector is None
            collector = self.huggingface_collector or PublicHuggingFaceMaterialCollector()
            try:
                material = collector.collect(str(request.url))
            finally:
                self._close_owned(collector, owned)
            return list(builder.build(bundle.target, [material]).bundle.sources)
        if request.tool_name == "fetch_web_page":
            target = self._resolve_target("project_page", str(request.url))
            owned = self.project_page_collector is None
            collector = self.project_page_collector or ProjectPageMaterialCollector()
            try:
                materials = collector.collect(target)
            finally:
                self._close_owned(collector, owned)
            return list(builder.from_paper(bundle.target, materials).bundle.sources)
        if request.tool_name == "fetch_paper":
            target_type, entry = self._paper_target(request.identifier or "")
            target = self._resolve_target(target_type, entry)
            owned = self.paper_collector is None
            collector = self.paper_collector or PublicPaperMaterialCollector()
            try:
                materials = collector.collect(target)
            finally:
                self._close_owned(collector, owned)
            return list(builder.from_paper(bundle.target, materials).bundle.sources)
        if request.tool_name == "probe_dataset_access":
            owned = self.dataset_probe is None
            probe = self.dataset_probe or PublicDatasetAccessProbe()
            try:
                result = probe.probe(str(request.url))
            finally:
                self._close_owned(probe, owned)
            return self._probe_material(
                builder,
                bundle,
                request,
                "Dataset Page",
                result.source_url,
                asdict(result),
            )
        if request.tool_name == "probe_checkpoint_access":
            owned = self.checkpoint_probe is None
            probe = self.checkpoint_probe or PublicExternalAssetProbe()
            try:
                result = probe.probe(str(request.url))
            finally:
                self._close_owned(probe, owned)
            return self._probe_material(
                builder,
                bundle,
                request,
                "Checkpoint-Release",
                result.source_url,
                asdict(result),
            )
        if request.tool_name == "inspect_local_environment":
            service = self.environment_service or EnvironmentFactService()
            facts = service.acquire(
                "readonly",
                authorized=True,
                supplied_text=None,
            )
            if facts is None:
                raise ResearchToolExecutionError(
                    "authorized environment inspection returned no facts"
                )
            return list(builder.from_environment(bundle.target, facts).bundle.sources)
        raise ResearchToolExecutionError("tool is not implemented")  # pragma: no cover

    @staticmethod
    def _close_owned(instance: object, owned: bool) -> None:
        if not owned:
            return
        close = getattr(instance, "close", None)
        if callable(close):
            close()

    def _bounded_builder(
        self,
        remaining_sources: int,
        remaining_chars: int,
    ) -> MaterialBundleBuilder:
        return MaterialBundleBuilder(
            max_total_chars=min(self.bundle_builder.max_total_chars, remaining_chars),
            max_source_chars=min(self.bundle_builder.max_source_chars, remaining_chars),
            max_sources=min(self.bundle_builder.max_sources, remaining_sources),
            max_candidate_chars=self.bundle_builder.max_candidate_chars,
        )

    @staticmethod
    def _huggingface_card_is_declared(bundle: MaterialBundle, url: str) -> bool:
        """Require deterministic provenance before a third-party card read."""

        try:
            canonical = PublicHuggingFaceMaterialCollector.parse_public_card_url(url).canonical_url
        except Exception:  # noqa: BLE001 - executor emits a safe policy denial.
            return False
        if canonical == str(bundle.target.canonical_url).rstrip("/"):
            return True
        return any(
            canonical in source.content or canonical == str(source.source_url or "").rstrip("/")
            for source in bundle.sources
        )

    @staticmethod
    def _search_material(
        builder: MaterialBundleBuilder,
        bundle: MaterialBundle,
        request: ToolRequest,
        hits: tuple[PublicSearchHit, ...],
        title: str,
    ) -> list[MaterialSource]:
        payload = {
            "query": request.query,
            "result_count": len(hits),
            "results": [asdict(hit) for hit in hits],
        }
        material = CollectedMaterial(
            material_type="Repository" if request.tool_name == "search_github" else "Other",
            title=title,
            source_path=f".researchops/tool-results/{request.request_id}.json",
            content=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            access_scope="public",
            priority=75,
        )
        return list(builder.build(bundle.target, [material]).bundle.sources)

    @staticmethod
    def _probe_material(
        builder: MaterialBundleBuilder,
        bundle: MaterialBundle,
        request: ToolRequest,
        material_type: str,
        source_url: str,
        payload: dict[str, object],
    ) -> list[MaterialSource]:
        material = CollectedMaterial(
            material_type=material_type,
            title=f"{request.tool_name} result",
            source_path=f".researchops/tool-results/{request.request_id}.json",
            source_url=source_url,
            content=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            access_scope="public",
            priority=98,
        )
        return list(builder.build(bundle.target, [material]).bundle.sources)

    @staticmethod
    def _github_file_material(
        builder: MaterialBundleBuilder,
        bundle: MaterialBundle,
        material,
    ) -> list[MaterialSource]:
        suffix = material.path.rsplit(".", 1)[-1].casefold() if "." in material.path else ""
        material_type = (
            "Config" if suffix in {"cfg", "ini", "json", "toml", "yaml", "yml"} else "Other"
        )
        collected = CollectedMaterial(
            material_type=material_type,
            title=material.path,
            source_path=material.path,
            source_url=material.html_url,
            content=material.text,
            access_scope="public",
            priority=96,
        )
        return list(builder.build(bundle.target, [collected]).bundle.sources)

    @staticmethod
    def _resolve_target(target_type: str, entry: str) -> ResolvedTarget:
        response = TargetResolutionService(
            paper_metadata_search=_NoopPaperMetadataSearch()
        ).resolve(TargetResolutionRequest(target_type=target_type, target_entry=entry))
        if response.status != "identified" or response.resolved_target is None:
            raise ResearchToolExecutionError("tool argument did not resolve to an allowed target")
        return response.resolved_target

    @staticmethod
    def _paper_target(identifier: str) -> tuple[str, str]:
        normalized = identifier.strip()
        folded = normalized.casefold()
        if folded.startswith("doi:"):
            candidate = normalized[4:].strip()
            if DOI_PATTERN.fullmatch(candidate):
                return "doi", candidate
            raise ResearchToolArgumentError("fetch_paper DOI identifier is invalid")
        if folded.startswith("arxiv:"):
            candidate = normalized[6:].strip()
            if ARXIV_PATTERN.fullmatch(candidate):
                return "arxiv", candidate
            raise ResearchToolArgumentError("fetch_paper arXiv identifier is invalid")
        if DOI_PATTERN.fullmatch(normalized):
            return "doi", normalized
        if ARXIV_PATTERN.fullmatch(normalized):
            return "arxiv", normalized
        raise ResearchToolArgumentError(
            "fetch_paper requires a DOI or arXiv identifier, not a title, citation, or URL"
        )

    @staticmethod
    def _failure_code(exc: Exception) -> ResearchToolFailureCode:
        if isinstance(exc, ResearchToolArgumentError):
            return "invalid_tool_argument"

        chain: list[BaseException] = []
        current: BaseException | None = exc
        while current is not None and current not in chain:
            chain.append(current)
            current = current.__cause__ or current.__context__

        if any(isinstance(item, httpx.TimeoutException) for item in chain):
            return "transport_timeout"
        status_errors = [item for item in chain if isinstance(item, httpx.HTTPStatusError)]
        if any(item.response.status_code == 404 for item in status_errors):
            return "target_not_found"
        if status_errors or any(isinstance(item, httpx.HTTPError) for item in chain):
            return "remote_access_failed"
        if isinstance(exc, PaperMaterialCollectionError):
            safe_message = str(exc).casefold()
            if any(
                marker in safe_message
                for marker in ("no paper metadata record", "did not match the requested paper")
            ):
                return "target_not_found"
        return "connector_failure"

    @staticmethod
    def _result(
        request: ToolRequest,
        status: str,
        detail: str,
        started_at: datetime,
        source_ids: list[str] | None = None,
        failure_code: ResearchToolFailureCode | None = None,
    ) -> ToolRequestExecutionResult:
        return ToolRequestExecutionResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            status=status,
            failure_code=failure_code,
            source_ids=source_ids or [],
            detail=detail,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
