"""Deterministic Step 7 Readiness adjudication tests."""

from uuid import uuid4

from researchops.schemas import (
    AIAnalysisDomainProjection,
    Evidence,
    EvidenceConflict,
    EvidenceValidationIssue,
    Finding,
    ProjectedConflict,
    ProjectedEvidence,
    ProjectedFinding,
    UnresolvedQuestion,
)
from researchops.services import DeterministicReadinessAdjudicator
from researchops.services.readiness_adjudication import REQUIRED_CRITERIA


def _evidence(candidate_id: str, criterion_id: str, *, evidence_type: str = "Fact"):
    evidence = Evidence(
        evidence_type=evidence_type,
        verification_status="Located Only",
        source_type="Material",
        material_type="README",
        summary=f"Evidence for {criterion_id}.",
        source="README.md",
        location="README.md:lines 1-1",
        line_start=1,
        line_end=1,
        excerpt=f"Explicit statement for {criterion_id}.",
    )
    return ProjectedEvidence(
        evidence_candidate_id=candidate_id,
        source_id="src-readme",
        criterion_id=criterion_id,
        evidence=evidence,
    )


def _finding(
    candidate_id: str,
    criterion_id: str,
    dimension_id: str,
    *,
    effect: str = "condition_supported",
    finding_type: str = "Fact",
):
    evidence_id = f"e-{candidate_id}"
    projected_evidence = _evidence(evidence_id, criterion_id, evidence_type=finding_type)
    finding = Finding(
        finding_id=candidate_id,
        condition=criterion_id,
        title=f"Finding for {criterion_id}",
        summary=f"Structured candidate for {criterion_id}.",
        finding_type=finding_type,
        readiness_impact="Awaiting deterministic adjudication.",
        evidence=[projected_evidence.evidence],
    )
    return projected_evidence, ProjectedFinding(
        finding_candidate_id=candidate_id,
        evidence_candidate_ids=[evidence_id],
        primary_dimension_id=dimension_id,
        criterion_id=criterion_id,
        readiness_effect=effect,
        finding=finding,
    )


def _complete_projection(*, override: tuple[str, str, str] | None = None):
    evidence = []
    findings = []
    for dimension_id, criteria in REQUIRED_CRITERIA.items():
        for criterion_id in criteria:
            effect = "condition_supported"
            finding_type = "Fact"
            if override and criterion_id == override[0]:
                effect, finding_type = override[1], override[2]
            projected_evidence, projected_finding = _finding(
                f"f-{criterion_id}",
                criterion_id,
                dimension_id,
                effect=effect,
                finding_type=finding_type,
            )
            evidence.append(projected_evidence)
            findings.append(projected_finding)
    return AIAnalysisDomainProjection(
        analysis_id=uuid4(),
        bundle_id=uuid4(),
        evidence=evidence,
        findings=findings,
    )


def test_all_required_criteria_need_positive_fact_evidence_for_proceed() -> None:
    result = DeterministicReadinessAdjudicator().adjudicate(_complete_projection())

    assert [item.status for item in result.dimensions] == ["Ready", "Ready", "Ready"]
    assert result.overall_gate == "PROCEED"
    assert result.first_next_action.action_type == "Minimum Validation"
    assert all(item.outcome == "supported" for item in result.criterion_decisions)


def test_explicit_fact_failure_blocks_dimension_and_triggers_pause() -> None:
    projection = _complete_projection(
        override=("rd03.checkpoint_access", "condition_not_met", "Fact")
    )
    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.dimensions[2].status == "Blocked"
    assert result.overall_gate == "PAUSE"
    assert result.first_next_action.action_type == "Resolve Blocker"
    assert result.trigger_refs[0] == "RD-03"


def test_missing_criterion_is_unknown_not_ready_or_blocked() -> None:
    projection = _complete_projection()
    missing_id = "f-rd02.environment_compatibility"
    projection = projection.model_copy(
        update={
            "findings": [
                item for item in projection.findings if item.finding_candidate_id != missing_id
            ],
            "evidence": [
                item
                for item in projection.evidence
                if item.evidence_candidate_id != f"e-{missing_id}"
            ],
        }
    )

    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.dimensions[1].status == "Unknown"
    assert result.overall_gate == "CONDITIONAL PROCEED"
    assert result.first_next_action.action_type == "Resolve Gate-critical Unknown"
    assert any(
        item.finding_id == "rule-missing-rd02.environment_compatibility"
        for item in result.dimensions[1].findings
    )
    decisive_finding = result.dimensions[1].findings[0]
    assert result.dimensions[1].summary == decisive_finding.summary
    assert result.dimensions[1].gate_impact == (
        "Project-to-user environment compatibility is Gate-critical; full PROCEED waits "
        "for its verification."
    )
    assert result.main_risk == decisive_finding.title
    assert "sufficient, consistent Fact evidence" not in result.dimensions[1].summary
    assert "environment compatibility" in decisive_finding.summary.lower()


def test_inference_cannot_be_promoted_to_ready_or_blocked() -> None:
    projection = _complete_projection(
        override=("rd01.dataset_access", "condition_not_met", "Inference")
    )
    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.dimensions[0].status == "Unknown"
    assert result.overall_gate == "CONDITIONAL PROCEED"


def test_known_fact_risk_maps_to_warning() -> None:
    projection = _complete_projection(
        override=("rd02.dependency_requirements", "non_blocking_risk", "Fact")
    )
    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.dimensions[1].status == "Warning"
    assert result.overall_gate == "CONDITIONAL PROCEED"
    assert result.first_next_action.action_type == "Mitigate Warning"


def test_core_conflict_stays_unknown_and_evaluation_difference_stays_signal() -> None:
    projection = _complete_projection()
    core_sources = projection.findings[0].finding.evidence * 2
    core_conflict = ProjectedConflict(
        conflict_candidate_id="conflict-data-access",
        evidence_candidate_ids=["e-f-rd01.dataset_identity", "e-f-rd01.dataset_access"],
        criterion_id="rd01.dataset_access",
        disposition="authoritative_value_unresolved",
        conflict=EvidenceConflict(
            conflict_id="conflict-data-access",
            condition_key="data.access",
            dimension_ids=["RD-01"],
            summary="Two admitted sources disagree about anonymous access.",
            sources=core_sources,
        ),
    )
    eval_conflict = ProjectedConflict(
        conflict_candidate_id="conflict-evaluation",
        evidence_candidate_ids=["e-f-rd03.configuration_mapping", "e-f-rd03.execution_contract"],
        criterion_id="evaluation.paper_code_setting",
        disposition="known_difference",
        conflict=EvidenceConflict(
            conflict_id="conflict-evaluation",
            condition_key="evaluation.setting",
            dimension_ids=["RD-03"],
            summary="Paper and code use different evaluation settings.",
            sources=projection.findings[-1].finding.evidence * 2,
        ),
    )
    projection = projection.model_copy(update={"conflicts": [core_conflict, eval_conflict]})

    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.dimensions[0].status == "Unknown"
    assert result.dimensions[2].status == "Ready"
    assert result.evaluation_signal.status == "Warning"
    assert result.evaluation_signal.conflict_type == "Paper-Code Setting"
    assert result.overall_gate == "CONDITIONAL PROCEED"


def test_unresolved_question_is_gate_critical_unknown() -> None:
    projection = _complete_projection()
    question = UnresolvedQuestion(
        question_id="q-checkpoint",
        condition_key="weights.access",
        criterion_id="rd03.checkpoint_access",
        dimension_id="RD-03",
        question="Is the required checkpoint publicly accessible?",
        missing_information="Anonymous checkpoint access was not established.",
        inspected_source_ids=["src-readme"],
    )
    projection = projection.model_copy(update={"unresolved_questions": [question]})

    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.dimensions[2].status == "Unknown"
    assert result.first_next_action.action_type == "Resolve Gate-critical Unknown"


def test_unadmitted_candidate_does_not_create_a_fourth_gate_state() -> None:
    projection = _complete_projection().model_copy(
        update={"human_confirmation_candidate_ids": ["candidate-needs-human"]}
    )
    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.decision_available is True
    assert result.overall_gate == "PROCEED"
    assert [item.status for item in result.dimensions] == ["Ready", "Ready", "Ready"]
    assert result.unavailable_reason is None


def test_invalid_analysis_source_identity_keeps_gate_unavailable() -> None:
    projection = AIAnalysisDomainProjection(
        analysis_id=uuid4(),
        bundle_id=uuid4(),
        analysis_source_ids_verified=False,
        analysis_issues=[
            EvidenceValidationIssue(
                code="source_not_examined",
                message="A bundle source was omitted from the model analysis.",
            )
        ],
    )
    result = DeterministicReadinessAdjudicator().adjudicate(projection)

    assert result.decision_available is False
    assert result.unavailable_reason.startswith("The AI analysis source set failed")


def test_same_candidate_graph_produces_identical_business_decision() -> None:
    projection = _complete_projection()
    service = DeterministicReadinessAdjudicator()

    first = service.adjudicate(projection)
    second = service.adjudicate(projection)

    assert first.model_dump(exclude={"analysis_id", "bundle_id"}) == second.model_dump(
        exclude={"analysis_id", "bundle_id"}
    )
