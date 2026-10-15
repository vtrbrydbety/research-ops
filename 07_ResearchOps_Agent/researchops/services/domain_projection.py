"""Project admitted AI candidates into stable Readiness domain objects."""

from __future__ import annotations

from researchops.schemas.ai_analysis import (
    AIAnalysisAdjudicationResult,
    AIAnalysisDomainProjection,
    AIAnalysisResult,
    AIAnalysisValidationResult,
    ConflictCandidate,
    EvidenceCandidate,
    EvidenceValidationResult,
    FindingCandidate,
    MaterialBundle,
    MaterialSource,
    ProjectedConflict,
    ProjectedEvidence,
    ProjectedFinding,
)
from researchops.schemas.readiness import (
    Evidence,
    EvidenceConflict,
    Finding,
)


class DomainProjectionError(RuntimeError):
    """Candidate, validation, adjudication, and material identities are inconsistent."""


class ReadinessDomainProjectionService:
    """Create domain objects without assigning readiness status or Overall Gate."""

    def project(
        self,
        bundle: MaterialBundle,
        analysis: AIAnalysisResult,
        evidence_validation: AIAnalysisValidationResult,
        adjudication: AIAnalysisAdjudicationResult,
    ) -> AIAnalysisDomainProjection:
        self._validate_input_graph(bundle, analysis, evidence_validation, adjudication)

        evidence_candidates = {
            candidate.candidate_id: candidate for candidate in analysis.evidence_candidates
        }
        evidence_results = {
            result.evidence_candidate_id: result for result in evidence_validation.evidence_results
        }
        sources = {source.source_id: source for source in bundle.sources}

        projected_evidence = [
            self._project_evidence(
                evidence_candidates[candidate_id],
                evidence_results[candidate_id],
                sources,
            )
            for candidate_id in adjudication.admitted_evidence_candidate_ids
        ]
        domain_evidence_by_id = {
            item.evidence_candidate_id: item.evidence for item in projected_evidence
        }

        original_findings = {
            candidate.candidate_id: candidate for candidate in analysis.finding_candidates
        }
        projected_findings = [
            self._project_finding(candidate, original_findings, domain_evidence_by_id)
            for candidate in adjudication.admitted_finding_candidates
        ]

        original_conflicts = {
            candidate.candidate_id: candidate for candidate in analysis.conflict_candidates
        }
        projected_conflicts = [
            self._project_conflict(candidate, original_conflicts, domain_evidence_by_id)
            for candidate in adjudication.admitted_conflict_candidates
        ]

        return AIAnalysisDomainProjection(
            analysis_id=analysis.analysis_id,
            bundle_id=bundle.bundle_id,
            analysis_source_ids_verified=adjudication.analysis_source_ids_verified,
            analysis_issues=adjudication.analysis_issues,
            evidence=projected_evidence,
            findings=projected_findings,
            conflicts=projected_conflicts,
            unresolved_questions=analysis.unresolved_questions,
            human_confirmation_candidate_ids=adjudication.human_confirmation_candidate_ids,
        )

    @staticmethod
    def _validate_input_graph(
        bundle: MaterialBundle,
        analysis: AIAnalysisResult,
        evidence_validation: AIAnalysisValidationResult,
        adjudication: AIAnalysisAdjudicationResult,
    ) -> None:
        if not (
            bundle.bundle_id
            == analysis.bundle_id
            == evidence_validation.bundle_id
            == adjudication.bundle_id
        ) or not (
            analysis.analysis_id == evidence_validation.analysis_id == adjudication.analysis_id
        ):
            raise DomainProjectionError("Bundle、Analysis、Validation 与 Adjudication 身份不匹配。")

        candidate_ids = {item.candidate_id for item in analysis.evidence_candidates}
        validation_by_id = {
            item.evidence_candidate_id: item for item in evidence_validation.evidence_results
        }
        if set(validation_by_id) != candidate_ids:
            raise DomainProjectionError("Evidence 验证结果未完整覆盖候选集。")
        accepted_ids = {
            item.evidence_candidate_id
            for item in evidence_validation.evidence_results
            if item.decision in {"accepted", "downgraded"}
            and item.resulting_type is not None
            and item.verified_locator is not None
        }
        if set(adjudication.admitted_evidence_candidate_ids) != accepted_ids:
            raise DomainProjectionError("Adjudication 的受理 Evidence 集与 Rule 结果不一致。")
        if (
            adjudication.analysis_source_ids_verified
            != evidence_validation.analysis_source_ids_verified
            or adjudication.analysis_issues != evidence_validation.analysis_issues
        ):
            raise DomainProjectionError("Adjudication 未保留 Evidence 层的来源验证结论。")

        graph_ids = {
            *candidate_ids,
            *(item.candidate_id for item in analysis.conflict_candidates),
            *(item.candidate_id for item in analysis.finding_candidates),
        }
        if not set(adjudication.human_confirmation_candidate_ids) <= graph_ids:
            raise DomainProjectionError("Human confirmation 队列包含候选图外的 ID。")
        admitted_graph_ids = {
            *adjudication.admitted_evidence_candidate_ids,
            *(item.candidate_id for item in adjudication.admitted_conflict_candidates),
            *(item.candidate_id for item in adjudication.admitted_finding_candidates),
        }
        if set(adjudication.human_confirmation_candidate_ids) & admitted_graph_ids:
            raise DomainProjectionError("待人工确认候选不能同时进入领域投影。")

    def _project_evidence(
        self,
        candidate: EvidenceCandidate,
        validation: EvidenceValidationResult,
        sources: dict[str, MaterialSource],
    ) -> ProjectedEvidence:
        if (
            validation.decision not in {"accepted", "downgraded"}
            or validation.resulting_type is None
        ):
            raise DomainProjectionError("只有 Rule 可用的 Evidence 才能进入领域投影。")
        if (
            validation.decision == "accepted"
            and validation.resulting_type != candidate.evidence_type
        ):
            raise DomainProjectionError("accepted Evidence 不得改变模型候选类型。")
        locator = validation.verified_locator
        if locator is None or locator.source_id != candidate.locator.source_id:
            raise DomainProjectionError("Evidence 的规范化 locator 与模型来源不一致。")
        source = sources.get(locator.source_id)
        if source is None:
            raise DomainProjectionError("Evidence 的规范化来源不在 MaterialBundle 中。")
        if candidate.quote not in source.content:
            raise DomainProjectionError("accepted Evidence 的逐字 quote 与 Bundle 内容不一致。")
        lines = source.content.splitlines()
        local_line_start = (
            locator.line_start - source.line_start + 1 if locator.line_start is not None else None
        )
        local_line_end = (
            locator.line_end - source.line_start + 1 if locator.line_end is not None else None
        )
        if (
            local_line_start is None
            or local_line_end is None
            or local_line_start < 1
            or local_line_end > len(lines)
            or candidate.quote not in "\n".join(lines[local_line_start - 1 : local_line_end])
        ):
            raise DomainProjectionError("Rule 可用 Evidence 的规范化行号未覆盖逐字 quote。")

        source_type = "Material" if source.access_scope == "public" else "User Context"
        evidence = Evidence(
            evidence_id=candidate.candidate_id,
            source_id=source.source_id,
            evidence_type=validation.resulting_type,
            verification_status="Located Only",
            source_type=source_type,
            material_type=source.material_type,
            summary=self._truncate(candidate.claim, 1000),
            source=source.title,
            location=locator.location,
            line_start=locator.line_start,
            line_end=locator.line_end,
            excerpt=self._truncate(candidate.quote, 2000),
            source_url=source.source_url,
        )
        return ProjectedEvidence(
            evidence_candidate_id=candidate.candidate_id,
            source_id=source.source_id,
            criterion_id=candidate.criterion_id,
            evidence=evidence,
        )

    def _project_finding(
        self,
        candidate: FindingCandidate,
        original_findings: dict[str, FindingCandidate],
        evidence_by_id: dict[str, Evidence],
    ) -> ProjectedFinding:
        original = original_findings.get(candidate.candidate_id)
        if original is None or not self._same_finding_except_type(original, candidate):
            raise DomainProjectionError("Admitted Finding 不是原始候选的受控版本。")
        if candidate.finding_type != original.finding_type and not (
            original.finding_type == "Fact" and candidate.finding_type == "Inference"
        ):
            raise DomainProjectionError("Admitted Finding 出现了未经允许的类型变更。")
        if not set(candidate.evidence_candidate_ids) <= set(evidence_by_id):
            raise DomainProjectionError("Admitted Finding 引用了未投影 Evidence。")
        evidence = [evidence_by_id[item_id] for item_id in candidate.evidence_candidate_ids]
        finding = Finding(
            finding_id=candidate.candidate_id,
            condition=candidate.condition_key,
            title=candidate.title,
            summary=candidate.summary,
            finding_type=candidate.finding_type,
            gate_critical=False,
            readiness_impact="Accepted candidate awaiting deterministic readiness adjudication.",
            evidence=evidence,
        )
        return ProjectedFinding(
            finding_candidate_id=candidate.candidate_id,
            evidence_candidate_ids=candidate.evidence_candidate_ids,
            primary_dimension_id=candidate.primary_dimension_id,
            related_dimension_ids=candidate.related_dimension_ids,
            criterion_id=candidate.criterion_id,
            readiness_effect=candidate.readiness_effect,
            finding=finding,
        )

    def _project_conflict(
        self,
        candidate: ConflictCandidate,
        original_conflicts: dict[str, ConflictCandidate],
        evidence_by_id: dict[str, Evidence],
    ) -> ProjectedConflict:
        original = original_conflicts.get(candidate.candidate_id)
        if original is None or original != candidate:
            raise DomainProjectionError("Admitted Conflict 必须与原始模型候选完全一致。")
        if not set(candidate.evidence_candidate_ids) <= set(evidence_by_id):
            raise DomainProjectionError("Admitted Conflict 引用了未投影 Evidence。")
        sources = [evidence_by_id[item_id] for item_id in candidate.evidence_candidate_ids]
        conflict = EvidenceConflict(
            conflict_id=candidate.candidate_id,
            condition_key=candidate.condition_key,
            dimension_ids=candidate.dimension_ids,
            summary=candidate.summary,
            gate_critical=False,
            status="unresolved",
            sources=sources,
        )
        return ProjectedConflict(
            conflict_candidate_id=candidate.candidate_id,
            evidence_candidate_ids=candidate.evidence_candidate_ids,
            criterion_id=candidate.criterion_id,
            disposition=candidate.disposition,
            conflict=conflict,
        )

    @staticmethod
    def _same_finding_except_type(
        original: FindingCandidate,
        admitted: FindingCandidate,
    ) -> bool:
        original_payload = original.model_dump()
        admitted_payload = admitted.model_dump()
        original_payload.pop("finding_type", None)
        admitted_payload.pop("finding_type", None)
        return original_payload == admitted_payload

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        return value if len(value) <= limit else value[:limit]
