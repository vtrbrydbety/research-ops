"""Deterministic admission of model-proposed Conflict and Finding candidates."""

from __future__ import annotations

from typing import Literal

from researchops.schemas.ai_analysis import (
    AIAnalysisAdjudicationResult,
    AIAnalysisResult,
    AIAnalysisValidationResult,
    CandidateGraphIssue,
    CandidateGraphIssueCode,
    ConflictCandidate,
    ConflictCandidateValidationResult,
    EvidenceCandidate,
    EvidenceValidationResult,
    FindingCandidate,
    FindingCandidateValidationResult,
)


class CandidateGraphValidationError(RuntimeError):
    """Analysis and Evidence validation inputs do not describe the same candidate graph."""


class DeterministicCandidateGraphValidator:
    """Admit only candidates backed by accepted, internally consistent Evidence."""

    def validate(
        self,
        analysis: AIAnalysisResult,
        evidence_validation: AIAnalysisValidationResult,
    ) -> AIAnalysisAdjudicationResult:
        self._validate_input_identity_and_completeness(analysis, evidence_validation)

        evidence_by_id = {
            candidate.candidate_id: candidate for candidate in analysis.evidence_candidates
        }
        validation_by_id = {
            result.evidence_candidate_id: result for result in evidence_validation.evidence_results
        }
        admitted_evidence_ids = [
            candidate.candidate_id
            for candidate in analysis.evidence_candidates
            if self._evidence_is_admissible(validation_by_id[candidate.candidate_id])
        ]

        conflict_results: list[ConflictCandidateValidationResult] = []
        admitted_conflicts: list[ConflictCandidate] = []
        for candidate in analysis.conflict_candidates:
            result = self._validate_conflict(candidate, evidence_by_id, validation_by_id)
            conflict_results.append(result)
            if result.decision == "accepted":
                admitted_conflicts.append(candidate)

        finding_results: list[FindingCandidateValidationResult] = []
        admitted_findings: list[FindingCandidate] = []
        for candidate in analysis.finding_candidates:
            result, admitted_candidate = self._validate_finding(
                candidate,
                evidence_by_id,
                validation_by_id,
            )
            finding_results.append(result)
            if admitted_candidate is not None:
                admitted_findings.append(admitted_candidate)

        human_confirmation_ids = [
            result.evidence_candidate_id
            for result in evidence_validation.evidence_results
            if result.decision == "needs_human_confirmation"
        ]
        human_confirmation_ids.extend(
            result.conflict_candidate_id
            for result in conflict_results
            if result.decision == "needs_human_confirmation"
        )
        human_confirmation_ids.extend(
            result.finding_candidate_id
            for result in finding_results
            if result.decision == "needs_human_confirmation"
        )

        return AIAnalysisAdjudicationResult(
            analysis_id=analysis.analysis_id,
            bundle_id=analysis.bundle_id,
            analysis_source_ids_verified=evidence_validation.analysis_source_ids_verified,
            analysis_issues=evidence_validation.analysis_issues,
            admitted_evidence_candidate_ids=admitted_evidence_ids,
            human_confirmation_candidate_ids=human_confirmation_ids,
            conflict_results=conflict_results,
            finding_results=finding_results,
            admitted_conflict_candidates=admitted_conflicts,
            admitted_finding_candidates=admitted_findings,
        )

    @staticmethod
    def _validate_input_identity_and_completeness(
        analysis: AIAnalysisResult,
        evidence_validation: AIAnalysisValidationResult,
    ) -> None:
        if (
            analysis.analysis_id != evidence_validation.analysis_id
            or analysis.bundle_id != evidence_validation.bundle_id
        ):
            raise CandidateGraphValidationError(
                "AIAnalysisResult 与 EvidenceValidationResult 身份不匹配。"
            )
        candidate_ids = {item.candidate_id for item in analysis.evidence_candidates}
        validation_ids = {
            item.evidence_candidate_id for item in evidence_validation.evidence_results
        }
        if candidate_ids != validation_ids:
            raise CandidateGraphValidationError(
                "每个 EvidenceCandidate 必须且只能具有一个 Rule 验证结果。"
            )

    def _validate_conflict(
        self,
        candidate: ConflictCandidate,
        evidence_by_id: dict[str, EvidenceCandidate],
        validation_by_id: dict[str, EvidenceValidationResult],
    ) -> ConflictCandidateValidationResult:
        referenced_ids = candidate.evidence_candidate_ids
        referenced_evidence = [evidence_by_id[item_id] for item_id in referenced_ids]
        referenced_validation = [validation_by_id[item_id] for item_id in referenced_ids]

        pending_ids = [
            item.evidence_candidate_id
            for item in referenced_validation
            if item.decision == "needs_human_confirmation"
        ]
        if pending_ids:
            return self._conflict_result(
                candidate,
                "needs_human_confirmation",
                "evidence_needs_human_confirmation",
                "Conflict 引用了仍需人工确认的 Evidence。",
                pending_ids,
            )

        unavailable_ids = [
            item.evidence_candidate_id
            for item in referenced_validation
            if item.decision == "rejected"
        ]
        if unavailable_ids:
            return self._conflict_result(
                candidate,
                "rejected",
                "evidence_not_accepted",
                "Conflict 引用了未被 Rule 层接受的 Evidence。",
                unavailable_ids,
            )

        non_fact_ids = [
            item.evidence_candidate_id
            for item in referenced_validation
            if item.decision == "downgraded" or item.resulting_type != "Fact"
        ]
        if non_fact_ids:
            return self._conflict_result(
                candidate,
                "needs_human_confirmation",
                "evidence_not_fact",
                "正式冲突至少需要两条已验证 Fact；Inference 或 Unknown 不得自动升级。",
                non_fact_ids,
            )

        mismatched_condition_ids = [
            item.candidate_id
            for item in referenced_evidence
            if item.condition_key.casefold() != candidate.condition_key.casefold()
        ]
        if mismatched_condition_ids:
            return self._conflict_result(
                candidate,
                "rejected",
                "condition_mismatch",
                "Conflict 与被引用 Evidence 不属于同一复现条件。",
                mismatched_condition_ids,
            )

        evidence_criteria = {item.criterion_id for item in referenced_evidence}
        if candidate.criterion_id is not None and evidence_criteria != {candidate.criterion_id}:
            return self._conflict_result(
                candidate,
                "rejected",
                "criterion_mismatch",
                "Conflict 与被引用 Evidence 的规范化 criterion 不一致。",
                candidate.evidence_candidate_ids,
            )

        evidence_dimensions = {
            dimension_id for item in referenced_evidence for dimension_id in item.dimension_ids
        }
        if not set(candidate.dimension_ids) <= evidence_dimensions:
            return self._conflict_result(
                candidate,
                "rejected",
                "dimension_mismatch",
                "Conflict 声明了引用 Evidence 未覆盖的 Readiness Dimension。",
                referenced_ids,
            )

        source_ids = {
            item.verified_locator.source_id
            for item in referenced_validation
            if item.verified_locator is not None
        }
        if len(source_ids) < 2:
            return self._conflict_result(
                candidate,
                "rejected",
                "insufficient_distinct_sources",
                "跨来源 Conflict 必须由至少两个不同来源支持。",
                referenced_ids,
            )

        normalized_claims = {
            " ".join(item.claim.casefold().split()) for item in referenced_evidence
        }
        if len(normalized_claims) < 2:
            return self._conflict_result(
                candidate,
                "rejected",
                "non_conflicting_evidence",
                "被引用 Evidence 的规范化 Claim 完全相同，不能据此建立冲突。",
                referenced_ids,
            )

        return ConflictCandidateValidationResult(
            conflict_candidate_id=candidate.candidate_id,
            decision="accepted",
        )

    def _validate_finding(
        self,
        candidate: FindingCandidate,
        evidence_by_id: dict[str, EvidenceCandidate],
        validation_by_id: dict[str, EvidenceValidationResult],
    ) -> tuple[FindingCandidateValidationResult, FindingCandidate | None]:
        if (candidate.criterion_id is None) != (candidate.readiness_effect is None):
            return self._finding_failure(
                candidate,
                "rejected",
                "criterion_mismatch",
                "Finding 的 canonical criterion 与 readiness effect 必须同时提供。",
                candidate.evidence_candidate_ids,
            )
        if candidate.criterion_id is not None:
            expected_prefix = candidate.primary_dimension_id.casefold().replace("-", "")
            if not candidate.criterion_id.startswith(f"{expected_prefix}."):
                return self._finding_failure(
                    candidate,
                    "rejected",
                    "criterion_mismatch",
                    "Finding criterion 不属于其 primary dimension。",
                    candidate.evidence_candidate_ids,
                )
            invalid_effect_type = (
                candidate.readiness_effect == "insufficient_or_conflicting"
                and candidate.finding_type != "Unknown"
            ) or (
                candidate.readiness_effect != "insufficient_or_conflicting"
                and candidate.finding_type == "Unknown"
            )
            if invalid_effect_type:
                return self._finding_failure(
                    candidate,
                    "rejected",
                    "finding_strength_downgraded",
                    "Finding 的 readiness effect 与 Fact/Inference/Unknown 类型不一致。",
                    candidate.evidence_candidate_ids,
                )
        if not candidate.evidence_candidate_ids:
            return (
                FindingCandidateValidationResult(
                    finding_candidate_id=candidate.candidate_id,
                    decision="accepted",
                    resulting_type="Unknown",
                ),
                candidate,
            )

        referenced_evidence = [
            evidence_by_id[item_id] for item_id in candidate.evidence_candidate_ids
        ]
        referenced_validation = [
            validation_by_id[item_id] for item_id in candidate.evidence_candidate_ids
        ]
        pending_ids = [
            item.evidence_candidate_id
            for item in referenced_validation
            if item.decision == "needs_human_confirmation"
        ]
        if pending_ids:
            return self._finding_failure(
                candidate,
                "needs_human_confirmation",
                "evidence_needs_human_confirmation",
                "Finding 引用了仍需人工确认的 Evidence。",
                pending_ids,
            )

        unavailable_ids = [
            item.evidence_candidate_id
            for item in referenced_validation
            if not self._evidence_is_admissible(item)
        ]
        if unavailable_ids:
            return self._finding_failure(
                candidate,
                "rejected",
                "evidence_not_accepted",
                "Finding 引用了未被 Rule 层接受的 Evidence。",
                unavailable_ids,
            )

        mismatched_condition_ids = [
            item.candidate_id
            for item in referenced_evidence
            if item.condition_key.casefold() != candidate.condition_key.casefold()
        ]
        if mismatched_condition_ids:
            return self._finding_failure(
                candidate,
                "rejected",
                "condition_mismatch",
                "Finding 与被引用 Evidence 不属于同一复现条件。",
                mismatched_condition_ids,
            )

        evidence_criteria = {item.criterion_id for item in referenced_evidence}
        if candidate.criterion_id is not None and evidence_criteria != {candidate.criterion_id}:
            return self._finding_failure(
                candidate,
                "rejected",
                "criterion_mismatch",
                "Finding 与被引用 Evidence 的规范化 criterion 不一致。",
                candidate.evidence_candidate_ids,
            )

        evidence_dimensions = {
            dimension_id for item in referenced_evidence for dimension_id in item.dimension_ids
        }
        if candidate.primary_dimension_id not in evidence_dimensions:
            return self._finding_failure(
                candidate,
                "rejected",
                "dimension_mismatch",
                "Finding 的 primary dimension 未被引用 Evidence 覆盖。",
                candidate.evidence_candidate_ids,
            )

        evidence_types = {item.resulting_type for item in referenced_validation}
        if "Unknown" in evidence_types and candidate.finding_type != "Unknown":
            return self._finding_failure(
                candidate,
                "rejected",
                "unknown_evidence_cannot_support_conclusion",
                "Unknown Evidence 不能自动支持 Fact 或 Inference Finding。",
                candidate.evidence_candidate_ids,
            )

        if candidate.finding_type == "Fact" and "Inference" in evidence_types:
            admitted_candidate = FindingCandidate.model_validate(
                {**candidate.model_dump(), "finding_type": "Inference"}
            )
            result = FindingCandidateValidationResult(
                finding_candidate_id=candidate.candidate_id,
                decision="downgraded",
                resulting_type="Inference",
                issues=[
                    CandidateGraphIssue(
                        code="finding_strength_downgraded",
                        message="Fact Finding 引用了 Inference Evidence，最高只能受理为 Inference。",
                        evidence_candidate_ids=candidate.evidence_candidate_ids,
                    )
                ],
            )
            return result, admitted_candidate

        return (
            FindingCandidateValidationResult(
                finding_candidate_id=candidate.candidate_id,
                decision="accepted",
                resulting_type=candidate.finding_type,
            ),
            candidate,
        )

    @staticmethod
    def _evidence_is_admissible(result: EvidenceValidationResult) -> bool:
        return (
            result.decision in {"accepted", "downgraded"}
            and result.resulting_type is not None
            and result.verified_locator is not None
        )

    @staticmethod
    def _conflict_result(
        candidate: ConflictCandidate,
        decision: Literal["accepted", "rejected", "needs_human_confirmation"],
        code: CandidateGraphIssueCode,
        message: str,
        evidence_ids: list[str],
    ) -> ConflictCandidateValidationResult:
        return ConflictCandidateValidationResult(
            conflict_candidate_id=candidate.candidate_id,
            decision=decision,
            issues=[
                CandidateGraphIssue(
                    code=code,
                    message=message,
                    evidence_candidate_ids=evidence_ids,
                )
            ],
        )

    @staticmethod
    def _finding_failure(
        candidate: FindingCandidate,
        decision: Literal["rejected", "needs_human_confirmation"],
        code: CandidateGraphIssueCode,
        message: str,
        evidence_ids: list[str],
    ) -> tuple[FindingCandidateValidationResult, None]:
        return (
            FindingCandidateValidationResult(
                finding_candidate_id=candidate.candidate_id,
                decision=decision,
                issues=[
                    CandidateGraphIssue(
                        code=code,
                        message=message,
                        evidence_candidate_ids=evidence_ids,
                    )
                ],
            ),
            None,
        )
