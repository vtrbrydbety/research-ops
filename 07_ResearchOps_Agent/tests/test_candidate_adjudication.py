"""Conflict / Finding candidate admission against verified Evidence."""

from uuid import uuid4

import pytest

from researchops.schemas import (
    AIAnalysisResult,
    AIAnalysisValidationResult,
    ConflictCandidate,
    EvidenceCandidate,
    EvidenceValidationIssue,
    EvidenceValidationResult,
    FindingCandidate,
    SourceLocator,
)
from researchops.services import (
    CandidateGraphValidationError,
    DeterministicCandidateGraphValidator,
)


def _evidence(
    candidate_id: str,
    *,
    source_id: str,
    claim: str,
    evidence_type: str = "Fact",
    condition_key: str = "evaluation.metric",
    dimension_ids: list[str] | None = None,
    criterion_id: str | None = None,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        candidate_id=candidate_id,
        condition_key=condition_key,
        criterion_id=criterion_id,
        dimension_ids=dimension_ids or ["RD-03"],
        evidence_type=evidence_type,
        claim=claim,
        locator=SourceLocator(
            source_id=source_id,
            location=f"{source_id}:line 1",
            line_start=1,
            line_end=1,
        ),
        quote=claim,
        confidence=0.9,
        rationale="The quoted source supports the candidate interpretation.",
        uncertainty_reason=(
            "The source leaves the value unresolved." if evidence_type == "Unknown" else None
        ),
    )


def _validation(
    candidate: EvidenceCandidate,
    *,
    decision: str = "accepted",
    resulting_type: str | None = None,
) -> EvidenceValidationResult:
    if decision == "accepted":
        return EvidenceValidationResult(
            evidence_candidate_id=candidate.candidate_id,
            decision="accepted",
            source_verified=True,
            quote_verified=True,
            location_verified=True,
            claim_scope_verified=True,
            verified_locator=candidate.locator,
            resulting_type=resulting_type or candidate.evidence_type,
        )
    if decision == "downgraded":
        return EvidenceValidationResult(
            evidence_candidate_id=candidate.candidate_id,
            decision="downgraded",
            source_verified=True,
            quote_verified=True,
            location_verified=False,
            resulting_type="Inference",
            issues=[
                EvidenceValidationIssue(
                    code="location_mismatch",
                    message="The model line range did not match the quote.",
                )
            ],
        )
    if decision == "needs_human_confirmation":
        return EvidenceValidationResult(
            evidence_candidate_id=candidate.candidate_id,
            decision="needs_human_confirmation",
            source_verified=True,
            quote_verified=True,
            location_verified=False,
            issues=[
                EvidenceValidationIssue(
                    code="ambiguous_location",
                    message="The quote occurs more than once.",
                )
            ],
        )
    return EvidenceValidationResult(
        evidence_candidate_id=candidate.candidate_id,
        decision="rejected",
        source_verified=True,
        quote_verified=False,
        location_verified=False,
        issues=[
            EvidenceValidationIssue(
                code="quote_mismatch",
                message="The quote is absent from the source.",
            )
        ],
    )


def _analysis(
    evidence: list[EvidenceCandidate],
    *,
    conflicts: list[ConflictCandidate] | None = None,
    findings: list[FindingCandidate] | None = None,
) -> AIAnalysisResult:
    return AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=uuid4(),
        summary="The model proposed a bounded candidate graph.",
        examined_source_ids=list(dict.fromkeys(item.locator.source_id for item in evidence)),
        evidence_candidates=evidence,
        conflict_candidates=conflicts or [],
        finding_candidates=findings or [],
    )


def _validated_analysis(
    analysis: AIAnalysisResult,
    validations: list[EvidenceValidationResult],
) -> AIAnalysisValidationResult:
    return AIAnalysisValidationResult(
        analysis_id=analysis.analysis_id,
        bundle_id=analysis.bundle_id,
        evidence_results=validations,
    )


def _conflict(first_id: str, second_id: str) -> ConflictCandidate:
    return ConflictCandidate(
        candidate_id="conflict-metric",
        condition_key="evaluation.metric",
        dimension_ids=["RD-03"],
        summary="The paper and repository specify incompatible metrics.",
        evidence_candidate_ids=[first_id, second_id],
        confidence=0.85,
        uncertainty_reason="The semantic incompatibility remains a model interpretation.",
    )


def test_conflict_is_admitted_only_with_two_accepted_cross_source_facts() -> None:
    paper = _evidence("e-paper", source_id="src-paper", claim="Metric: accuracy")
    code = _evidence("e-code", source_id="src-code", claim="Metric: F1")
    conflict = _conflict(paper.candidate_id, code.candidate_id)
    analysis = _analysis([paper, code], conflicts=[conflict])

    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(analysis, [_validation(paper), _validation(code)]),
    )

    assert result.admitted_evidence_candidate_ids == ["e-paper", "e-code"]
    assert result.conflict_results[0].decision == "accepted"
    assert result.admitted_conflict_candidates == [conflict]


def test_conflict_cannot_use_rejected_evidence() -> None:
    paper = _evidence("e-paper", source_id="src-paper", claim="Metric: accuracy")
    code = _evidence("e-code", source_id="src-code", claim="Metric: F1")
    conflict = _conflict(paper.candidate_id, code.candidate_id)
    analysis = _analysis([paper, code], conflicts=[conflict])

    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(
            analysis,
            [_validation(paper), _validation(code, decision="rejected")],
        ),
    )

    assert result.conflict_results[0].decision == "rejected"
    assert result.conflict_results[0].issues[0].code == "evidence_not_accepted"
    assert result.admitted_conflict_candidates == []


def test_conflict_using_downgraded_evidence_requires_human_confirmation() -> None:
    paper = _evidence("e-paper", source_id="src-paper", claim="Metric: accuracy")
    code = _evidence("e-code", source_id="src-code", claim="Metric: F1")
    conflict = _conflict(paper.candidate_id, code.candidate_id)
    analysis = _analysis([paper, code], conflicts=[conflict])

    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(
            analysis,
            [_validation(paper), _validation(code, decision="downgraded")],
        ),
    )

    assert result.conflict_results[0].decision == "needs_human_confirmation"
    assert result.conflict_results[0].issues[0].code == "evidence_not_fact"
    assert "conflict-metric" in result.human_confirmation_candidate_ids
    assert result.admitted_conflict_candidates == []


def test_conflict_using_pending_or_inference_evidence_requires_human_confirmation() -> None:
    paper = _evidence("e-paper", source_id="src-paper", claim="Metric: accuracy")
    code = _evidence(
        "e-code",
        source_id="src-code",
        claim="Metric may be F1",
        evidence_type="Inference",
    )
    conflict = _conflict(paper.candidate_id, code.candidate_id)
    analysis = _analysis([paper, code], conflicts=[conflict])

    inference_result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(analysis, [_validation(paper), _validation(code)]),
    )
    assert inference_result.conflict_results[0].decision == "needs_human_confirmation"
    assert inference_result.conflict_results[0].issues[0].code == "evidence_not_fact"

    pending_result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(
            analysis,
            [_validation(paper), _validation(code, decision="needs_human_confirmation")],
        ),
    )
    assert pending_result.conflict_results[0].decision == "needs_human_confirmation"
    assert "e-code" in pending_result.human_confirmation_candidate_ids
    assert "conflict-metric" in pending_result.human_confirmation_candidate_ids


def test_same_source_or_identical_claims_do_not_form_a_cross_source_conflict() -> None:
    first = _evidence("e-one", source_id="src-one", claim="Metric: accuracy")
    same_source = _evidence("e-two", source_id="src-one", claim="Metric: F1")
    same_source_conflict = _conflict(first.candidate_id, same_source.candidate_id)
    analysis = _analysis([first, same_source], conflicts=[same_source_conflict])
    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(analysis, [_validation(first), _validation(same_source)]),
    )
    assert result.conflict_results[0].issues[0].code == "insufficient_distinct_sources"

    duplicate = _evidence("e-two", source_id="src-two", claim="Metric: accuracy")
    duplicate_conflict = _conflict(first.candidate_id, duplicate.candidate_id)
    duplicate_analysis = _analysis([first, duplicate], conflicts=[duplicate_conflict])
    duplicate_result = DeterministicCandidateGraphValidator().validate(
        duplicate_analysis,
        _validated_analysis(
            duplicate_analysis,
            [_validation(first), _validation(duplicate)],
        ),
    )
    assert duplicate_result.conflict_results[0].issues[0].code == "non_conflicting_evidence"


def test_fact_finding_is_downgraded_when_accepted_evidence_is_only_inference() -> None:
    evidence = _evidence(
        "e-python",
        source_id="src-readme",
        claim="Python version may be 3.11",
        evidence_type="Inference",
        condition_key="environment.python.version",
        dimension_ids=["RD-02"],
    )
    finding = FindingCandidate(
        candidate_id="finding-python",
        condition_key="environment.python.version",
        primary_dimension_id="RD-02",
        title="Python requirement located",
        summary="The project requires Python 3.11.",
        finding_type="Fact",
        evidence_candidate_ids=[evidence.candidate_id],
    )
    analysis = _analysis([evidence], findings=[finding])

    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(analysis, [_validation(evidence)]),
    )

    assert result.finding_results[0].decision == "downgraded"
    assert result.finding_results[0].resulting_type == "Inference"
    assert result.admitted_finding_candidates[0].finding_type == "Inference"


def test_unknown_evidence_cannot_support_fact_but_standalone_unknown_is_admitted() -> None:
    evidence = _evidence(
        "e-cuda",
        source_id="src-readme",
        claim="CUDA requirement is not specified",
        evidence_type="Unknown",
        condition_key="environment.cuda.version",
        dimension_ids=["RD-02"],
    )
    false_fact = FindingCandidate(
        candidate_id="finding-cuda-fact",
        condition_key="environment.cuda.version",
        primary_dimension_id="RD-02",
        title="CUDA version located",
        summary="The CUDA requirement is known.",
        finding_type="Fact",
        evidence_candidate_ids=[evidence.candidate_id],
    )
    unknown = FindingCandidate(
        candidate_id="finding-cuda-unknown",
        condition_key="environment.cuda.version",
        primary_dimension_id="RD-02",
        title="CUDA requirement unresolved",
        summary="The available materials do not establish a CUDA version.",
        finding_type="Unknown",
        uncertainty_reason="No explicit CUDA requirement was found.",
    )
    analysis = _analysis([evidence], findings=[false_fact, unknown])

    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(analysis, [_validation(evidence)]),
    )

    assert result.finding_results[0].decision == "rejected"
    assert result.finding_results[0].issues[0].code == "unknown_evidence_cannot_support_conclusion"
    assert result.finding_results[1].decision == "accepted"
    assert result.admitted_finding_candidates == [unknown]


def test_missing_or_foreign_evidence_validation_result_stops_adjudication() -> None:
    evidence = _evidence("e-one", source_id="src-one", claim="Metric: accuracy")
    analysis = _analysis([evidence])
    incomplete = _validated_analysis(analysis, [])

    with pytest.raises(CandidateGraphValidationError, match="每个 EvidenceCandidate"):
        DeterministicCandidateGraphValidator().validate(analysis, incomplete)

    foreign = _validated_analysis(analysis, [_validation(evidence)]).model_copy(
        update={"analysis_id": uuid4()}
    )
    with pytest.raises(CandidateGraphValidationError, match="身份不匹配"):
        DeterministicCandidateGraphValidator().validate(analysis, foreign)


def test_rule_rejects_finding_with_mismatched_canonical_criterion() -> None:
    evidence = _evidence(
        "e-python",
        source_id="src-readme",
        claim="Python 3.11 is required.",
        condition_key="environment.python.version",
        dimension_ids=["RD-02"],
        criterion_id="rd02.software_requirements",
    )
    finding = FindingCandidate(
        candidate_id="finding-python",
        condition_key="environment.python.version",
        criterion_id="rd03.checkpoint_access",
        readiness_effect="condition_supported",
        primary_dimension_id="RD-02",
        title="Python requirement located",
        summary="The project requires Python 3.11.",
        finding_type="Fact",
        evidence_candidate_ids=[evidence.candidate_id],
    )
    analysis = _analysis([evidence], findings=[finding])

    result = DeterministicCandidateGraphValidator().validate(
        analysis,
        _validated_analysis(analysis, [_validation(evidence)]),
    )

    assert result.finding_results[0].decision == "rejected"
    assert result.finding_results[0].issues[0].code == "criterion_mismatch"
    assert result.admitted_finding_candidates == []
