"""Deterministic provenance and quote validation for AI-proposed evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from researchops.schemas.ai_analysis import (
    AIAnalysisResult,
    AIAnalysisValidationResult,
    AIEvidenceExtractionResult,
    EvidenceCandidate,
    EvidenceValidationDecision,
    EvidenceValidationIssue,
    EvidenceValidationResult,
    ExternalEvidenceKind,
    ExternalEvidenceVerification,
    MaterialBundle,
    MaterialSource,
    SourceLocator,
)
from researchops.schemas.readiness import FindingType
from researchops.services.data_access import DatasetAccessProbe, PublicDatasetAccessProbe
from researchops.services.external_assets import (
    ALLOWED_ASSET_HOSTS,
    ExternalAssetProbe,
    PublicExternalAssetProbe,
)

_URL_PATTERN = re.compile(r"https?://[^\s)\]}>\"']+")


class EvidenceRuleValidationError(RuntimeError):
    """Analysis and material identities violate the Rule-layer input contract."""


@dataclass(frozen=True, slots=True)
class _QuoteOccurrence:
    start: int
    end: int
    line_start: int
    line_end: int


class DeterministicEvidenceRuleValidator:
    """Validate evidence provenance without reinterpreting research semantics."""

    def __init__(
        self,
        *,
        dataset_probe: DatasetAccessProbe | None = None,
        asset_probe: ExternalAssetProbe | None = None,
    ) -> None:
        self._dataset_probe = dataset_probe
        self._asset_probe = asset_probe

    def validate(
        self,
        bundle: MaterialBundle,
        analysis: AIAnalysisResult | AIEvidenceExtractionResult,
    ) -> AIAnalysisValidationResult:
        if isinstance(analysis, AIEvidenceExtractionResult):
            analysis = analysis.to_analysis_result()
        if analysis.bundle_id != bundle.bundle_id:
            raise EvidenceRuleValidationError("Analysis 与 MaterialBundle 身份不匹配。")

        sources = {source.source_id: source for source in bundle.sources}
        collected_urls = self._collected_urls(bundle)
        missing_examined_ids = sorted(set(analysis.examined_source_ids) - set(sources))
        analysis_issues = [
            EvidenceValidationIssue(
                code="source_missing",
                message=f"模型声明检查的 source_id 不存在：{source_id}",
            )
            for source_id in missing_examined_ids
        ]
        examined_ids = set(analysis.examined_source_ids)
        evidence_results = [
            self._validate_candidate(candidate, sources, examined_ids, collected_urls)
            for candidate in analysis.evidence_candidates
        ]
        return AIAnalysisValidationResult(
            analysis_id=analysis.analysis_id,
            bundle_id=bundle.bundle_id,
            analysis_source_ids_verified=not analysis_issues,
            analysis_issues=analysis_issues,
            evidence_results=evidence_results,
        )

    def _validate_candidate(
        self,
        candidate: EvidenceCandidate,
        sources: dict[str, MaterialSource],
        examined_ids: set[str],
        collected_urls: set[str],
    ) -> EvidenceValidationResult:
        source = sources.get(candidate.locator.source_id)
        if source is None:
            return self._result(
                candidate,
                decision="rejected",
                issues=[
                    EvidenceValidationIssue(
                        code="source_missing",
                        message=f"Evidence 引用的 source_id 不存在：{candidate.locator.source_id}",
                    )
                ],
            )
        if source.source_id not in examined_ids:
            return self._result(
                candidate,
                decision="rejected",
                source_verified=True,
                issues=[
                    EvidenceValidationIssue(
                        code="source_not_examined",
                        message="Evidence 引用的来源未出现在模型声明的 examined_source_ids 中。",
                    )
                ],
            )

        occurrences = self._quote_occurrences(
            source.content,
            candidate.quote,
            line_offset=source.line_start - 1,
        )
        if not occurrences:
            if source.is_truncated:
                return self._result(
                    candidate,
                    decision="needs_human_confirmation",
                    source_verified=True,
                    issues=[
                        EvidenceValidationIssue(
                            code="source_truncated",
                            message="来源已被有界截断，无法断言引用在原始材料中不存在。",
                        ),
                        EvidenceValidationIssue(
                            code="quote_missing",
                            message="逐字引用未出现在当前送检的有界内容中。",
                        ),
                    ],
                )
            return self._result(
                candidate,
                decision="rejected",
                source_verified=True,
                issues=[
                    EvidenceValidationIssue(
                        code="quote_mismatch",
                        message="逐字引用未出现在指定来源中。",
                    )
                ],
            )

        occurrence, location_issue = self._verified_occurrence(candidate.locator, occurrences)
        if location_issue is not None:
            if location_issue.code == "ambiguous_location":
                return self._result(
                    candidate,
                    decision="needs_human_confirmation",
                    source_verified=True,
                    quote_verified=True,
                    issues=[location_issue],
                )
            return self._result(
                candidate,
                decision="downgraded",
                source_verified=True,
                quote_verified=True,
                resulting_type=self._downgraded_type(candidate),
                issues=[location_issue],
            )

        verified_locator = SourceLocator(
            source_id=source.source_id,
            location=self._canonical_location(
                source.source_path,
                occurrence.line_start,
                occurrence.line_end,
            ),
            line_start=occurrence.line_start,
            line_end=occurrence.line_end,
        )
        claim_urls = self._extract_urls(candidate.claim)
        quote_urls = self._extract_urls(candidate.quote)
        external_kind = self._external_verification_kind(candidate.condition_key)
        first_party_access = self._is_first_party_access_confirmation(candidate, source)
        referenced_urls = claim_urls or quote_urls
        if (
            not referenced_urls
            and external_kind is not None
            and source.source_url is not None
            and source.material_type in {"Dataset Page", "Checkpoint-Release"}
        ):
            referenced_urls = [str(source.source_url)]
        url_membership_verified: bool | None = None
        if referenced_urls:
            url_membership_verified = all(
                self._canonical_url(url) in collected_urls for url in referenced_urls
            )
            if not url_membership_verified:
                return self._result(
                    candidate,
                    decision="rejected",
                    source_verified=True,
                    quote_verified=True,
                    location_verified=True,
                    claim_scope_verified=False,
                    url_membership_verified=False,
                    verified_locator=verified_locator,
                    issues=[
                        EvidenceValidationIssue(
                            code="url_not_in_collected_sources",
                            message="Evidence 声称的 URL 不属于本次已采集材料。",
                        )
                    ],
                )

        claim_scope_verified = self._claim_scope_verified(candidate.claim, candidate.quote)
        if claim_scope_verified is False:
            return self._result(
                candidate,
                decision="downgraded",
                source_verified=True,
                quote_verified=True,
                location_verified=True,
                claim_scope_verified=False,
                url_membership_verified=url_membership_verified,
                verified_locator=verified_locator,
                resulting_type=self._downgraded_type(candidate),
                issues=[
                    EvidenceValidationIssue(
                        code="claim_exceeds_source",
                        message="Claim 包含逐字引用中不存在的版本、数值、URL 或文件标识。",
                    )
                ],
            )

        external_verifications: list[ExternalEvidenceVerification] = []
        if external_kind is not None and not first_party_access:
            if not referenced_urls:
                return self._result(
                    candidate,
                    decision="downgraded",
                    source_verified=True,
                    quote_verified=True,
                    location_verified=True,
                    claim_scope_verified=claim_scope_verified,
                    verified_locator=verified_locator,
                    resulting_type="Unknown",
                    issues=[
                        EvidenceValidationIssue(
                            code="external_access_unconfirmed",
                            message="访问性 Claim 没有提供可执行确定性探测的已采集 URL。",
                        )
                    ],
                )

            external_verifications = self._probe_external_urls(referenced_urls, external_kind)
            states = {item.state for item in external_verifications}
            if "verified_inaccessible" in states:
                return self._result(
                    candidate,
                    decision="rejected",
                    source_verified=True,
                    quote_verified=True,
                    location_verified=True,
                    claim_scope_verified=claim_scope_verified,
                    url_membership_verified=True,
                    verified_locator=verified_locator,
                    external_verifications=external_verifications,
                    issues=[
                        EvidenceValidationIssue(
                            code="external_access_inaccessible",
                            message="确定性只读探测确认至少一个外部入口当前不可公开访问。",
                        )
                    ],
                )
            if states != {"verified_public"}:
                issue_code = (
                    "external_acquisition_failure"
                    if "acquisition_failure" in states
                    else "external_probe_unsupported"
                    if "unsupported" in states
                    else "external_access_unconfirmed"
                )
                return self._result(
                    candidate,
                    decision="downgraded",
                    source_verified=True,
                    quote_verified=True,
                    location_verified=True,
                    claim_scope_verified=claim_scope_verified,
                    url_membership_verified=True,
                    verified_locator=verified_locator,
                    resulting_type="Unknown",
                    external_verifications=external_verifications,
                    issues=[
                        EvidenceValidationIssue(
                            code=issue_code,
                            message=(
                                "外部入口已定位，但本次确定性只读探测不足以确认匿名公开访问。"
                            ),
                        )
                    ],
                )

        return self._result(
            candidate,
            decision="accepted",
            source_verified=True,
            quote_verified=True,
            location_verified=True,
            claim_scope_verified=claim_scope_verified,
            url_membership_verified=url_membership_verified,
            verified_locator=verified_locator,
            resulting_type=candidate.evidence_type,
            external_verifications=external_verifications,
        )

    @staticmethod
    def _collected_urls(bundle: MaterialBundle) -> set[str]:
        urls: set[str] = set()
        for source in bundle.sources:
            if source.source_url is not None:
                urls.add(DeterministicEvidenceRuleValidator._canonical_url(str(source.source_url)))
            urls.update(
                DeterministicEvidenceRuleValidator._canonical_url(url)
                for url in DeterministicEvidenceRuleValidator._extract_urls(source.content)
            )
        return urls

    @staticmethod
    def _extract_urls(text: str) -> list[str]:
        return [match.rstrip(".,;:") for match in _URL_PATTERN.findall(text)]

    @staticmethod
    def _canonical_url(url: str) -> str:
        parts = urlsplit(url)
        hostname = (parts.hostname or "").casefold()
        port = parts.port
        netloc = hostname
        if port is not None and not (
            (parts.scheme.casefold() == "https" and port == 443)
            or (parts.scheme.casefold() == "http" and port == 80)
        ):
            netloc = f"{hostname}:{port}"
        path = parts.path or "/"
        query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
        return urlunsplit((parts.scheme.casefold(), netloc, path, query, ""))

    @staticmethod
    def _external_verification_kind(condition_key: str) -> ExternalEvidenceKind | None:
        key = condition_key.casefold()
        access_condition = any(token in key for token in ("access", "public", "download"))
        if not access_condition:
            return None
        if any(token in key for token in ("dataset", "data.")):
            return "dataset_access"
        if any(token in key for token in ("checkpoint", "weight")):
            return "checkpoint_access"
        return None

    @staticmethod
    def _is_first_party_access_confirmation(
        candidate: EvidenceCandidate,
        source: MaterialSource,
    ) -> bool:
        """Recognize customer-owned access facts without claiming public availability."""

        if source.access_scope != "user_provided":
            return False
        if candidate.evidence_type != "Fact":
            return False
        if candidate.criterion_id not in {"rd01.dataset_access", "rd03.checkpoint_access"}:
            return False
        public_markers = (
            "public",
            "publicly",
            "anonymous",
            "anonymously",
            "anyone",
            "without login",
            "公开",
            "匿名",
            "任何人",
            "无需登录",
        )
        normalized_claim = candidate.claim.casefold()
        return not any(marker in normalized_claim for marker in public_markers)

    def _probe_external_urls(
        self,
        urls: list[str],
        kind: ExternalEvidenceKind,
    ) -> list[ExternalEvidenceVerification]:
        if kind == "dataset_access":
            owned_probe = self._dataset_probe is None
            probe = self._dataset_probe or PublicDatasetAccessProbe()
            try:
                results = [probe.probe(url) for url in urls]
            finally:
                if owned_probe and hasattr(probe, "close"):
                    probe.close()
            state_mapping = {
                "public_download": "verified_public",
                "public_page": "public_page_only",
                "account_required": "account_required",
                "approval_required": "approval_required",
                "verified_inaccessible": "verified_inaccessible",
                "unreachable": "acquisition_failure",
                "unsupported": "unsupported",
            }
            return [
                ExternalEvidenceVerification(
                    url=result.source_url,
                    kind=kind,
                    state=state_mapping[result.state],
                    detail=result.detail[:1000],
                )
                for result in results
            ]

        unsupported = [
            ExternalEvidenceVerification(
                url=url,
                kind=kind,
                state="unsupported",
                detail="External asset host is outside the read-only checkpoint allowlist.",
            )
            for url in urls
            if urlsplit(url).hostname not in ALLOWED_ASSET_HOSTS
        ]
        supported_urls = [url for url in urls if urlsplit(url).hostname in ALLOWED_ASSET_HOSTS]
        if not supported_urls:
            return unsupported

        owned_probe = self._asset_probe is None
        asset_probe = self._asset_probe or PublicExternalAssetProbe()
        try:
            asset_results = [asset_probe.probe(url) for url in supported_urls]
        finally:
            if owned_probe and hasattr(asset_probe, "close"):
                asset_probe.close()
        return unsupported + [
            ExternalEvidenceVerification(
                url=result.source_url,
                kind=kind,
                state=result.verification_state,
                detail=result.detail[:1000],
            )
            for result in asset_results
        ]

    @staticmethod
    def _verified_occurrence(
        locator: SourceLocator,
        occurrences: list[_QuoteOccurrence],
    ) -> tuple[_QuoteOccurrence | None, EvidenceValidationIssue | None]:
        if locator.line_start is None:
            if len(occurrences) == 1:
                return occurrences[0], None
            return None, EvidenceValidationIssue(
                code="ambiguous_location",
                message="相同逐字引用在来源中出现多次，且模型未提供行号范围。",
            )

        matching = [
            occurrence
            for occurrence in occurrences
            if locator.line_start <= occurrence.line_start
            and occurrence.line_end <= locator.line_end
        ]
        if matching:
            return matching[0], None
        return None, EvidenceValidationIssue(
            code="location_mismatch",
            message="逐字引用存在，但不在模型声明的行号范围内。",
        )

    @staticmethod
    def _quote_occurrences(
        content: str,
        quote: str,
        *,
        line_offset: int = 0,
    ) -> list[_QuoteOccurrence]:
        occurrences: list[_QuoteOccurrence] = []
        start = 0
        while True:
            index = content.find(quote, start)
            if index < 0:
                return occurrences
            end = index + len(quote)
            occurrences.append(
                _QuoteOccurrence(
                    start=index,
                    end=end,
                    line_start=content.count("\n", 0, index) + 1 + line_offset,
                    line_end=content.count("\n", 0, end - 1) + 1 + line_offset,
                )
            )
            start = index + max(1, len(quote))

    @staticmethod
    def _downgraded_type(candidate: EvidenceCandidate) -> FindingType:
        return "Unknown" if candidate.evidence_type == "Unknown" else "Inference"

    @staticmethod
    def _canonical_location(source_path: str, line_start: int, line_end: int) -> str:
        suffix = f":lines {line_start}-{line_end}"
        available_path_length = 500 - len(suffix)
        if len(source_path) > available_path_length:
            source_path = f"…{source_path[-(available_path_length - 1) :]}"
        return f"{source_path}{suffix}"

    @staticmethod
    def _claim_scope_verified(claim: str, quote: str) -> bool | None:
        """Check only objective literal anchors; do not pretend to prove entailment."""
        anchor_pattern = re.compile(
            r"https?://[^\s)\]>]+"
            r"|\b\d+(?:\.\d+)+\b"
            r"|\b[A-Za-z0-9_.-]+\.(?:cfg|ini|json|toml|txt|yaml|yml|py|pth|pt|ckpt)\b"
            r"|\b[A-Z][A-Z0-9_-]{1,}\b"
        )
        anchors = {match.casefold() for match in anchor_pattern.findall(claim)}
        if not anchors:
            return None
        normalized_quote = quote.casefold()
        return all(anchor in normalized_quote for anchor in anchors)

    @staticmethod
    def _result(
        candidate: EvidenceCandidate,
        *,
        decision: EvidenceValidationDecision,
        source_verified: bool = False,
        quote_verified: bool = False,
        location_verified: bool = False,
        claim_scope_verified: bool | None = None,
        url_membership_verified: bool | None = None,
        verified_locator: SourceLocator | None = None,
        resulting_type: FindingType | None = None,
        external_verifications: list[ExternalEvidenceVerification] | None = None,
        issues: list[EvidenceValidationIssue] | None = None,
    ) -> EvidenceValidationResult:
        return EvidenceValidationResult(
            evidence_candidate_id=candidate.candidate_id,
            decision=decision,
            source_verified=source_verified,
            quote_verified=quote_verified,
            location_verified=location_verified,
            claim_scope_verified=claim_scope_verified,
            url_membership_verified=url_membership_verified,
            verified_locator=verified_locator,
            resulting_type=resulting_type,
            external_verifications=external_verifications or [],
            issues=issues or [],
        )
