"""RD-01 数据入口与访问条件的受限只读核验。"""

from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urljoin, urlparse

import httpx

from researchops.core.outbound import outbound_client
from researchops.core.security import redact_sensitive_url
from researchops.schemas import Evidence, FindingType, ReadinessStatus
from researchops.services.repository_materials import DatasetReference, RepositoryMaterials

DatasetAccessState = Literal[
    "public_download",
    "public_page",
    "account_required",
    "approval_required",
    "verified_inaccessible",
    "unreachable",
    "unsupported",
]
ALLOWED_DATASET_HOSTS = {
    "docs.google.com",
    "github.com",
    "huggingface.co",
    "kaggle.com",
    "sites.google.com",
    "www.kaggle.com",
    "zenodo.org",
}
APPROVAL_MARKERS = (
    "apply for access",
    "data request form",
    "fill out the request form",
    "once accepted",
    "request access",
    "requires approval",
)
GATED_MARKERS = (
    "access request",
    "gated dataset",
    "you need to agree",
    "you must accept",
)


@dataclass(frozen=True, slots=True)
class DatasetAccessProbeResult:
    """一个数据入口在公开、未登录条件下的可观察状态。"""

    source_url: str
    final_url: str | None
    state: DatasetAccessState
    detail: str


class DatasetAccessProbe(Protocol):
    """数据入口核验器协议。"""

    def probe(self, url: str) -> DatasetAccessProbeResult:
        """只读检查入口，不登录、不接受条款、不下载数据集。"""
        ...


class PublicDatasetAccessProbe:
    """仅访问 allowlist 中的数据入口并读取有界页面内容。"""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_response_bytes: int = 500_000,
        max_redirects: int = 4,
    ) -> None:
        self._owns_client = client is None
        self.client = client or outbound_client(
            headers={"User-Agent": "ResearchOps-Agent/0.1"},
            timeout=httpx.Timeout(12.0, connect=5.0),
            follow_redirects=False,
            trust_env=False,
        )
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max(0, max_redirects)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def probe(self, url: str) -> DatasetAccessProbeResult:
        if not self._is_allowed_url(url):
            return DatasetAccessProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=None,
                state="unsupported",
                detail="Dataset host is outside the read-only allowlist.",
            )

        current_url = url
        for redirect_count in range(self.max_redirects + 1):
            if not self._is_allowed_url(current_url):
                return DatasetAccessProbeResult(
                    source_url=redact_sensitive_url(url),
                    final_url=redact_sensitive_url(current_url),
                    state="unsupported",
                    detail="Dataset redirect was blocked before leaving the read-only allowlist.",
                )
            try:
                with self.client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location or redirect_count >= self.max_redirects:
                            return DatasetAccessProbeResult(
                                source_url=redact_sensitive_url(url),
                                final_url=redact_sensitive_url(response.url),
                                state="unreachable",
                                detail="Dataset redirect chain could not be resolved safely.",
                            )
                        current_url = urljoin(current_url, location)
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").casefold()
                    disposition = response.headers.get("content-disposition", "").casefold()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        remaining = self.max_response_bytes - len(body)
                        if remaining <= 0:
                            break
                        body.extend(chunk[:remaining])
                    final_url = str(response.url)
            except httpx.HTTPStatusError as exc:
                state: DatasetAccessState = (
                    "verified_inaccessible"
                    if exc.response.status_code in {401, 403, 404, 410}
                    else "unreachable"
                )
                return DatasetAccessProbeResult(
                    source_url=redact_sensitive_url(url),
                    final_url=redact_sensitive_url(exc.response.url),
                    state=state,
                    detail=(
                        f"Dataset entry was reached but returned HTTP {exc.response.status_code}."
                    ),
                )
            except httpx.RequestError:
                return DatasetAccessProbeResult(
                    source_url=redact_sensitive_url(url),
                    final_url=None,
                    state="unreachable",
                    detail="Dataset entry request failed for a transport reason.",
                )
            break

        final_host = urlparse(final_url).hostname
        if final_host not in ALLOWED_DATASET_HOSTS:
            return DatasetAccessProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                state="unsupported",
                detail="Dataset entry redirected outside the read-only allowlist.",
            )

        content = body.decode("utf-8", errors="replace").casefold()
        if any(marker in content for marker in APPROVAL_MARKERS):
            return DatasetAccessProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                state="approval_required",
                detail="The public dataset instructions require a request or approval step.",
            )
        if final_host == "huggingface.co" and any(marker in content for marker in GATED_MARKERS):
            return DatasetAccessProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                state="approval_required",
                detail="The Hugging Face dataset entry is gated and requires approval or terms.",
            )
        if final_host in {"kaggle.com", "www.kaggle.com"}:
            return DatasetAccessProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                state="account_required",
                detail=(
                    "The Kaggle dataset entry is identifiable, but authenticated account access "
                    "and competition or dataset terms may be required for download."
                ),
            )
        if "attachment" in disposition or (
            content_type and "html" not in content_type and "text/plain" not in content_type
        ):
            return DatasetAccessProbeResult(
                source_url=redact_sensitive_url(url),
                final_url=redact_sensitive_url(final_url),
                state="public_download",
                detail="The dataset artifact responds as a public downloadable resource.",
            )
        return DatasetAccessProbeResult(
            source_url=redact_sensitive_url(url),
            final_url=redact_sensitive_url(final_url),
            state="public_page",
            detail=(
                "The dataset information page is publicly readable, but artifact access and the "
                "user's entitlement are not confirmed."
            ),
        )

    @staticmethod
    def _is_allowed_url(url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_DATASET_HOSTS
            and parsed.port in {None, 443}
            and parsed.username is None
            and parsed.password is None
        )


@dataclass(frozen=True, slots=True)
class DataAccessEvaluation:
    """供 RD-01 直接消费的结构化判断。"""

    status: ReadinessStatus
    summary: str
    gate_impact: str
    finding_title: str
    finding_summary: str
    finding_type: FindingType
    readiness_impact: str
    evidence: tuple[Evidence, ...]


class DataAccessService:
    """把数据入口的公开状态转成冻结的 RD-01 状态语义。"""

    def __init__(self, probe: DatasetAccessProbe | None = None) -> None:
        self.probe = probe or PublicDatasetAccessProbe()

    def evaluate(self, materials: RepositoryMaterials) -> DataAccessEvaluation:
        references = materials.dataset_references
        if not references:
            return DataAccessEvaluation(
                status="Unknown",
                summary="The collected Repository materials do not establish a dataset entry.",
                gate_impact="Prevents full PROCEED until the required dataset path is identified.",
                finding_title="Dataset entry was not located",
                finding_summary=(
                    "No allowlisted dataset URL was found in the bounded README material."
                ),
                finding_type="Unknown",
                readiness_impact="Prevents full PROCEED",
                evidence=(self._missing_evidence(materials),),
            )

        results = [(reference, self.probe.probe(reference.url)) for reference in references]
        evidence = tuple(self._evidence(reference, result) for reference, result in results)
        all_public_downloads = all(result.state == "public_download" for _, result in results)
        if all_public_downloads:
            return DataAccessEvaluation(
                status="Ready",
                summary=(
                    "The documented dataset artifacts respond as public downloads without an "
                    "observed account or approval requirement."
                ),
                gate_impact="No current blocker from the documented dataset entry.",
                finding_title="Dataset artifacts are publicly reachable",
                finding_summary=(
                    "All documented dataset references responded as public downloadable resources; "
                    "full dataset integrity and preprocessing remain outside this check."
                ),
                finding_type="Fact",
                readiness_impact="No current blocker",
                evidence=evidence,
            )

        counts = self._state_counts(results)
        conditions = []
        if counts.get("approval_required"):
            conditions.append(f"{counts['approval_required']} approval-required")
        if counts.get("account_required"):
            conditions.append(f"{counts['account_required']} account/terms-dependent")
        if counts.get("public_page"):
            conditions.append(f"{counts['public_page']} public-page-only")
        if counts.get("verified_inaccessible"):
            conditions.append(f"{counts['verified_inaccessible']} verified-inaccessible")
        if counts.get("unreachable") or counts.get("unsupported"):
            conditions.append(
                f"{counts.get('unreachable', 0) + counts.get('unsupported', 0)} unverified"
            )
        condition_summary = ", ".join(conditions) or "artifact access unconfirmed"
        return DataAccessEvaluation(
            status="Unknown",
            summary=(
                f"Located {len(results)} dataset entry or entries ({condition_summary}), but the "
                "user's access to the selected reproduction dataset is not confirmed."
            ),
            gate_impact="Prevents full PROCEED until access for the selected dataset path is confirmed.",
            finding_title="Dataset entries located; access remains unconfirmed",
            finding_summary=(
                "The public entry pages were inspected without login or download. Account, terms, "
                "approval, or artifact-level access still requires user confirmation."
            ),
            finding_type="Unknown",
            readiness_impact="Prevents full PROCEED",
            evidence=evidence,
        )

    @staticmethod
    def _state_counts(
        results: list[tuple[DatasetReference, DatasetAccessProbeResult]],
    ) -> dict[DatasetAccessState, int]:
        counts: dict[DatasetAccessState, int] = {}
        for _, result in results:
            counts[result.state] = counts.get(result.state, 0) + 1
        return counts

    @staticmethod
    def _evidence(
        reference: DatasetReference,
        result: DatasetAccessProbeResult,
    ) -> Evidence:
        located = result.state not in {"unreachable", "unsupported"}
        return Evidence(
            evidence_type="Fact" if located else "Unknown",
            verification_status="Corroborated" if located else "Unverifiable",
            source_type="Material",
            material_type="Dataset Page",
            summary=f"{reference.name}: {result.detail}",
            source=f"{reference.source_path} + dataset entry",
            location=f"{reference.source_path}:line {reference.line_number}",
            excerpt=reference.excerpt,
            source_url=reference.url,
        )

    @staticmethod
    def _missing_evidence(materials: RepositoryMaterials) -> Evidence:
        return Evidence(
            evidence_type="Unknown",
            verification_status="Unverifiable",
            source_type="Material",
            material_type="Repository",
            summary="No allowlisted dataset entry URL was located in the collected README.",
            source="Bounded Repository material scan",
            location=f"branch:{materials.default_branch}",
            excerpt="No dataset entry URL was located.",
            source_url=materials.repository_url,
        )
