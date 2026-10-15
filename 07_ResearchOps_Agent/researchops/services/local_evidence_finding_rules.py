"""Deterministic admission for the locally scoped Evidence/Finding phase.

The AI phase produces only drafts.  This adapter gives those drafts stable
identities, validates every quoted source through the existing Rule validator,
and only then exposes them to the existing candidate graph, domain projection,
and readiness adjudication rules.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from researchops.schemas.ai_analysis import (
    AIAnalysisAdjudicationResult,
    AIAnalysisDomainProjection,
    AIAnalysisResult,
    AIAnalysisValidationResult,
    AIEvidenceFindingDraftResult,
    CandidateMerge,
    ConflictCandidate,
    ConflictDraft,
    EvidenceCandidate,
    EvidenceDraft,
    EvidenceFindingInput,
    FindingCandidate,
    FindingDraft,
    SourceLocator,
    UnresolvedQuestion,
)
from researchops.schemas.readiness import ReadinessAdjudicationResult
from researchops.services.candidate_adjudication import DeterministicCandidateGraphValidator
from researchops.services.domain_projection import ReadinessDomainProjectionService
from researchops.services.evidence_validation import DeterministicEvidenceRuleValidator
from researchops.services.readiness_adjudication import DeterministicReadinessAdjudicator

_READINESS_CRITERIA = {
    "rd01.dataset_identity",
    "rd01.dataset_access",
    "rd01.input_contract",
    "rd02.software_requirements",
    "rd02.dependency_requirements",
    "rd02.environment_compatibility",
    "rd03.checkpoint_access",
    "rd03.configuration_mapping",
    "rd03.execution_contract",
    "resource.minimum_requirements",
    "resource.current_capacity",
    "evaluation.dataset_split",
    "evaluation.metric_definition",
    "evaluation.aggregation",
    "evaluation.paper_code_setting",
    "evaluation.protocol",
}


@dataclass(frozen=True, slots=True)
class RuleGapResolution:
    """Concrete, deterministic status for a Gap in the current local scope."""

    gap_ref: str
    state: str
    reason: str


@dataclass(frozen=True, slots=True)
class LocalDraftRuleIssue:
    """A model draft defect retained as a Rule explanation, never an exception path."""

    local_ref: str
    reason: str


@dataclass(frozen=True, slots=True)
class LocalEvidenceFindingRuleOutcome:
    """Rule-owned result before workflow merges it into the retained assessment."""

    analysis: AIAnalysisResult
    evidence_validation: AIAnalysisValidationResult
    candidate_adjudication: AIAnalysisAdjudicationResult
    projection: AIAnalysisDomainProjection
    readiness: ReadinessAdjudicationResult
    stable_id_by_local_ref: dict[str, str]
    gap_resolutions: tuple[RuleGapResolution, ...]
    merges: tuple[CandidateMerge, ...]
    rule_issues: tuple[LocalDraftRuleIssue, ...]


class LocalEvidenceFindingRuleService:
    """Validate a local draft without restoring the old global Coverage contract."""

    def __init__(
        self,
        *,
        evidence_validator: DeterministicEvidenceRuleValidator | None = None,
        candidate_validator: DeterministicCandidateGraphValidator | None = None,
        projector: ReadinessDomainProjectionService | None = None,
        readiness_adjudicator: DeterministicReadinessAdjudicator | None = None,
    ) -> None:
        self._evidence_validator = evidence_validator or DeterministicEvidenceRuleValidator()
        self._candidate_validator = candidate_validator or DeterministicCandidateGraphValidator()
        self._projector = projector or ReadinessDomainProjectionService()
        self._readiness_adjudicator = readiness_adjudicator or DeterministicReadinessAdjudicator()

    def adjudicate(
        self,
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
    ) -> LocalEvidenceFindingRuleOutcome:
        """Apply the same rules to the same local AI Draft every time."""
        analysis_id = self._analysis_id(context, draft)
        evidence, stable_ids, rule_issues = self._evidence_candidates(context, draft)
        findings, finding_merges, finding_issues = self._finding_candidates(
            context, draft, stable_ids
        )
        conflicts, conflict_merges, conflict_issues = self._conflict_candidates(
            context, draft, stable_ids
        )
        questions, gap_issues = self._remaining_gap_questions(context, draft)
        examined_source_ids = self._examined_source_ids(context)

        analysis = AIAnalysisResult(
            analysis_id=analysis_id,
            bundle_id=context.bundle.bundle_id,
            summary="Rule-adapted locally scoped Evidence/Finding draft.",
            examined_source_ids=examined_source_ids,
            evidence_candidates=evidence,
            conflict_candidates=conflicts,
            finding_candidates=findings,
            unresolved_questions=questions,
        )
        evidence_validation = self._evidence_validator.validate(context.bundle, analysis)
        candidate_adjudication = self._candidate_validator.validate(analysis, evidence_validation)
        projection = self._projector.project(
            context.bundle,
            analysis,
            evidence_validation,
            candidate_adjudication,
        )
        readiness = self._readiness_adjudicator.adjudicate(projection)
        return LocalEvidenceFindingRuleOutcome(
            analysis=analysis,
            evidence_validation=evidence_validation,
            candidate_adjudication=candidate_adjudication,
            projection=projection,
            readiness=readiness,
            stable_id_by_local_ref=stable_ids,
            gap_resolutions=self._gap_resolutions(context, draft, evidence_validation, stable_ids),
            merges=tuple([*finding_merges, *conflict_merges]),
            rule_issues=tuple(
                [*rule_issues, *finding_issues, *conflict_issues, *gap_issues]
            ),
        )

    @staticmethod
    def _analysis_id(
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
    ) -> UUID:
        payload = {
            "bundle_id": str(context.bundle.bundle_id),
            "focus": context.focus.model_dump(mode="json"),
            "conditions": [item.model_dump(mode="json") for item in context.condition_contexts],
            "gaps": [item.model_dump(mode="json") for item in context.current_information_gaps],
            "sources": context.relevant_source_ids,
            "draft": draft.model_dump(mode="json"),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return uuid5(NAMESPACE_URL, f"researchops/local-rule/{encoded}")

    def _evidence_candidates(
        self,
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
    ) -> tuple[list[EvidenceCandidate], dict[str, str], list[LocalDraftRuleIssue]]:
        condition_contexts = {item.condition_ref: item for item in context.condition_contexts}
        # ``related_evidence`` is trusted retained state, not a newly model-
        # proposed identity.  Preserve its current stable ID so a feedback
        # revision cannot break Evidence drawer links from the prior revision.
        all_drafts = [
            *( (item, True) for item in context.related_evidence ),
            *( (item, False) for item in draft.evidence_drafts ),
        ]
        stable_ids: dict[str, str] = {}
        candidates_by_id: dict[str, EvidenceCandidate] = {}
        issues: list[LocalDraftRuleIssue] = []
        seen_local_refs: set[str] = set()
        for item, is_retained in all_drafts:
            if item.local_evidence_id in seen_local_refs:
                issues.append(
                    LocalDraftRuleIssue(
                        item.local_evidence_id,
                        "Evidence Draft local_evidence_id is duplicated in the local Rule scope.",
                    )
                )
                continue
            seen_local_refs.add(item.local_evidence_id)
            condition_ref, issue = self._single_condition_ref(item, condition_contexts)
            if issue is not None:
                issues.append(LocalDraftRuleIssue(item.local_evidence_id, issue))
                continue
            stable_id = (
                item.local_evidence_id
                if is_retained
                else self._stable_evidence_id(item, condition_ref)
            )
            stable_ids[item.local_evidence_id] = stable_id
            if stable_id in candidates_by_id:
                continue
            condition = condition_contexts[condition_ref]
            candidates_by_id[stable_id] = EvidenceCandidate(
                candidate_id=stable_id,
                condition_key=condition_ref,
                criterion_id=(condition_ref if condition_ref in _READINESS_CRITERIA else None),
                dimension_ids=[condition.primary_dimension, *condition.related_dimensions],
                evidence_type=item.evidence_type,
                claim=item.claim,
                locator=SourceLocator(
                    source_id=item.source_ref,
                    location=item.location,
                    line_start=item.line_start,
                    line_end=item.line_end,
                ),
                quote=item.quote,
                confidence=0.5,
                rationale="Local Draft submitted for deterministic provenance validation.",
                uncertainty_reason=(
                    item.conflict_note or "The scoped material is ambiguous."
                    if item.evidence_type == "Unknown"
                    else None
                ),
            )
        return list(candidates_by_id.values()), stable_ids, issues

    @staticmethod
    def _single_condition_ref(
        item: EvidenceDraft,
        contexts: dict[str, object],
    ) -> tuple[str | None, str | None]:
        if len(item.condition_refs) != 1:
            return (
                None,
                "Evidence Draft must declare exactly one current condition_ref before Rule admission.",
            )
        condition_ref = item.condition_refs[0]
        if condition_ref not in contexts:
            return None, "Evidence Draft references a condition outside the current Rule scope."
        return condition_ref, None

    @staticmethod
    def _stable_evidence_id(item: EvidenceDraft, condition_ref: str) -> str:
        fingerprint = "\x1f".join(
            (
                condition_ref,
                item.source_ref,
                item.location,
                str(item.line_start),
                str(item.line_end),
                item.quote,
            )
        )
        return "evd-" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:20]

    def _finding_candidates(
        self,
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
        stable_ids: dict[str, str],
    ) -> tuple[list[FindingCandidate], list[CandidateMerge], list[LocalDraftRuleIssue]]:
        contexts = {item.condition_ref: item for item in context.condition_contexts}
        grouped: dict[str, list[FindingDraft]] = {}
        issues: list[LocalDraftRuleIssue] = []
        # Retained Findings are Rule inputs, not a request for the model to
        # rediscover unrelated material.  A local update may replace one of
        # these only when it has the same deterministic root-cause key.
        for item in [*context.related_findings, *draft.finding_drafts]:
            condition = contexts.get(item.condition)
            if condition is None:
                issues.append(
                    LocalDraftRuleIssue(
                        item.local_finding_id,
                        "Finding Draft references a condition outside the current Rule scope.",
                    )
                )
                continue
            if (
                item.primary_dimension != condition.primary_dimension
                or item.related_dimensions != condition.related_dimensions
            ):
                issues.append(
                    LocalDraftRuleIssue(
                        item.local_finding_id,
                        "Finding Draft dimensions do not match the supplied Condition Context.",
                    )
                )
                continue
            root_key = f"{item.condition}|{condition.primary_dimension}"
            grouped.setdefault(root_key, []).append(item)

        findings: list[FindingCandidate] = []
        merges: list[CandidateMerge] = []
        for root_key, group in sorted(grouped.items()):
            canonical = min(
                group,
                key=lambda item: (
                    item.operation != "update_existing",
                    item.local_finding_id,
                ),
            )
            condition = contexts[canonical.condition]
            requested_refs = {
                ref for item in group for ref in item.evidence_refs_local
            }
            missing_refs = requested_refs - set(stable_ids)
            evidence_ids = self._ordered_unique(
                stable_ids[ref]
                for item in group
                for ref in item.evidence_refs_local
                if ref in stable_ids
            )
            candidate_id = (
                canonical.existing_finding_ref
                if canonical.operation == "update_existing"
                else "fnd-" + hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:20]
            )
            finding_type = (
                "Unknown"
                if missing_refs
                else self._weakest_finding_type(item.finding_type for item in group)
            )
            if missing_refs:
                issues.append(
                    LocalDraftRuleIssue(
                        canonical.local_finding_id,
                        "Finding Draft referenced Evidence that Rule could not resolve: "
                        + ", ".join(sorted(missing_refs)),
                    )
                )
                # A Finding that names an unresolved Evidence reference cannot
                # be repaired by silently discarding that relationship.  Keep a
                # Rule issue and its Gap instead of admitting a partial claim.
                continue
            findings.append(
                FindingCandidate(
                    candidate_id=candidate_id,
                    root_cause_key=root_key,
                    condition_key=canonical.condition,
                    criterion_id=(
                        canonical.condition
                        if canonical.condition in _READINESS_CRITERIA
                        else None
                    ),
                    readiness_effect=self._readiness_effect(finding_type),
                    primary_dimension_id=condition.primary_dimension,
                    related_dimension_ids=condition.related_dimensions,
                    title=f"Rule-reviewed {canonical.condition}",
                    summary=min(item.summary for item in group),
                    finding_type=finding_type,
                    evidence_candidate_ids=evidence_ids,
                    uncertainty_reason=(
                        "The local draft is Unknown or conflicting."
                        if finding_type == "Unknown"
                        else None
                    ),
                )
            )
            if len(group) > 1:
                merges.append(
                    CandidateMerge(
                        candidate_kind="finding",
                        canonical_candidate_id=candidate_id,
                        merged_candidate_ids=sorted(item.local_finding_id for item in group),
                        merge_key=root_key,
                    )
                )
        return findings, merges, issues

    def _conflict_candidates(
        self,
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
        stable_ids: dict[str, str],
    ) -> tuple[list[ConflictCandidate], list[CandidateMerge], list[LocalDraftRuleIssue]]:
        contexts = {item.condition_ref: item for item in context.condition_contexts}
        grouped: dict[str, list[ConflictDraft]] = {}
        issues: list[LocalDraftRuleIssue] = []
        for item in draft.conflict_drafts:
            condition = contexts.get(item.condition_ref)
            if condition is None:
                issues.append(
                    LocalDraftRuleIssue(
                        item.local_conflict_id,
                        "Conflict Draft references a condition outside the current Rule scope.",
                    )
                )
                continue
            if (
                item.primary_dimension != condition.primary_dimension
                or item.related_dimensions != condition.related_dimensions
            ):
                issues.append(
                    LocalDraftRuleIssue(
                        item.local_conflict_id,
                        "Conflict Draft dimensions do not match the supplied Condition Context.",
                    )
                )
                continue
            root_key = f"{item.condition_ref}|{item.primary_dimension}"
            grouped.setdefault(root_key, []).append(item)

        conflicts: list[ConflictCandidate] = []
        merges: list[CandidateMerge] = []
        for root_key, group in sorted(grouped.items()):
            canonical = min(group, key=lambda item: item.local_conflict_id)
            evidence_ids = self._ordered_unique(
                stable_ids[ref]
                for item in group
                for ref in [*item.local_evidence_refs, *item.related_existing_evidence_refs]
                if ref in stable_ids
            )
            candidate_id = "cfl-" + hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:20]
            if len(evidence_ids) < 2:
                issues.append(
                    LocalDraftRuleIssue(
                        canonical.local_conflict_id,
                        "Conflict Draft did not retain two Rule-resolvable Evidence references.",
                    )
                )
                continue
            conflicts.append(
                ConflictCandidate(
                    candidate_id=candidate_id,
                    conflict_key=root_key,
                    condition_key=canonical.condition_ref,
                    criterion_id=(
                        canonical.condition_ref
                        if canonical.condition_ref in _READINESS_CRITERIA
                        else None
                    ),
                    disposition=(
                        "authoritative_value_unresolved"
                        if canonical.condition_ref in _READINESS_CRITERIA
                        else None
                    ),
                    dimension_ids=[
                        canonical.primary_dimension,
                        *canonical.related_dimensions,
                    ],
                    summary=min(item.summary for item in group),
                    evidence_candidate_ids=evidence_ids,
                    confidence=0.0,
                    uncertainty_reason="Rule must retain both conflict sides until resolved.",
                )
            )
            if len(group) > 1:
                merges.append(
                    CandidateMerge(
                        candidate_kind="conflict",
                        canonical_candidate_id=candidate_id,
                        merged_candidate_ids=sorted(item.local_conflict_id for item in group),
                        merge_key=root_key,
                    )
                )
        return conflicts, merges, issues

    def _remaining_gap_questions(
        self,
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
    ) -> tuple[list[UnresolvedQuestion], list[LocalDraftRuleIssue]]:
        gaps = {item.gap_id: item for item in context.current_information_gaps}
        conditions = {item.condition_ref: item for item in context.condition_contexts}
        questions: list[UnresolvedQuestion] = []
        issues: list[LocalDraftRuleIssue] = []
        for item in draft.remaining_information_gaps:
            gap = gaps.get(item.gap_ref)
            if gap is None:
                issues.append(
                    LocalDraftRuleIssue(
                        item.gap_ref,
                        "Remaining Gap references a Gap outside the current Rule scope.",
                    )
                )
                continue
            matching = next(
                (
                    condition
                    for condition in conditions.values()
                    if condition.primary_dimension == gap.scope_ref
                ),
                next(iter(conditions.values())),
            )
            questions.append(
                UnresolvedQuestion(
                    question_id="gap-"
                    + hashlib.sha256(gap.gap_id.encode("utf-8")).hexdigest()[:20],
                    condition_key=matching.condition_ref,
                    criterion_id=(
                        matching.condition_ref
                        if matching.condition_ref in _READINESS_CRITERIA
                        else None
                    ),
                    dimension_id=matching.primary_dimension,
                    question=gap.question,
                    missing_information=item.reason,
                    inspected_source_ids=context.relevant_source_ids,
                )
            )
        return questions, issues

    @staticmethod
    def _examined_source_ids(context: EvidenceFindingInput) -> list[str]:
        return LocalEvidenceFindingRuleService._ordered_unique(
            [
                *context.relevant_source_ids,
                *(item.source_ref for item in context.related_evidence),
            ]
        )

    @staticmethod
    def _gap_resolutions(
        context: EvidenceFindingInput,
        draft: AIEvidenceFindingDraftResult,
        validation: AIAnalysisValidationResult,
        stable_ids: dict[str, str],
    ) -> tuple[RuleGapResolution, ...]:
        unresolved = {item.gap_ref: item.reason for item in draft.remaining_information_gaps}
        validation_by_id = {
            item.evidence_candidate_id: item for item in validation.evidence_results
        }
        resolutions: list[RuleGapResolution] = []
        for gap in context.current_information_gaps:
            if gap.gap_id in unresolved:
                resolutions.append(
                    RuleGapResolution(gap.gap_id, "unresolved", unresolved[gap.gap_id])
                )
                continue
            linked_ids = {
                stable_ids[ref]
                for finding in draft.finding_drafts
                if gap.gap_id in finding.source_gap_refs
                for ref in finding.evidence_refs_local
                if ref in stable_ids
            }
            accepted = [
                item for item in linked_ids if validation_by_id.get(item) is not None
                and validation_by_id[item].decision in {"accepted", "downgraded"}
            ]
            if accepted:
                resolutions.append(
                    RuleGapResolution(
                        gap.gap_id,
                        "resolved_by_verified_evidence",
                        "A linked Evidence Draft passed deterministic source, quote, and location validation.",
                    )
                )
            else:
                resolutions.append(
                    RuleGapResolution(
                        gap.gap_id,
                        "unresolved",
                        "No linked Evidence Draft passed deterministic validation for this Gap.",
                    )
                )
        return tuple(resolutions)

    @staticmethod
    def _ordered_unique(values) -> list[str]:
        return list(dict.fromkeys(values))

    @staticmethod
    def _weakest_finding_type(types) -> str:
        values = set(types)
        if "Unknown" in values:
            return "Unknown"
        if "Inference" in values:
            return "Inference"
        return "Fact"

    @staticmethod
    def _readiness_effect(finding_type: str) -> str:
        return (
            "condition_supported"
            if finding_type == "Fact"
            else "insufficient_or_conflicting"
        )
