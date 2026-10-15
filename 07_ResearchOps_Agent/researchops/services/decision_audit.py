"""Build a privacy-bounded AI → Rule → Human decision lineage."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from researchops.core.security import redact_sensitive_text
from researchops.schemas import (
    AssessmentAuditActor,
    AssessmentAuditEvent,
    AssessmentAuditOutcome,
    FinalInvestmentDecisionRecord,
    HumanFeedback,
)


def build_assessment_audit(
    state: dict[str, Any],
    *,
    existing: Iterable[AssessmentAuditEvent] = (),
    human_feedback: HumanFeedback | None = None,
    final_decision: FinalInvestmentDecisionRecord | None = None,
) -> list[AssessmentAuditEvent]:
    """Create metadata-only lineage without retaining prompts, quotes, or credentials."""

    generated: list[AssessmentAuditEvent] = []
    if human_feedback is not None:
        generated.append(_human_feedback_event(human_feedback))
    if final_decision is not None:
        generated.append(_final_decision_event(final_decision))
    bundle = state.get("material_bundle")
    research_loop = state.get("research_loop")
    feedback_reassessment = state.get("feedback_reassessment")
    initial_bundle = state.get("initial_material_bundle")
    evidence_invocation = state.get("evidence_invocation")
    validation = state.get("evidence_validation")
    conflict_invocation = state.get("conflict_invocation")
    local_evidence_invocations = state.get("local_evidence_invocations", [])
    adjudication = state.get("candidate_adjudication")
    readiness = state.get("readiness")
    assessment = state.get("assessment")

    recorded_bundle = initial_bundle or bundle
    if recorded_bundle is not None:
        generated.append(
            _event(
                actor="connector",
                stage="material_bundle",
                outcome="completed",
                occurred_at=recorded_bundle.assembled_at,
                refs=[
                    f"bundle:{recorded_bundle.bundle_id}",
                    *(f"source:{source.source_id}" for source in recorded_bundle.sources),
                ],
                detail=(
                    "Bounded material bundle assembled from "
                    f"{len(recorded_bundle.sources)} source(s)."
                ),
            )
        )
    if state.get("material_partial"):
        generated.append(
            _event(
                actor="connector",
                stage="material_acquisition",
                outcome="partial",
                occurred_at=_assessment_time(assessment),
                refs=(
                    [f"bundle:{recorded_bundle.bundle_id}"]
                    if recorded_bundle is not None
                    else []
                ),
                detail=(
                    "At least one linked public material could not be acquired; available "
                    "materials remained separately traceable."
                ),
            )
        )

    if feedback_reassessment is not None:
        result = feedback_reassessment.result
        trace = feedback_reassessment.trace
        scope = result.affected_scope
        generated.append(
            _event(
                actor="ai",
                stage="ai_feedback_reassessment",
                outcome="completed",
                occurred_at=trace.completed_at,
                refs=[
                    f"feedback_reassessment:{result.reassessment_id}",
                    f"bundle:{result.bundle_id}",
                    *(f"finding:{item}" for item in scope.finding_refs),
                    *(f"evidence:{item}" for item in scope.evidence_refs),
                    *(f"dimension:{item}" for item in scope.dimension_refs),
                    *(f"signal:{item}" for item in scope.signal_refs),
                    *(f"gap:{item.gap_id}" for item in result.information_gaps),
                ],
                model=trace.model,
                model_trace_id=trace.trace_id,
                provider_request_id=trace.request_id,
                duration_ms=trace.duration_ms,
                detail=(
                    f"AI scoped feedback to {len(scope.finding_refs)} Finding(s), "
                    f"{len(scope.dimension_refs)} Dimension(s), and "
                    f"{len(result.information_gaps)} new Gap(s); "
                    f"handoff={result.handoff}."
                ),
            )
        )

    if research_loop is not None:
        for round_record in research_loop.rounds:
            context_gap = round_record.context_gap
            tool_acquisition = round_record.tool_acquisition
            if context_gap is not None:
                context_result = context_gap.result
                context_trace = context_gap.trace
                generated.append(
                    _event(
                        actor="ai",
                        stage="ai_context_gap",
                        outcome="completed",
                        occurred_at=context_trace.completed_at,
                        refs=[
                            f"research_run:{research_loop.run_id}",
                            f"research_round:{round_record.round_number}",
                            *(f"source:{item.source_ref}" for item in context_result.supported_facts),
                            *(f"gap:{item.gap_id}" for item in context_result.information_gaps),
                        ],
                        model=context_trace.model,
                        model_trace_id=context_trace.trace_id,
                        provider_request_id=context_trace.request_id,
                        duration_ms=context_trace.duration_ms,
                        detail=(
                            f"AI retained {len(context_result.supported_facts)} source-bound fact(s) "
                            f"and identified {len(context_result.information_gaps)} minimum Gap(s)."
                        ),
                    )
                )
            if tool_acquisition is not None:
                acquisition_result = tool_acquisition.result
                acquisition_trace = tool_acquisition.trace
                generated.append(
                    _event(
                        actor="ai",
                        stage="ai_tool_acquisition",
                        outcome="completed",
                        occurred_at=acquisition_trace.completed_at,
                        refs=[
                            f"research_run:{research_loop.run_id}",
                            f"research_round:{round_record.round_number}",
                            *(f"gap:{item.gap_ref}" for item in acquisition_result.requests),
                            *(
                                f"tool_request:{item.tool_ref}:{item.gap_ref}"
                                for item in acquisition_result.requests
                                if item.tool_ref is not None
                            ),
                        ],
                        model=acquisition_trace.model,
                        model_trace_id=acquisition_trace.trace_id,
                        provider_request_id=acquisition_trace.request_id,
                        duration_ms=acquisition_trace.duration_ms,
                        detail=(
                            f"AI produced a minimum Tool Acquisition handoff "
                            f"({acquisition_result.acquisition_state}; "
                            f"{len(acquisition_result.requests)} request(s)); it executed no tool."
                        ),
                    )
                )
            if context_gap is None and round_record.planning is not None:
                plan = round_record.planning.result
                trace = round_record.planning.trace
                generated.append(
                    _event(
                        actor="ai",
                        stage="ai_research_planning",
                        outcome="completed",
                        occurred_at=trace.completed_at,
                        refs=[
                            f"research_run:{research_loop.run_id}",
                            f"research_round:{round_record.round_number}",
                            f"bundle:{plan.bundle_id}",
                            f"plan:{plan.plan_id}",
                            *(f"source:{item}" for item in plan.examined_source_ids),
                            *(f"gap:{item.gap_id}" for item in plan.information_gaps),
                            *(f"tool_request:{item.request_id}" for item in plan.tool_requests),
                        ],
                        model=trace.model,
                        model_trace_id=trace.trace_id,
                        provider_request_id=trace.request_id,
                        duration_ms=trace.duration_ms,
                        detail=(
                            f"AI identified {len(plan.information_gaps)} information gap(s) and "
                            f"requested {len(plan.tool_requests)} allowlisted tool call(s); "
                            "the model executed no tools and made no Gate decision."
                        ),
                    )
                )
            execution = round_record.execution
            if execution is None:
                continue
            execution_trace = (
                tool_acquisition.trace
                if tool_acquisition is not None
                else context_gap.trace
                if context_gap is not None
                else round_record.planning.trace
                if round_record.planning is not None
                else None
            )
            completed_at = max(
                (item.completed_at for item in execution.request_results),
                default=(
                    execution_trace.completed_at
                    if execution_trace is not None
                    else bundle.assembled_at if bundle is not None else datetime.now(UTC)
                ),
            )
            completed = sum(
                item.status == "succeeded" for item in execution.request_results
            )
            failure_codes = sorted(
                {
                    item.failure_code
                    for item in execution.request_results
                    if item.failure_code is not None
                }
            )
            generated.append(
                _event(
                    actor="connector",
                    stage="research_tool_execution",
                    outcome=(
                        "completed"
                        if completed == len(execution.request_results)
                        else "partial"
                    ),
                    occurred_at=completed_at,
                    refs=[
                        f"plan:{execution.plan_id}",
                        f"bundle:{execution.output_bundle.bundle_id}",
                        *(
                            (
                                f"tool_result:{item.request_id}:{item.tool_name}:"
                                f"{item.status}:{item.failure_code or 'none'}"
                            )
                            for item in execution.request_results
                        ),
                        *(f"source:{item}" for item in execution.new_source_ids),
                    ],
                    duration_ms=_execution_duration_ms(execution.request_results),
                    detail=(
                        f"Deterministic connectors completed {completed} of "
                        f"{len(execution.request_results)} requested read(s) and admitted "
                        f"{len(execution.new_source_ids)} new bounded source(s)."
                        + (
                            f" Safe failure codes={','.join(failure_codes)}."
                            if failure_codes
                            else ""
                        )
                    ),
                )
            )
        if initial_bundle is not None and bundle is not None and (
            bundle.bundle_id != initial_bundle.bundle_id
        ):
            generated.append(
                _event(
                    actor="connector",
                    stage="material_bundle_enriched",
                    outcome="completed",
                    occurred_at=bundle.assembled_at,
                    refs=[
                        f"bundle:{bundle.bundle_id}",
                        *(f"source:{source.source_id}" for source in bundle.sources),
                    ],
                    detail=(
                        "Research loop produced a bounded Evidence input containing "
                        f"{len(bundle.sources)} source(s)."
                    ),
                )
            )

    if evidence_invocation is not None:
        result = evidence_invocation.result
        trace = evidence_invocation.trace
        generated.append(
            _event(
                actor="ai",
                stage="ai_evidence_analysis",
                outcome="completed",
                occurred_at=trace.completed_at,
                refs=[
                    f"bundle:{result.bundle_id}",
                    f"extraction:{result.extraction_id}",
                    *(f"evidence:{item.candidate_id}" for item in result.evidence_candidates),
                ],
                model=trace.model,
                model_trace_id=trace.trace_id,
                provider_request_id=trace.request_id,
                duration_ms=trace.duration_ms,
                detail=(
                    f"AI proposed {len(result.evidence_candidates)} Evidence candidate(s); "
                    "no status or Gate was accepted from the model."
                ),
            )
        )

    for batch_number, invocation in enumerate(local_evidence_invocations, start=1):
        trace = invocation.trace if hasattr(invocation, "trace") else invocation
        result = getattr(invocation, "result", None)
        generated.append(
            _event(
                actor="ai",
                stage="ai_local_evidence_finding",
                outcome="completed",
                occurred_at=trace.completed_at,
                refs=[
                    f"bundle:{bundle.bundle_id}" if bundle is not None else "bundle:unavailable",
                    f"evidence_finding_batch:{batch_number}",
                    *(
                        f"local_evidence:{item.local_evidence_id}"
                        for item in (result.evidence_drafts if result is not None else [])
                    ),
                    *(
                        f"local_finding:{item.local_finding_id}"
                        for item in (result.finding_drafts if result is not None else [])
                    ),
                ],
                model=trace.model,
                model_trace_id=trace.trace_id,
                provider_request_id=trace.request_id,
                duration_ms=trace.duration_ms,
                detail=(
                    "AI drafted locally scoped Evidence/Finding candidates; "
                    "Rule owns provenance validation and formal adjudication."
                ),
            )
        )

    if validation is not None:
        decisions = Counter(item.decision for item in validation.evidence_results)
        generated.append(
            _event(
                actor="rule",
                stage="evidence_validation",
                outcome="completed",
                occurred_at=_latest_time(evidence_invocation, assessment),
                refs=[
                    f"bundle:{validation.bundle_id}",
                    *(f"evidence:{item.evidence_candidate_id}:{item.decision}" for item in validation.evidence_results),
                ],
                detail=(
                    "Rule accounted for every Evidence candidate: "
                    + ", ".join(f"{key}={value}" for key, value in sorted(decisions.items()))
                    + "."
                ),
            )
        )

    if conflict_invocation is not None:
        result = conflict_invocation.result
        trace = conflict_invocation.trace
        generated.append(
            _event(
                actor="ai",
                stage="ai_conflict_finding_analysis",
                outcome="completed",
                occurred_at=trace.completed_at,
                refs=[
                    f"interpretation:{result.interpretation_id}",
                    *(f"conflict:{item.candidate_id}" for item in result.conflict_candidates),
                    *(f"finding:{item.candidate_id}" for item in result.finding_candidates),
                ],
                model=trace.model,
                model_trace_id=trace.trace_id,
                provider_request_id=trace.request_id,
                duration_ms=trace.duration_ms,
                detail=(
                    f"AI proposed {len(result.conflict_candidates)} Conflict and "
                    f"{len(result.finding_candidates)} Finding candidate(s)."
                ),
            )
        )

    if adjudication is not None:
        generated.append(
            _event(
                actor="rule",
                stage="candidate_validation",
                outcome="completed",
                occurred_at=_latest_time(conflict_invocation, assessment),
                refs=[
                    *(f"conflict:{item.conflict_candidate_id}:{item.decision}" for item in adjudication.conflict_results),
                    *(f"finding:{item.finding_candidate_id}:{item.decision}" for item in adjudication.finding_results),
                    *(f"human_confirmation:{item}" for item in adjudication.human_confirmation_candidate_ids),
                ],
                detail=(
                    "Rule validated candidate identity, lineage, deduplication, and admissible strength."
                ),
            )
        )

    if readiness is not None:
        refs = [*(f"trigger:{item}" for item in readiness.trigger_refs)]
        if readiness.overall_gate is not None:
            refs.insert(0, f"gate:{readiness.overall_gate}")
        generated.append(
            _event(
                actor="rule",
                stage="rule_adjudication",
                outcome="completed" if readiness.decision_available else "unavailable",
                occurred_at=_latest_time(conflict_invocation, assessment),
                refs=refs,
                detail=(
                    "Rule computed Dimension statuses and Overall Gate from admitted candidates."
                    if readiness.decision_available
                    else "Rule withheld the Gate because validated decision inputs were insufficient."
                ),
            )
        )

    failure_state = state.get("failure_state")
    if failure_state is not None:
        actor: AssessmentAuditActor = (
            "ai"
            if failure_state in {"configuration_required", "model_unavailable", "invalid_model_response"}
            else "connector"
            if failure_state in {
                "acquisition_failure",
                "partial_material_acquisition",
                "tool_failure",
            }
            else "rule"
        )
        failure_trace = state.get("failure_trace")
        generated.append(
            _event(
                actor=actor,
                stage="analysis_failure",
                outcome="failed",
                occurred_at=_assessment_time(assessment),
                refs=[f"analysis_state:{failure_state}"]
                + (
                    [f"source:{source.source_id}" for source in bundle.sources]
                    if bundle is not None
                    else []
                ),
                model=(failure_trace.model if actor == "ai" and failure_trace is not None else None),
                model_trace_id=(
                    failure_trace.trace_id if actor == "ai" and failure_trace is not None else None
                ),
                provider_request_id=(
                    failure_trace.request_id
                    if actor == "ai" and failure_trace is not None
                    else None
                ),
                duration_ms=(
                    failure_trace.duration_ms
                    if actor == "ai" and failure_trace is not None
                    else None
                ),
                detail="The workflow exposed a technical state without fabricating a business status.",
            )
        )

    if assessment is not None:
        output_refs = [f"assessment:{assessment.assessment_id}"]
        if human_feedback is not None:
            output_refs.append(f"revision:{human_feedback.revision}")
        generated.append(
            _event(
                actor="system",
                stage="output_validation",
                outcome="completed",
                occurred_at=(
                    datetime.now(UTC) if human_feedback is not None else assessment.generated_at
                ),
                refs=output_refs,
                detail="Stable Assessment output contract validated.",
            )
        )
    return _merge(existing, generated)


def append_human_feedback_audit(
    existing: Iterable[AssessmentAuditEvent],
    feedback: HumanFeedback,
) -> list[AssessmentAuditEvent]:
    return _merge(existing, [_human_feedback_event(feedback)])


def append_final_decision_audit(
    existing: Iterable[AssessmentAuditEvent],
    record: FinalInvestmentDecisionRecord,
) -> list[AssessmentAuditEvent]:
    return _merge(existing, [_final_decision_event(record)])


def _human_feedback_event(feedback: HumanFeedback) -> AssessmentAuditEvent:
    return _event(
        actor="human",
        stage="human_feedback",
        outcome="recorded",
        occurred_at=feedback.submitted_at,
        refs=[
            f"feedback:{feedback.feedback_id}",
            f"assessment:{feedback.assessment_id}",
            f"revision:{feedback.revision}",
            f"target:{feedback.target_type}:{feedback.target_id}",
            f"action:{feedback.action}",
        ],
        detail=(
            "Human feedback was recorded separately from AI candidates and Rule decisions; "
            f"reassessment_required={str(feedback.requires_reassessment).lower()}."
        ),
    )


def _final_decision_event(record: FinalInvestmentDecisionRecord) -> AssessmentAuditEvent:
    return _event(
        actor="human",
        stage="final_investment_decision",
        outcome="recorded",
        occurred_at=record.submitted_at,
        refs=[
            f"decision:{record.decision_id}",
            f"assessment:{record.assessment_id}",
            f"revision:{record.revision}",
            f"human_decision:{record.decision}",
        ],
        detail="The user's final investment decision was recorded without changing the Rule Gate.",
    )


def _event(
    *,
    actor: AssessmentAuditActor,
    stage: str,
    outcome: AssessmentAuditOutcome,
    occurred_at: datetime,
    refs: Iterable[str],
    detail: str,
    model: str | None = None,
    model_trace_id=None,
    provider_request_id: str | None = None,
    duration_ms: int | None = None,
) -> AssessmentAuditEvent:
    safe_refs = list(dict.fromkeys(_safe_value(item, 300) for item in refs))
    safe_model = _safe_value(model, 200) if model is not None else None
    safe_request_id = (
        _safe_value(provider_request_id, 300) if provider_request_id is not None else None
    )
    identity = "\0".join(
        [
            actor,
            stage,
            outcome,
            *safe_refs,
            str(model_trace_id or ""),
            safe_request_id or "",
            str(duration_ms if duration_ms is not None else ""),
        ]
    )
    return AssessmentAuditEvent(
        event_id=f"audit-{sha256(identity.encode('utf-8')).hexdigest()[:20]}",
        actor=actor,
        stage=stage,
        outcome=outcome,
        occurred_at=occurred_at,
        refs=safe_refs,
        model=safe_model,
        model_trace_id=model_trace_id,
        provider_request_id=safe_request_id,
        duration_ms=duration_ms,
        detail=_safe_value(detail, 500),
    )


def _merge(
    existing: Iterable[AssessmentAuditEvent],
    generated: Iterable[AssessmentAuditEvent],
) -> list[AssessmentAuditEvent]:
    result: list[AssessmentAuditEvent] = []
    seen: set[str] = set()
    for event in [*existing, *generated]:
        if event.event_id not in seen:
            result.append(event.model_copy(deep=True))
            seen.add(event.event_id)
    return result


def _latest_time(invocation: Any, assessment: Any) -> datetime:
    if invocation is not None:
        return invocation.trace.completed_at
    return _assessment_time(assessment)


def _assessment_time(assessment: Any) -> datetime:
    return assessment.generated_at if assessment is not None else datetime.now(UTC)


def _execution_duration_ms(results: Iterable[Any]) -> int:
    entries = list(results)
    if not entries:
        return 0
    return max(
        0,
        int((max(item.completed_at for item in entries) - min(item.started_at for item in entries)).total_seconds() * 1000),
    )


def _safe_value(value: object, limit: int) -> str:
    return redact_sensitive_text(value)[:limit] or "unavailable"
