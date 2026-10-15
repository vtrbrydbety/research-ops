"""Human feedback, reassessment, and final-decision boundary for model-backed Readiness."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from researchops.core.access_context import authorize_resource, bind_resource
from researchops.core.config import Settings, get_settings
from researchops.schemas import (
    AIAnalysisResult,
    AIEvidenceExtractionResult,
    AIFeedbackReassessmentResult,
    AssessmentFeedbackRequest,
    AssessmentFeedbackResponse,
    AssessmentRequest,
    AssessmentRevision,
    AssessmentRevisionChange,
    AssessmentRevisionHistory,
    CollectedMaterial,
    EvidenceAreaCoverage,
    EvidenceDraft,
    EvidenceFindingConditionContext,
    EvidenceFindingInput,
    FinalInvestmentDecisionRecord,
    FinalInvestmentDecisionRequest,
    FindingDraft,
    HumanFeedback,
    HumanReviewContext,
    MaterialBundle,
    NextAction,
    PhaseInformationGap,
    ReadinessAdjudicationResult,
    ReadinessAssessment,
    ReadinessDimension,
    SourceLocator,
)
from researchops.services.analysis_boundaries import (
    EvidenceFindingDraftModel,
    FeedbackReassessmentModel,
    ResearchLoopRunner,
)
from researchops.services.assessment_review_store import (
    AssessmentReviewStore,
)
from researchops.services.candidate_adjudication import (
    CandidateGraphValidationError,
    DeterministicCandidateGraphValidator,
)
from researchops.services.decision_audit import (
    append_final_decision_audit,
    append_human_feedback_audit,
    build_assessment_audit,
)
from researchops.services.deepseek_analysis import (
    AIModelConfigurationError,
    AIModelError,
    AIModelResponseError,
)
from researchops.services.domain_projection import (
    DomainProjectionError,
    ReadinessDomainProjectionService,
)
from researchops.services.evidence_validation import (
    DeterministicEvidenceRuleValidator,
    EvidenceRuleValidationError,
)
from researchops.services.gate_decision import GateDecisionService
from researchops.services.local_evidence_finding_rules import LocalEvidenceFindingRuleService
from researchops.services.material_context import MaterialBundleBuilder, MaterialContextError
from researchops.services.readiness_adjudication import DeterministicReadinessAdjudicator
from researchops.services.readiness_assessment import ReadinessAssessmentService


class AssessmentReviewNotFoundError(LookupError):
    """The retained review state is absent, corrupt, or expired."""


class AssessmentFeedbackTargetError(ValueError):
    """Feedback references an object outside the retained Assessment graph."""


@dataclass(slots=True)
class AssessmentReviewSession:
    assessment_id: UUID
    state: dict[str, Any]
    revision: int = 0
    revisions: list[AssessmentRevision] = field(default_factory=list)
    feedback: list[HumanFeedback] = field(default_factory=list)
    final_decisions: list[FinalInvestmentDecisionRecord] = field(default_factory=list)


class InMemoryAssessmentReviewStore:
    """TTL-bounded test/local store with sliding expiration."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        ttl_seconds: float | None = None,
        max_entries: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        config = settings or get_settings()
        self.ttl_seconds = ttl_seconds or config.assessment_review_ttl_seconds
        self.max_entries = max_entries or config.llm_analysis_run_max_entries
        self._clock = clock
        self._lock = RLock()
        self._sessions: OrderedDict[UUID, tuple[float, AssessmentReviewSession]] = OrderedDict()

    def save(self, session: AssessmentReviewSession) -> None:
        with self._lock:
            now = self._clock()
            self._prune(now)
            self._sessions.pop(session.assessment_id, None)
            while len(self._sessions) >= self.max_entries:
                self._sessions.popitem(last=False)
            self._sessions[session.assessment_id] = (
                now + self.ttl_seconds,
                deepcopy(session),
            )

    def get(self, assessment_id: UUID) -> AssessmentReviewSession | None:
        with self._lock:
            now = self._clock()
            self._prune(now)
            stored = self._sessions.get(assessment_id)
            if stored is None:
                return None
            # Reading the active Assessment or submitting feedback keeps the
            # review session alive for one more bounded retention window.
            self._sessions.move_to_end(assessment_id)
            self._sessions[assessment_id] = (
                now + self.ttl_seconds,
                stored[1],
            )
            return deepcopy(stored[1])

    def _prune(self, now: float) -> None:
        for assessment_id in [
            key for key, (expires_at, _) in self._sessions.items() if expires_at <= now
        ]:
            self._sessions.pop(assessment_id, None)


class HumanReviewService:
    """Apply Human overlays without allowing them to bypass Evidence or Gate rules."""

    def __init__(
        self,
        *,
        assessment_service: ReadinessAssessmentService,
        evidence_model: EvidenceFindingDraftModel,
        feedback_model: FeedbackReassessmentModel | None = None,
        research_loop: ResearchLoopRunner | None = None,
        store: AssessmentReviewStore | None = None,
        material_builder: MaterialBundleBuilder | None = None,
    ) -> None:
        self.assessment_service = assessment_service
        self.evidence_model = evidence_model
        self.feedback_model = feedback_model
        self.research_loop = research_loop
        self.store = store or InMemoryAssessmentReviewStore()
        self.material_builder = material_builder or MaterialBundleBuilder()
        self.evidence_validator = DeterministicEvidenceRuleValidator()
        self.candidate_validator = DeterministicCandidateGraphValidator()
        self.projector = ReadinessDomainProjectionService()
        self.readiness_adjudicator = DeterministicReadinessAdjudicator()
        self.local_evidence_finding_rules = LocalEvidenceFindingRuleService()

    def register(self, state: dict[str, Any]) -> ReadinessAssessment:
        assessment = ReadinessAssessment.model_validate(state["assessment"])
        retained_state = deepcopy(state)
        request = retained_state.get("request")
        if request is not None:
            # The completed MaterialBundle already contains the bounded,
            # redacted environment facts required for review.  Short-lived
            # authorization tokens and raw environment input are never part
            # of the recoverable session.
            retained_state["request"] = AssessmentRequest.model_validate(request).model_copy(
                update={
                    "environment_authorized": False,
                    "environment_authorization_token": None,
                    "environment_input": None,
                }
            )
        initial_revision = AssessmentRevision(
            revision=0,
            created_at=datetime.now(UTC),
            assessment=assessment.model_copy(deep=True),
        )
        self.store.save(
            AssessmentReviewSession(
                assessment_id=assessment.assessment_id,
                state=retained_state,
                revisions=[initial_revision],
            )
        )
        bind_resource("assessment", assessment.assessment_id)
        return assessment

    def get_assessment(self, assessment_id: UUID) -> ReadinessAssessment:
        """Return the latest stored adjudicated revision without internal source material."""

        session = self._required_session(assessment_id)
        return ReadinessAssessment.model_validate(session.state["assessment"])

    def get_revision_history(self, assessment_id: UUID) -> AssessmentRevisionHistory:
        """Return immutable assessment snapshots with deterministic adjacent diffs."""

        session = self._required_session(assessment_id)
        revisions = [item.model_copy(deep=True) for item in session.revisions]
        return AssessmentRevisionHistory(
            assessment_id=assessment_id,
            revisions=revisions,
            changes=[
                self._revision_change(previous, current)
                for previous, current in zip(revisions, revisions[1:], strict=False)
            ],
        )

    def submit_feedback(
        self,
        assessment_id: UUID,
        request: AssessmentFeedbackRequest,
    ) -> AssessmentFeedbackResponse:
        session = self._required_session(assessment_id)
        self._validate_target(session.state, request)
        revision = session.revision + 1
        requires_reassessment = self._requires_reassessment(request)
        feedback = HumanFeedback(
            feedback_id=uuid4(),
            assessment_id=assessment_id,
            revision=revision,
            target_type=request.target_type,
            target_id=request.target_id,
            action=request.action,
            comment=request.comment,
            requires_reassessment=requires_reassessment,
            submitted_at=datetime.now(UTC),
        )
        session.revision = revision
        session.feedback.append(feedback)

        if not requires_reassessment:
            assessment = ReadinessAssessment.model_validate(session.state["assessment"])
            assessment = assessment.model_copy(
                update={
                    "audit_trail": append_human_feedback_audit(
                        assessment.audit_trail,
                        feedback,
                    )
                }
            )
            session.state["assessment"] = ReadinessAssessment.model_validate(assessment)
            self._append_revision(session, assessment, feedback)
            self.store.save(session)
            return self._response(session, feedback, False, "not_required")

        try:
            state = self._reassess(session.state, request, feedback)
        except AIModelConfigurationError:
            self._append_current_revision(session, feedback)
            self.store.save(session)
            return self._response(session, feedback, False, "configuration_required")
        except AIModelResponseError as exc:
            self._append_current_revision(session, feedback)
            self.store.save(session)
            return self._response(
                session,
                feedback,
                False,
                "invalid_model_response",
                detail=self._safe_reassessment_detail(exc),
            )
        except AIModelError:
            self._append_current_revision(session, feedback)
            self.store.save(session)
            return self._response(session, feedback, False, "model_unavailable")
        except (
            CandidateGraphValidationError,
            DomainProjectionError,
            EvidenceRuleValidationError,
            MaterialContextError,
            ValueError,
        ):
            self._append_current_revision(session, feedback)
            self.store.save(session)
            return self._response(session, feedback, False, "evidence_validation_failure")

        session.state = state
        self._append_revision(
            session,
            ReadinessAssessment.model_validate(state["assessment"]),
            feedback,
        )
        self.store.save(session)
        assessment = ReadinessAssessment.model_validate(state["assessment"])
        return self._response(session, feedback, True, "completed")

    def record_final_decision(
        self,
        assessment_id: UUID,
        request: FinalInvestmentDecisionRequest,
    ) -> FinalInvestmentDecisionRecord:
        session = self._required_session(assessment_id)
        assessment = ReadinessAssessment.model_validate(session.state["assessment"])
        record = FinalInvestmentDecisionRecord(
            decision_id=uuid4(),
            assessment_id=assessment_id,
            revision=session.revision,
            decision=request.decision,
            rationale=request.rationale,
            rule_gate_at_decision=assessment.overall_gate,
            gate_available_at_decision=assessment.gate_available,
            submitted_at=datetime.now(UTC),
        )
        assessment = assessment.model_copy(
            update={
                "audit_trail": append_final_decision_audit(
                    assessment.audit_trail,
                    record,
                )
            }
        )
        session.state["assessment"] = ReadinessAssessment.model_validate(assessment)
        session.final_decisions.append(record)
        self.store.save(session)
        return record

    def _reassess(
        self,
        state: dict[str, Any],
        request: AssessmentFeedbackRequest,
        feedback: HumanFeedback,
    ) -> dict[str, Any]:
        revised = deepcopy(state)
        trace = [
            *ReadinessAssessment.model_validate(state["assessment"]).trace_summary,
            (
                f"human_feedback: revision={feedback.revision}, action={feedback.action}, "
                f"target={feedback.target_type}:{feedback.target_id}."
            ),
        ]
        review_context = self._review_context(state, request)

        original_bundle = state["material_bundle"]
        if request.source_submission is not None:
            bundle = self._augment_bundle(
                state["material_bundle"],
                request,
                review_context,
            )
        else:
            # Research Planning receives the exact Human context before deciding
            # whether a bounded read can close a newly exposed information gap.
            bundle = original_bundle.model_copy(
                deep=True,
                update={"human_review_context": review_context.model_copy(deep=True)},
            )
        retained_bundle = bundle.model_copy(deep=True)

        if self.feedback_model is None:
            raise AIModelConfigurationError(
                "Feedback reassessment requires an AI model that implements reassess_feedback."
            )
        feedback_reassessment = None
        try:
            feedback_reassessment = self.feedback_model.reassess_feedback(bundle)
            self._validate_feedback_reassessment_scope(
                state,
                request,
                review_context,
                feedback_reassessment.result,
            )
        except AIModelResponseError:
            # The user explicitly selected the target and supplied a new
            # source.  A malformed *scoping* response must not discard that
            # source or prevent the later Evidence/Conflict AI stages from
            # analysing it with the entire retained material set.  This is not
            # a guessed scope: it is the user-selected target, and the trace
            # makes the degraded handoff visible for audit.
            if request.source_submission is None:
                raise
            trace.append(
                "ai_feedback_reassessment: invalid response; continued with the "
                "user-selected target and supplied source for evidence analysis."
            )
        if feedback_reassessment is not None:
            revised["feedback_reassessment"] = feedback_reassessment
            trace.append(
                "ai_feedback_reassessment: success - "
                f"handoff={feedback_reassessment.result.handoff}, "
                f"findings={len(feedback_reassessment.result.affected_scope.finding_refs)}, "
                f"gaps={len(feedback_reassessment.result.information_gaps)}."
            )
        affected_dimensions = self._feedback_dimensions(
            review_context,
            feedback_reassessment.result if feedback_reassessment is not None else None,
        )
        bundle = self._scoped_feedback_bundle(
            state,
            bundle,
            affected_dimensions=affected_dimensions,
        )
        trace.append(
            "human_feedback_scope: dimensions="
            f"{','.join(affected_dimensions)}; sources={len(bundle.sources)}."
        )
        if (
            feedback_reassessment is not None
            and feedback_reassessment.result.handoff == "no_change"
        ):
            previous = ReadinessAssessment.model_validate(state["assessment"])
            revised["assessment"] = previous.model_copy(
                update={
                    "audit_trail": append_human_feedback_audit(
                        previous.audit_trail,
                        feedback,
                    ),
                    "trace_summary": trace,
                }
            )
            revised["workflow_trace"] = trace
            return revised
        if (
            self.research_loop is not None
            and feedback_reassessment is not None
            and feedback_reassessment.result.handoff == "tool_acquisition"
        ):
            research_result = self.research_loop.run(
                bundle,
                local_environment_authorized=state["request"].environment_authorized,
            )
            # A deterministic executor may rebuild the bundle. Preserve the
            # feedback context for the downstream Evidence and Finding stages.
            bundle = research_result.final_bundle.model_copy(
                deep=True,
                update={"human_review_context": review_context.model_copy(deep=True)},
            )
            revised["research_loop"] = research_result
            trace.append(
                "human_research_materials: completed - "
                f"rounds={len(research_result.rounds)}, "
                f"tool_requests={research_result.tool_requests_used}, "
                f"stop={research_result.stop_reason}."
            )

        if review_context.original_finding is not None and callable(
            getattr(self.evidence_model, "draft_evidence_findings", None)
        ):
            return self._reassess_local_feedback(
                state=state,
                revised=revised,
                request=request,
                feedback=feedback,
                bundle=bundle,
                retained_bundle=retained_bundle,
                review_context=review_context,
                feedback_reassessment=feedback_reassessment,
                affected_dimensions=affected_dimensions,
                trace=trace,
            )
        # The former all-material Evidence/Conflict fallback is deliberately
        # disabled. A feedback target without a resolvable local Finding must
        # be surfaced for correction instead of silently re-running the entire
        # repository through the retired global prompt path.
        raise AIModelResponseError(
            "Feedback scope could not be mapped to a local Finding/Evidence context; legacy full-material reassessment is disabled."
        )

    def _reassess_local_feedback(
        self,
        *,
        state: dict[str, Any],
        revised: dict[str, Any],
        request: AssessmentFeedbackRequest,
        feedback: HumanFeedback,
        bundle: MaterialBundle,
        retained_bundle: MaterialBundle,
        review_context: HumanReviewContext,
        feedback_reassessment,
        affected_dimensions: tuple[str, ...],
        trace: list[str],
    ) -> dict[str, Any]:
        """Run the PA-04/05 local pipeline for one feedback dependency scope.

        The model sees only target-linked retained material, user material, and
        tool material.  Rule then replaces only those Conditions in the retained
        candidate graph and adjudicates the complete graph for the Overall Gate.
        """

        local_input = self._build_local_feedback_input(
            state,
            bundle,
            review_context,
            feedback_reassessment.result if feedback_reassessment is not None else None,
            affected_dimensions,
        )
        draft_invocation = self.evidence_model.draft_evidence_findings(local_input)
        local_outcome = self.local_evidence_finding_rules.adjudicate(
            local_input,
            draft_invocation.result,
        )
        trace.append(self._model_trace("human_local_evidence_finding", draft_invocation.trace))
        trace.append(
            "human_local_rule: "
            f"accepted_evidence={len(local_outcome.candidate_adjudication.admitted_evidence_candidate_ids)}, "
            f"rule_issues={len(local_outcome.rule_issues)}, "
            f"gaps={len(local_outcome.gap_resolutions)}."
        )

        full_bundle = self._merge_retained_bundle(retained_bundle, bundle)
        merged_analysis = self._merge_local_rule_analysis(
            state,
            local_outcome.analysis,
            full_bundle,
            {item.condition_ref for item in local_input.condition_contexts},
        )
        validation = self.evidence_validator.validate(full_bundle, merged_analysis)
        candidate_adjudication = self.candidate_validator.validate(merged_analysis, validation)
        projection = self.projector.project(
            full_bundle,
            merged_analysis,
            validation,
            candidate_adjudication,
        )

        scope_signals = (
            set(feedback_reassessment.result.affected_scope.signal_refs)
            if feedback_reassessment is not None
            else set()
        )
        previous = ReadinessAssessment.model_validate(state["assessment"])
        resource_signal = (
            None if "resource_constraint" in scope_signals else previous.resource_signal
        )
        evaluation_signal = (
            None if "evaluation_conditions" in scope_signals else previous.evaluation_signal
        )
        readiness = self.readiness_adjudicator.adjudicate(
            projection,
            resource_signal=resource_signal,
            evaluation_signal=evaluation_signal,
        )
        assessment = self._assessment(
            state,
            readiness,
            projection,
            trace,
            affected_dimensions=None,
        )
        assessment = assessment.model_copy(
            update={
                "audit_trail": build_assessment_audit(
                    revised,
                    existing=previous.audit_trail,
                    human_feedback=feedback,
                )
            }
        )
        revised.update(
            material_bundle=full_bundle,
            local_evidence_finding_input=local_input,
            local_evidence_finding_invocation=draft_invocation,
            local_evidence_finding_rule_outcome=local_outcome,
            local_analysis=merged_analysis,
            evidence_validation=validation,
            candidate_adjudication=candidate_adjudication,
            projection=projection,
            readiness=readiness,
            assessment=ReadinessAssessment.model_validate(assessment),
            workflow_trace=assessment.trace_summary,
        )
        return revised

    def _build_local_feedback_input(
        self,
        state: dict[str, Any],
        bundle: MaterialBundle,
        review_context: HumanReviewContext,
        feedback_reassessment: AIFeedbackReassessmentResult | None,
        affected_dimensions: tuple[str, ...],
    ) -> EvidenceFindingInput:
        """Build a bounded local context from retained target lineage only."""

        assessment = ReadinessAssessment.model_validate(state["assessment"])
        target = review_context.original_finding
        if target is None:
            raise AIModelResponseError("Local feedback reassessment requires a target Finding.")
        primary_dimension = next(
            (
                dimension.dimension_id
                for dimension in assessment.dimensions
                if any(item.finding_id == target.finding_id for item in dimension.findings)
            ),
            None,
        )
        if primary_dimension is None:
            raise AssessmentFeedbackTargetError(
                "Target Finding no longer belongs to the retained Assessment."
            )
        related_dimensions = [item for item in affected_dimensions if item != primary_dimension][:2]
        scope_finding_ids = (
            set(feedback_reassessment.affected_scope.finding_refs)
            if feedback_reassessment is not None
            else set()
        )
        scope_finding_ids.add(target.finding_id)
        selected_findings = [
            (dimension.dimension_id, finding)
            for dimension in assessment.dimensions
            for finding in dimension.findings
            if finding.finding_id in scope_finding_ids
        ][:5]
        if not selected_findings:
            selected_findings = [(primary_dimension, target)]

        contexts: list[EvidenceFindingConditionContext] = []
        related_evidence: list[EvidenceDraft] = []
        related_findings: list[FindingDraft] = []
        source_ids = {source.source_id for source in bundle.sources}
        for dimension_id, finding in selected_findings:
            condition_related = (
                related_dimensions if finding.finding_id == target.finding_id else []
            )
            contexts.append(
                EvidenceFindingConditionContext(
                    condition_ref=finding.condition,
                    primary_dimension=dimension_id,
                    related_dimensions=condition_related,
                    existing_finding_ref=finding.finding_id,
                    gate_critical=finding.gate_critical,
                )
            )
            finding_evidence: list[str] = []
            for evidence in finding.evidence:
                draft = self._retained_evidence_draft(evidence, finding.condition, source_ids)
                if draft is not None:
                    related_evidence.append(draft)
                    finding_evidence.append(draft.local_evidence_id)
            if finding_evidence:
                related_findings.append(
                    FindingDraft(
                        local_finding_id=f"retained-{finding.finding_id}",
                        operation="update_existing",
                        existing_finding_ref=finding.finding_id,
                        condition=finding.condition,
                        summary=finding.summary,
                        finding_type=finding.finding_type,
                        primary_dimension=dimension_id,
                        related_dimensions=condition_related,
                        evidence_refs_local=finding_evidence,
                        gate_critical=finding.gate_critical,
                        gate_critical_basis="supplied_condition_context",
                    )
                )
        # Multiple displayed Findings can share a Condition.  The Rule handles
        # candidate merging; the model needs one unambiguous condition context.
        unique_contexts = list({item.condition_ref: item for item in contexts}.values())
        gaps = self._feedback_phase_gaps(feedback_reassessment, primary_dimension)
        relevant_source_ids = list(
            dict.fromkeys(
                [
                    *(item.source_ref for item in related_evidence),
                    *(
                        source.source_id
                        for source in bundle.sources
                        if source.access_scope == "user_provided"
                    ),
                ]
            )
        )
        if not relevant_source_ids:
            relevant_source_ids = [source.source_id for source in bundle.sources]
        return EvidenceFindingInput(
            bundle=bundle,
            focus={
                "scope_refs": [primary_dimension],
                "finding_refs": sorted(scope_finding_ids),
            },
            condition_contexts=unique_contexts,
            current_information_gaps=gaps,
            relevant_source_ids=relevant_source_ids,
            related_evidence=related_evidence,
            related_findings=related_findings,
        )

    @staticmethod
    def _retained_evidence_draft(
        evidence, condition: str, source_ids: set[str]
    ) -> EvidenceDraft | None:
        if evidence.evidence_id is None or evidence.source_id not in source_ids:
            return None
        return EvidenceDraft(
            local_evidence_id=evidence.evidence_id,
            condition_refs=[condition],
            source_ref=evidence.source_id,
            source_type=evidence.source_type,
            evidence_type=evidence.evidence_type,
            location=evidence.location,
            line_start=evidence.line_start,
            line_end=evidence.line_end,
            material_type=evidence.material_type,
            quote=evidence.excerpt,
            claim=evidence.summary,
            verification_status=evidence.verification_status,
        )

    @staticmethod
    def _feedback_phase_gaps(
        reassessment: AIFeedbackReassessmentResult | None,
        primary_dimension: str,
    ) -> list[PhaseInformationGap]:
        if reassessment is None:
            return []
        return [
            PhaseInformationGap(
                gap_id=item.gap_id,
                question=item.description,
                scope_ref=primary_dimension,
                needed_source_type="User Context"
                if item.area == "user_environment"
                else "Material",
                reason=item.why_needed,
            )
            for item in reassessment.information_gaps
        ]

    @staticmethod
    def _merge_local_rule_analysis(
        state: dict[str, Any],
        local: AIAnalysisResult,
        bundle: MaterialBundle,
        replaced_conditions: set[str],
    ) -> AIAnalysisResult:
        """Replace only Conditions inside the feedback scope in the retained graph."""

        previous = state.get("local_analysis")
        if previous is None:
            raise AIModelResponseError(
                "The retained Assessment has no local Evidence/Finding graph for feedback reassessment."
            )
        retained_evidence = [
            item.model_copy(deep=True)
            for item in previous.evidence_candidates
            if item.condition_key not in replaced_conditions
        ]
        retained_findings = [
            item.model_copy(deep=True)
            for item in previous.finding_candidates
            if item.condition_key not in replaced_conditions
        ]
        retained_conflicts = [
            item.model_copy(deep=True)
            for item in previous.conflict_candidates
            if item.condition_key not in replaced_conditions
        ]
        retained_questions = [
            item.model_copy(deep=True)
            for item in previous.unresolved_questions
            if item.condition_key not in replaced_conditions
        ]
        return AIAnalysisResult(
            analysis_id=local.analysis_id,
            bundle_id=bundle.bundle_id,
            summary="Retained assessment graph with a Rule-admitted local feedback update.",
            examined_source_ids=list(
                dict.fromkeys(
                    [
                        *previous.examined_source_ids,
                        *local.examined_source_ids,
                        *(item.locator.source_id for item in retained_evidence),
                        *(item.locator.source_id for item in local.evidence_candidates),
                    ]
                )
            ),
            evidence_candidates=[*retained_evidence, *local.evidence_candidates],
            conflict_candidates=[*retained_conflicts, *local.conflict_candidates],
            finding_candidates=[*retained_findings, *local.finding_candidates],
            unresolved_questions=[*retained_questions, *local.unresolved_questions],
        )

    def _assessment(
        self,
        state,
        readiness,
        projection,
        trace,
        *,
        affected_dimensions: tuple[str, ...] | None = None,
    ) -> ReadinessAssessment:
        previous = ReadinessAssessment.model_validate(state["assessment"])
        if not readiness.decision_available:
            message = readiness.unavailable_reason or "Evidence validation did not complete."
            analysis_state = "evidence_validation_failure"
            dimensions = [
                ReadinessDimension(
                    dimension_id=dimension_id,
                    name=name,
                    analysis_state=analysis_state,
                    summary=message,
                    gate_impact="Overall Gate remains unavailable until validation succeeds.",
                )
                for dimension_id, name in (
                    ("RD-01", "Data & Access Readiness"),
                    ("RD-02", "Environment & Dependency Readiness"),
                    ("RD-03", "Weights & Configuration Readiness"),
                )
            ]
            payload = previous.model_dump()
            payload.update(
                {
                    "status": "partial",
                    "dimensions": dimensions,
                    "analysis_state": analysis_state,
                    "gate_available": False,
                    "overall_gate": None,
                    "trigger_refs": [],
                    "main_risk": message,
                    "first_next_action": NextAction(
                        action_id="action-evidence-validation-failure",
                        title="Resolve the evidence validation failure",
                        description=message,
                        action_type="Minimum Validation",
                        reason_refs=["evidence_validation_failure"],
                    ),
                    "conflicts": [],
                    "evaluation_signal": None,
                    "resource_signal": None,
                    "trace_summary": trace,
                }
            )
            return ReadinessAssessment.model_validate(payload)
        payload = previous.model_dump()
        payload.update(
            {
                "status": "partial" if state.get("material_partial") else "completed",
                "dimensions": readiness.dimensions,
                "analysis_state": "partial_result" if state.get("material_partial") else None,
                "gate_available": True,
                "overall_gate": readiness.overall_gate,
                "trigger_refs": readiness.trigger_refs,
                "main_risk": readiness.main_risk,
                "first_next_action": readiness.first_next_action,
                "conflicts": self._merged_conflicts(
                    previous.conflicts,
                    [item.conflict for item in projection.conflicts],
                    affected_dimensions,
                ),
                "evaluation_signal": readiness.evaluation_signal,
                "resource_signal": readiness.resource_signal,
                "trace_summary": [*trace, *readiness.rule_trace],
            }
        )
        return ReadinessAssessment.model_validate(payload)

    @staticmethod
    def _feedback_dimensions(
        review_context: HumanReviewContext,
        result: AIFeedbackReassessmentResult | None,
    ) -> tuple[str, ...]:
        """Use the AI scope when available; the explicit Human target is fallback."""

        # The AI scope deliberately includes both the primary Dimension and
        # any semantically dependent secondary Dimensions.  They are all
        # reanalysed together; only omitted Dimensions remain untouched.
        dimensions = list(result.affected_scope.dimension_refs) if result is not None else []
        if not dimensions and review_context.original_finding is not None:
            condition = review_context.original_finding.condition
            if condition.startswith("rd01."):
                dimensions.append("RD-01")
            elif condition.startswith("rd02."):
                dimensions.append("RD-02")
            elif condition.startswith("rd03."):
                dimensions.append("RD-03")
        if not dimensions:
            raise AIModelResponseError(
                "Feedback reassessment did not identify an affected Dimension."
            )
        return tuple(dict.fromkeys(dimensions))

    @staticmethod
    def _scoped_feedback_bundle(
        state: dict[str, Any],
        bundle: MaterialBundle,
        *,
        affected_dimensions: tuple[str, ...],
    ) -> MaterialBundle:
        """Limit Evidence/Conflict AI to the selected Dimension's material lineage."""

        assessment = ReadinessAssessment.model_validate(state["assessment"])
        source_ids = {
            evidence.source_id
            for dimension in assessment.dimensions
            if dimension.dimension_id in affected_dimensions
            for finding in dimension.findings
            for evidence in finding.evidence
        }
        source_ids.update(
            evidence.source_id
            for conflict in assessment.conflicts
            if set(conflict.dimension_ids) & set(affected_dimensions)
            for evidence in conflict.sources
        )
        sources = [
            source.model_copy(deep=True)
            for source in bundle.sources
            if source.source_id in source_ids or source.access_scope == "user_provided"
        ]
        if not sources:
            # A Rule-generated missing Finding has no pre-existing Evidence.
            # Keep the user-supplied material only; never silently broaden to
            # all repository files.
            sources = [
                source.model_copy(deep=True)
                for source in bundle.sources
                if source.access_scope == "user_provided"
            ]
        if not sources:
            raise AIModelResponseError(
                "No source-bound material is available for the selected feedback scope."
            )
        return bundle.model_copy(update={"sources": sources}, deep=True)

    @staticmethod
    def _merge_retained_bundle(
        retained: MaterialBundle,
        scoped: MaterialBundle,
    ) -> MaterialBundle:
        """Keep all first-pass material for later, independently scoped feedback."""

        sources = [source.model_copy(deep=True) for source in retained.sources]
        known_ids = {source.source_id for source in sources}
        sources.extend(
            source.model_copy(deep=True)
            for source in scoped.sources
            if source.source_id not in known_ids
        )
        return retained.model_copy(update={"sources": sources}, deep=True)

    @staticmethod
    def _merge_scoped_readiness(
        *,
        previous: ReadinessAssessment,
        scoped: ReadinessAdjudicationResult,
        affected_dimensions: tuple[str, ...],
    ) -> ReadinessAdjudicationResult:
        """Recalculate only scoped dimensions, then apply Gate rules to the full state."""

        if not scoped.decision_available:
            return scoped
        scoped_by_id = {item.dimension_id: item for item in scoped.dimensions}
        dimensions = [
            scoped_by_id[item.dimension_id]
            if item.dimension_id in affected_dimensions
            else item.model_copy(deep=True)
            for item in previous.dimensions
        ]
        resource_signal = (
            scoped.resource_signal
            if "resource_constraint" in affected_dimensions
            else previous.resource_signal
        )
        evaluation_signal = (
            scoped.evaluation_signal
            if "evaluation_conditions" in affected_dimensions
            else previous.evaluation_signal
        )
        gate = GateDecisionService().resolve(dimensions, resource_signal, evaluation_signal)
        return scoped.model_copy(
            update={
                "dimensions": dimensions,
                "resource_signal": resource_signal,
                "evaluation_signal": evaluation_signal,
                "overall_gate": gate.overall_gate,
                "main_risk": gate.main_risk,
                "first_next_action": gate.first_next_action,
                "trigger_refs": list(gate.trigger_refs),
                "rule_trace": [
                    *scoped.rule_trace,
                    "Scoped reassessment preserved unaffected Dimensions: "
                    + ",".join(
                        item.dimension_id
                        for item in previous.dimensions
                        if item.dimension_id not in affected_dimensions
                    ),
                ],
            }
        )

    @staticmethod
    def _merged_conflicts(previous, scoped, affected_dimensions):
        if affected_dimensions is None:
            return scoped
        return [
            *[
                item.model_copy(deep=True)
                for item in previous
                if not (set(item.dimension_ids) & set(affected_dimensions))
            ],
            *scoped,
        ]

    def _augment_bundle(
        self,
        bundle: MaterialBundle,
        request: AssessmentFeedbackRequest,
        review_context: HumanReviewContext,
    ) -> MaterialBundle:
        submission = request.source_submission
        if submission is None:
            raise ValueError("source_submission is required")
        submitted_bundle = self.material_builder.build(
            bundle.target,
            [
                CollectedMaterial(
                    material_type=submission.material_type,
                    title=submission.title,
                    source_path=submission.source_path,
                    source_url=submission.source_url,
                    content=submission.content,
                    access_scope="user_provided",
                    priority=100,
                )
            ],
        ).bundle
        # Preserve the exact first-pass MaterialSource objects and source_ids.
        # Rebuilding already chunked sources would hash each chunk as a new original
        # file and break every retained Evidence locator for large materials.
        sources = [source.model_copy(deep=True) for source in bundle.sources]
        existing_ids = {source.source_id for source in sources}
        sources.extend(
            source.model_copy(deep=True)
            for source in submitted_bundle.sources
            if source.source_id not in existing_ids
        )
        return MaterialBundle(
            bundle_id=uuid4(),
            target=bundle.target.model_copy(deep=True),
            assembled_at=datetime.now(UTC),
            sources=sources,
            human_review_context=review_context.model_copy(deep=True),
        )

    @staticmethod
    def _validate_feedback_reassessment_scope(
        state: dict[str, Any],
        request: AssessmentFeedbackRequest,
        review_context: HumanReviewContext,
        result: AIFeedbackReassessmentResult,
    ) -> None:
        """Require the AI-proposed scope to be traceable to the feedback target.

        The model may limit the scope, but it may not silently omit the Finding,
        Evidence, Dimension, or Signal that the user actually challenged.
        """

        assessment = ReadinessAssessment.model_validate(state["assessment"])
        finding_dimensions = {
            finding.finding_id: dimension.dimension_id
            for dimension in assessment.dimensions
            for finding in dimension.findings
        }
        evidence_findings = {
            evidence.evidence_id: finding.finding_id
            for dimension in assessment.dimensions
            for finding in dimension.findings
            for evidence in finding.evidence
            if evidence.evidence_id is not None
        }
        signal_evidence_ids = {
            evidence.evidence_id
            for evidence in [
                *(
                    assessment.evaluation_signal.evidence_refs
                    if assessment.evaluation_signal
                    else []
                ),
                *(
                    [assessment.resource_signal.evidence]
                    if assessment.resource_signal and assessment.resource_signal.evidence
                    else []
                ),
                *(source for conflict in assessment.conflicts for source in conflict.sources),
            ]
            if evidence.evidence_id is not None
        }
        scope = result.affected_scope
        if not set(scope.finding_refs) <= set(finding_dimensions):
            raise AIModelResponseError("Feedback reassessment referenced an unknown Finding.")
        if not set(scope.evidence_refs) <= (set(evidence_findings) | signal_evidence_ids):
            raise AIModelResponseError("Feedback reassessment referenced unknown Evidence.")

        target_finding_id = (
            request.target_id
            if request.target_type == "finding"
            else evidence_findings.get(request.target_id)
        )
        target_dimension_id = (
            finding_dimensions.get(target_finding_id) if target_finding_id is not None else None
        )
        target_is_covered = (
            request.target_id in scope.finding_refs
            or request.target_id in scope.evidence_refs
            or (target_finding_id is not None and target_finding_id in scope.finding_refs)
            or (target_dimension_id is not None and target_dimension_id in scope.dimension_refs)
            or (
                target_finding_id is None
                and review_context.original_evidence is not None
                and bool(scope.signal_refs)
            )
        )
        if result.reassessment_required and not target_is_covered:
            raise AIModelResponseError(
                "Feedback reassessment omitted the user-challenged assessment scope."
            )

    @staticmethod
    def _review_context(
        state: dict[str, Any],
        request: AssessmentFeedbackRequest,
    ) -> HumanReviewContext:
        assessment = ReadinessAssessment.model_validate(state["assessment"])
        original_finding = None
        original_evidence = None
        for dimension in assessment.dimensions:
            for finding in dimension.findings:
                if request.target_type == "finding" and finding.finding_id == request.target_id:
                    original_finding = finding.model_copy(deep=True)
                    break
                if request.target_type == "evidence":
                    matched = next(
                        (
                            item
                            for item in finding.evidence
                            if item.evidence_id == request.target_id
                        ),
                        None,
                    )
                    if matched is not None:
                        original_finding = finding.model_copy(deep=True)
                        original_evidence = matched.model_copy(deep=True)
                        break
            if original_finding is not None:
                break

        if request.target_type == "evidence" and original_evidence is None:
            signal_evidence = []
            if assessment.evaluation_signal is not None:
                signal_evidence.extend(assessment.evaluation_signal.evidence_refs)
            if (
                assessment.resource_signal is not None
                and assessment.resource_signal.evidence is not None
            ):
                signal_evidence.append(assessment.resource_signal.evidence)
            signal_evidence.extend(
                item for conflict in assessment.conflicts for item in conflict.sources
            )
            matched = next(
                (item for item in signal_evidence if item.evidence_id == request.target_id),
                None,
            )
            if matched is not None:
                original_evidence = matched.model_copy(deep=True)

        return HumanReviewContext(
            target_type=request.target_type,
            target_id=request.target_id,
            action=request.action,
            comment=request.comment,
            original_finding=original_finding,
            original_evidence=original_evidence,
        )

    @staticmethod
    def _retain_verified_evidence(
        *,
        previous: AIEvidenceExtractionResult,
        previous_validation,
        refreshed: AIEvidenceExtractionResult,
        bundle: MaterialBundle,
    ) -> AIEvidenceExtractionResult:
        """Carry forward source-bound evidence that the new extraction omitted.

        A reassessment is allowed to add or reinterpret material, but it must not
        silently erase an already Rule-verified quote merely because the model did
        not repeat it in the next extraction.  The carried candidates are validated
        again against the rebuilt bundle below, so this is provenance retention, not
        a bypass of the Evidence rules.
        """

        accepted_ids = {
            item.evidence_candidate_id
            for item in previous_validation.evidence_results
            if item.decision in {"accepted", "downgraded"}
        }
        available_sources = {source.source_id for source in bundle.sources}
        refreshed_ids = {item.candidate_id for item in refreshed.evidence_candidates} | {
            item.question_id for item in refreshed.unresolved_questions
        }
        refreshed_signatures = {
            (item.criterion_id, item.locator.source_id, item.quote)
            for item in refreshed.evidence_candidates
        }
        retained = [
            item.model_copy(deep=True)
            for item in previous.evidence_candidates
            if item.candidate_id in accepted_ids
            and item.candidate_id not in refreshed_ids
            and item.locator.source_id in available_sources
            and (item.criterion_id, item.locator.source_id, item.quote) not in refreshed_signatures
        ]
        # The extraction contract has a bounded candidate count. Fresh candidates
        # take precedence when the provider already filled the entire allowance.
        retained = retained[: max(0, 32 - len(refreshed.evidence_candidates))]
        if not retained:
            return refreshed

        areas_by_evidence: dict[str, set[str]] = {}
        for coverage in previous.coverage:
            for candidate_id in coverage.evidence_candidate_ids:
                areas_by_evidence.setdefault(candidate_id, set()).add(coverage.area)
        retained_by_area: dict[str, list[str]] = {}
        for candidate in retained:
            for area in areas_by_evidence.get(candidate.candidate_id, set()):
                retained_by_area.setdefault(area, []).append(candidate.candidate_id)

        coverage: list[EvidenceAreaCoverage] = []
        for item in refreshed.coverage:
            carried_ids = retained_by_area.get(item.area, [])
            evidence_ids = [*item.evidence_candidate_ids, *carried_ids]
            coverage.append(
                item.model_copy(
                    update={
                        "state": "uncertain"
                        if item.state == "not_found" and evidence_ids
                        else item.state,
                        "evidence_candidate_ids": evidence_ids,
                    }
                )
            )

        return refreshed.model_copy(
            update={
                "summary": (
                    f"{refreshed.summary} Previously Rule-verified evidence was "
                    "retained and will be revalidated for this reassessment."
                )[:2000],
                "examined_source_ids": list(
                    dict.fromkeys(
                        [
                            *refreshed.examined_source_ids,
                            *(item.locator.source_id for item in retained),
                        ]
                    )
                ),
                "evidence_candidates": [
                    *refreshed.evidence_candidates,
                    *retained,
                ],
                "coverage": coverage,
            }
        )

    @staticmethod
    def _resolve_evidence(
        extraction: AIEvidenceExtractionResult,
        request: AssessmentFeedbackRequest,
    ) -> AIEvidenceExtractionResult:
        resolution = request.evidence_resolution
        if resolution is None:
            raise ValueError("evidence_resolution is required")
        candidates = []
        for candidate in extraction.evidence_candidates:
            if candidate.candidate_id != request.target_id:
                candidates.append(candidate)
                continue
            if resolution.source_id != candidate.locator.source_id and resolution.quote is None:
                raise AssessmentFeedbackTargetError(
                    "Changing an Evidence source requires a verbatim quote from that source."
                )
            candidates.append(
                candidate.model_copy(
                    update={
                        "locator": SourceLocator(
                            source_id=resolution.source_id,
                            location=f"human-confirmed:lines {resolution.line_start}-{resolution.line_end}",
                            line_start=resolution.line_start,
                            line_end=resolution.line_end,
                        ),
                        "quote": resolution.quote or candidate.quote,
                    }
                )
            )
        payload = extraction.model_dump()
        payload.update(extraction_id=uuid4(), evidence_candidates=candidates)
        return AIEvidenceExtractionResult.model_validate(payload)

    @staticmethod
    def _requires_reassessment(request: AssessmentFeedbackRequest) -> bool:
        return (
            request.action in {"correct", "supplement"}
            or request.source_submission is not None
            or request.evidence_resolution is not None
        )

    @staticmethod
    def _validate_target(state: dict[str, Any], request: AssessmentFeedbackRequest) -> None:
        assessment = ReadinessAssessment.model_validate(state["assessment"])
        findings = [
            finding for dimension in assessment.dimensions for finding in dimension.findings
        ]
        if request.target_type == "finding":
            known_ids = {finding.finding_id for finding in findings}
        else:
            evidence = [item for finding in findings for item in finding.evidence]
            evidence.extend(item for conflict in assessment.conflicts for item in conflict.sources)
            if assessment.evaluation_signal is not None:
                evidence.extend(assessment.evaluation_signal.evidence_refs)
            if (
                assessment.resource_signal is not None
                and assessment.resource_signal.evidence is not None
            ):
                evidence.append(assessment.resource_signal.evidence)
            known_ids = {item.evidence_id for item in evidence if item.evidence_id is not None}
        if request.target_id not in known_ids:
            raise AssessmentFeedbackTargetError(
                "Feedback target does not belong to the retained Assessment revision."
            )

    def _required_session(self, assessment_id: UUID) -> AssessmentReviewSession:
        authorize_resource("assessment", assessment_id)
        session = self.store.get(assessment_id)
        if session is None:
            raise AssessmentReviewNotFoundError(
                "Assessment review state is missing, invalid, or past its retention window; "
                "rerun the assessment once to create a recoverable review session."
            )
        return session

    @staticmethod
    def _append_revision(
        session: AssessmentReviewSession,
        assessment: ReadinessAssessment,
        feedback: HumanFeedback,
    ) -> None:
        """Keep an immutable, API-safe snapshot; source material remains in session state only."""

        session.revisions.append(
            AssessmentRevision(
                revision=session.revision,
                created_at=datetime.now(UTC),
                feedback=feedback.model_copy(deep=True),
                assessment=assessment.model_copy(deep=True),
            )
        )

    def _append_current_revision(
        self,
        session: AssessmentReviewSession,
        feedback: HumanFeedback,
    ) -> None:
        self._append_revision(
            session,
            ReadinessAssessment.model_validate(session.state["assessment"]),
            feedback,
        )

    @staticmethod
    def _revision_change(
        previous: AssessmentRevision,
        current: AssessmentRevision,
    ) -> AssessmentRevisionChange:
        previous_dimensions = {
            item.dimension_id: item.status for item in previous.assessment.dimensions
        }
        current_dimensions = {
            item.dimension_id: item.status for item in current.assessment.dimensions
        }
        previous_findings = {
            finding.finding_id
            for dimension in previous.assessment.dimensions
            for finding in dimension.findings
        }
        current_findings = {
            finding.finding_id
            for dimension in current.assessment.dimensions
            for finding in dimension.findings
        }
        previous_evidence = {
            item.evidence_id
            for dimension in previous.assessment.dimensions
            for finding in dimension.findings
            for item in finding.evidence
            if item.evidence_id is not None
        }
        current_evidence = {
            item.evidence_id
            for dimension in current.assessment.dimensions
            for finding in dimension.findings
            for item in finding.evidence
            if item.evidence_id is not None
        }
        return AssessmentRevisionChange(
            from_revision=previous.revision,
            to_revision=current.revision,
            overall_gate_changed=(
                previous.assessment.overall_gate != current.assessment.overall_gate
            ),
            changed_dimension_ids=sorted(
                dimension_id
                for dimension_id in {*previous_dimensions, *current_dimensions}
                if previous_dimensions.get(dimension_id) != current_dimensions.get(dimension_id)
            ),
            added_finding_ids=sorted(current_findings - previous_findings),
            removed_finding_ids=sorted(previous_findings - current_findings),
            added_evidence_ids=sorted(current_evidence - previous_evidence),
            removed_evidence_ids=sorted(previous_evidence - current_evidence),
        )

    @staticmethod
    def _response(
        session,
        feedback,
        performed,
        state,
        *,
        detail: str | None = None,
    ) -> AssessmentFeedbackResponse:
        return AssessmentFeedbackResponse(
            assessment_id=session.assessment_id,
            revision=session.revision,
            feedback=feedback,
            requires_reassessment=feedback.requires_reassessment,
            reassessment_performed=performed,
            reassessment_state=state,
            reassessment_detail=detail,
            assessment=ReadinessAssessment.model_validate(session.state["assessment"]),
        )

    @staticmethod
    def _safe_reassessment_detail(error: AIModelResponseError) -> str:
        """Expose a useful failure category without returning model output or prompts."""

        message = str(error)
        if "omitted the user-challenged assessment scope" in message:
            return (
                "The AI did not include the selected Finding or Evidence in its reassessment "
                "scope. Your feedback was retained; retry the reassessment."
            )
        if "unknown Finding" in message or "unknown Evidence" in message:
            return (
                "The AI referenced an identifier outside this Assessment revision. Your feedback "
                "was retained; retry the reassessment."
            )
        if "Targeted Evidence reassessment omitted" in message:
            return (
                "The AI did not return a validated replacement for the selected Evidence. The "
                "previous Assessment was retained."
            )
        return (
            "The AI response did not satisfy the required reassessment contract. Your feedback "
            "was retained; retry the reassessment."
        )

    @staticmethod
    def _model_trace(stage: str, trace) -> str:
        return (
            f"{stage}: success - request_id={trace.request_id or 'unavailable'}, "
            f"tokens={trace.total_tokens if trace.total_tokens is not None else 'unavailable'}, "
            f"duration_ms={trace.duration_ms}."
        )
