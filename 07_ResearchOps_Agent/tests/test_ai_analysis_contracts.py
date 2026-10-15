"""AI / Rule / Human boundary contracts for the model-backed MVP."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import ValidationError

from researchops.schemas import (
    AIAnalysisResult,
    AIAnalysisValidationResult,
    ConflictCandidate,
    EvidenceCandidate,
    EvidenceValidationIssue,
    EvidenceValidationResult,
    FindingCandidate,
    HumanFeedback,
    MaterialBundle,
    MaterialSource,
    ResolvedTarget,
    SourceLocator,
)


def _source(source_id: str = "src-readme") -> MaterialSource:
    content = "Python 3.11 is required. Use the public checkpoint for evaluation."
    return MaterialSource(
        source_id=source_id,
        material_type="README",
        title="README",
        source_path="README.md",
        source_url="https://github.com/example/project/blob/main/README.md",
        content=content,
        content_sha256=sha256(content.encode()).hexdigest(),
        access_scope="public",
    )


def test_merged_analysis_bounds_retain_three_local_dimension_batches() -> None:
    properties = AIAnalysisResult.model_json_schema()["properties"]

    assert properties["evidence_candidates"]["maxItems"] == 96
    assert properties["conflict_candidates"]["maxItems"] == 48
    assert properties["finding_candidates"]["maxItems"] == 72
    assert properties["unresolved_questions"]["maxItems"] == 48


def _bundle() -> MaterialBundle:
    return MaterialBundle(
        bundle_id=uuid4(),
        target=ResolvedTarget(
            target_type="repository",
            source_entry="https://github.com/example/project",
            display_name="example/project",
            canonical_id="github:example/project",
            canonical_url="https://github.com/example/project",
            resolution_method="direct_url",
        ),
        assembled_at=datetime.now(UTC),
        sources=[_source()],
    )


def _evidence() -> EvidenceCandidate:
    return EvidenceCandidate(
        candidate_id="evidence-python",
        condition_key="environment.python.version",
        dimension_ids=["RD-02"],
        evidence_type="Fact",
        claim="The project requires Python 3.11.",
        locator=SourceLocator(
            source_id="src-readme",
            location="README.md line 1",
            line_start=1,
            line_end=1,
        ),
        quote="Python 3.11 is required.",
        confidence=0.95,
        rationale="The requirement is stated explicitly.",
    )


def test_material_bundle_requires_unique_bounded_sources() -> None:
    bundle = _bundle()
    assert bundle.sources[0].source_id == "src-readme"

    with pytest.raises(ValidationError, match="source_id 必须唯一"):
        MaterialBundle(
            bundle_id=uuid4(),
            target=bundle.target,
            assembled_at=datetime.now(UTC),
            sources=[_source(), _source()],
        )


def test_ai_output_cannot_set_final_status_or_gate() -> None:
    bundle = _bundle()
    payload = {
        "analysis_id": uuid4(),
        "bundle_id": bundle.bundle_id,
        "summary": "The model found one environment requirement.",
        "examined_source_ids": ["src-readme"],
        "evidence_candidates": [_evidence()],
        "overall_gate": "PROCEED",
    }

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        AIAnalysisResult.model_validate(payload)


def test_unknown_candidates_must_explain_uncertainty() -> None:
    payload = _evidence().model_dump()
    payload.update(
        {
            "candidate_id": "evidence-cuda",
            "condition_key": "environment.cuda.version",
            "evidence_type": "Unknown",
        }
    )

    with pytest.raises(ValidationError, match="uncertainty_reason"):
        EvidenceCandidate.model_validate(payload)


def test_analysis_rejects_dangling_candidate_references() -> None:
    bundle = _bundle()
    with pytest.raises(ValidationError, match="不存在的 EvidenceCandidate"):
        AIAnalysisResult(
            analysis_id=uuid4(),
            bundle_id=bundle.bundle_id,
            summary="A conflict was proposed.",
            examined_source_ids=["src-readme"],
            evidence_candidates=[_evidence()],
            conflict_candidates=[
                ConflictCandidate(
                    candidate_id="conflict-python",
                    condition_key="environment.python.version",
                    dimension_ids=["RD-02"],
                    summary="Two sources may specify different Python versions.",
                    evidence_candidate_ids=["evidence-python", "evidence-missing"],
                    confidence=0.7,
                    uncertainty_reason="The second source relationship needs validation.",
                )
            ],
        )


def test_fact_finding_requires_evidence_and_cannot_carry_gate_fields() -> None:
    with pytest.raises(ValidationError, match="必须引用 EvidenceCandidate"):
        FindingCandidate(
            candidate_id="finding-python",
            condition_key="environment.python.version",
            primary_dimension_id="RD-02",
            title="Python requirement located",
            summary="The README states a Python requirement.",
            finding_type="Fact",
        )

    payload = {
        "candidate_id": "finding-python",
        "condition_key": "environment.python.version",
        "primary_dimension_id": "RD-02",
        "title": "Python requirement located",
        "summary": "The README states a Python requirement.",
        "finding_type": "Fact",
        "evidence_candidate_ids": ["evidence-python"],
        "status": "Ready",
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FindingCandidate.model_validate(payload)


def test_finding_can_propose_semantic_effect_but_not_final_status() -> None:
    candidate = FindingCandidate(
        candidate_id="finding-python",
        condition_key="environment.python.version",
        criterion_id="rd02.software_requirements",
        readiness_effect="condition_supported",
        primary_dimension_id="RD-02",
        title="Python requirement located",
        summary="The README states a Python requirement.",
        finding_type="Fact",
        evidence_candidate_ids=["evidence-python"],
    )

    assert candidate.readiness_effect == "condition_supported"
    assert "status" not in candidate.model_dump()
    assert "overall_gate" not in candidate.model_dump()

    mismatched_candidate = FindingCandidate.model_validate(
        {
            **candidate.model_dump(),
            "criterion_id": "rd03.checkpoint_access",
        }
    )
    assert mismatched_candidate.primary_dimension_id == "RD-02"


def test_rule_validation_requires_source_quote_and_location_for_acceptance() -> None:
    with pytest.raises(ValidationError, match="全部验证"):
        EvidenceValidationResult(
            evidence_candidate_id="evidence-python",
            decision="accepted",
            source_verified=True,
            quote_verified=False,
            location_verified=True,
            resulting_type="Fact",
        )

    result = EvidenceValidationResult(
        evidence_candidate_id="evidence-python",
        decision="downgraded",
        source_verified=True,
        quote_verified=True,
        location_verified=False,
        resulting_type="Inference",
        issues=[
            EvidenceValidationIssue(
                code="location_mismatch",
                message="The exact line range could not be confirmed.",
            )
        ],
    )
    validation = AIAnalysisValidationResult(
        analysis_id=uuid4(),
        bundle_id=uuid4(),
        evidence_results=[result],
    )
    assert validation.evidence_results[0].decision == "downgraded"


def test_human_correction_is_a_separate_record_with_required_context() -> None:
    with pytest.raises(ValidationError, match="必须包含 comment"):
        HumanFeedback(
            feedback_id=uuid4(),
            target_type="evidence",
            target_id="evidence-python",
            action="correct",
            submitted_at=datetime.now(UTC),
        )

    feedback = HumanFeedback(
        feedback_id=uuid4(),
        target_type="evidence",
        target_id="evidence-python",
        action="question",
        comment="Does this requirement belong to an optional environment?",
        submitted_at=datetime.now(UTC),
    )
    assert feedback.action == "question"
