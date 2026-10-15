"""Projection of admitted AI candidates into stable Readiness domain objects."""

from uuid import uuid4

import pytest

from researchops.schemas import (
    AIAnalysisResult,
    CollectedMaterial,
    ConflictCandidate,
    EvidenceCandidate,
    EvidenceValidationResult,
    FindingCandidate,
    ResolvedTarget,
    SourceLocator,
    UnresolvedQuestion,
)
from researchops.services import (
    DeterministicCandidateGraphValidator,
    DeterministicEvidenceRuleValidator,
    DomainProjectionError,
    MaterialBundleBuilder,
    ReadinessDomainProjectionService,
)


def _target() -> ResolvedTarget:
    return ResolvedTarget(
        target_type="repository",
        source_entry="https://github.com/example/project",
        display_name="example/project",
        canonical_id="github:example/project",
        canonical_url="https://github.com/example/project",
        resolution_method="direct_url",
    )


def _bundle(*materials: CollectedMaterial):
    return MaterialBundleBuilder().build(_target(), materials).bundle


def _material(
    path: str,
    content: str,
    *,
    access_scope: str = "public",
    source_url: str | None = None,
) -> CollectedMaterial:
    return CollectedMaterial(
        material_type="README",
        title=path,
        source_path=path,
        source_url=source_url,
        content=content,
        access_scope=access_scope,
        priority=100,
    )


def _evidence(
    candidate_id: str,
    source_id: str,
    quote: str,
    claim: str,
    *,
    evidence_type: str = "Fact",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        candidate_id=candidate_id,
        condition_key="evaluation.metric",
        dimension_ids=["RD-03"],
        evidence_type=evidence_type,
        claim=claim,
        locator=SourceLocator(
            source_id=source_id,
            location="model location",
            line_start=1,
            line_end=1,
        ),
        quote=quote,
        confidence=0.9,
        rationale="The model interpreted the exact quote.",
        uncertainty_reason=(
            "The metric remains unresolved." if evidence_type == "Unknown" else None
        ),
    )


def _pipeline(bundle, analysis: AIAnalysisResult):
    validation = DeterministicEvidenceRuleValidator().validate(bundle, analysis)
    adjudication = DeterministicCandidateGraphValidator().validate(analysis, validation)
    projection = ReadinessDomainProjectionService().project(
        bundle,
        analysis,
        validation,
        adjudication,
    )
    return validation, adjudication, projection


def test_projection_preserves_evidence_finding_conflict_and_source_lineage() -> None:
    bundle = _bundle(
        _material(
            "paper.txt",
            "Metric: accuracy",
            source_url="https://example.org/paper",
        ),
        _material(
            "config.yaml",
            "Metric: F1",
            source_url="https://github.com/example/project/blob/main/config.yaml",
        ),
    )
    paper = _evidence(
        "e-paper",
        bundle.sources[1].source_id,
        "Metric: accuracy",
        "The paper uses accuracy.",
    )
    code = _evidence(
        "e-code",
        bundle.sources[0].source_id,
        "Metric: F1",
        "The repository uses F1.",
    )
    conflict = ConflictCandidate(
        candidate_id="conflict-metric",
        condition_key="evaluation.metric",
        dimension_ids=["RD-03"],
        summary="Paper and repository metrics are incompatible.",
        evidence_candidate_ids=[paper.candidate_id, code.candidate_id],
        confidence=0.9,
        uncertainty_reason="The semantic relationship was proposed by the model.",
    )
    finding = FindingCandidate(
        candidate_id="finding-paper-metric",
        condition_key="evaluation.metric",
        primary_dimension_id="RD-03",
        title="Paper metric located",
        summary="The paper states accuracy as its metric.",
        finding_type="Fact",
        evidence_candidate_ids=[paper.candidate_id],
    )
    question = UnresolvedQuestion(
        question_id="question-aggregation",
        condition_key="evaluation.aggregation",
        dimension_id="RD-03",
        question="Which aggregation rule is used?",
        missing_information="No aggregation rule was located.",
        inspected_source_ids=[source.source_id for source in bundle.sources],
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="A metric conflict and one unresolved question were proposed.",
        examined_source_ids=[source.source_id for source in bundle.sources],
        evidence_candidates=[paper, code],
        conflict_candidates=[conflict],
        finding_candidates=[finding],
        unresolved_questions=[question],
    )

    _, _, projection = _pipeline(bundle, analysis)

    assert [item.evidence_candidate_id for item in projection.evidence] == [
        "e-paper",
        "e-code",
    ]
    assert projection.evidence[0].evidence.verification_status == "Located Only"
    assert projection.evidence[0].evidence.source_type == "Material"
    assert projection.evidence[0].evidence.location.endswith(":lines 1-1")
    assert projection.evidence[0].evidence.line_start == 1
    assert projection.evidence[0].evidence.line_end == 1
    assert projection.findings[0].finding.finding_id == "finding-paper-metric"
    assert projection.findings[0].finding.gate_critical is False
    assert projection.findings[0].evidence_candidate_ids == ["e-paper"]
    assert projection.conflicts[0].conflict.conflict_id == "conflict-metric"
    assert projection.conflicts[0].conflict.status == "unresolved"
    assert len(projection.conflicts[0].conflict.sources) == 2
    assert projection.unresolved_questions == [question]


def test_user_supplied_material_projects_as_user_context() -> None:
    bundle = _bundle(_material("manual.txt", "Metric: accuracy", access_scope="user_provided"))
    candidate = _evidence(
        "e-manual",
        bundle.sources[0].source_id,
        "Metric: accuracy",
        "The user reports accuracy.",
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One user-context candidate was proposed.",
        examined_source_ids=[bundle.sources[0].source_id],
        evidence_candidates=[candidate],
    )

    _, _, projection = _pipeline(bundle, analysis)

    assert projection.evidence[0].evidence.source_type == "User Context"


def test_rejected_and_pending_evidence_are_not_projected() -> None:
    bundle = _bundle(_material("README.md", "same quote\nsame quote"))
    rejected = _evidence(
        "e-rejected",
        bundle.sources[0].source_id,
        "invented quote",
        "An invented claim.",
    )
    pending = _evidence(
        "e-pending",
        bundle.sources[0].source_id,
        "same quote",
        "The source repeats the same quote.",
    ).model_copy(
        update={
            "locator": SourceLocator(
                source_id=bundle.sources[0].source_id,
                location="no exact line",
            )
        }
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One rejected and one ambiguous candidate were proposed.",
        examined_source_ids=[bundle.sources[0].source_id],
        evidence_candidates=[rejected, pending],
    )

    _, _, projection = _pipeline(bundle, analysis)

    assert projection.evidence == []
    assert projection.human_confirmation_candidate_ids == ["e-pending"]


def test_controlled_finding_downgrade_is_preserved_in_domain_object() -> None:
    bundle = _bundle(_material("README.md", "Metric may be accuracy"))
    evidence = _evidence(
        "e-inference",
        bundle.sources[0].source_id,
        "Metric may be accuracy",
        "The metric may be accuracy.",
        evidence_type="Inference",
    )
    finding = FindingCandidate(
        candidate_id="finding-metric",
        condition_key="evaluation.metric",
        primary_dimension_id="RD-03",
        title="Metric identified",
        summary="The metric is accuracy.",
        finding_type="Fact",
        evidence_candidate_ids=[evidence.candidate_id],
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="A model-proposed Fact relies on an Inference.",
        examined_source_ids=[bundle.sources[0].source_id],
        evidence_candidates=[evidence],
        finding_candidates=[finding],
    )

    _, adjudication, projection = _pipeline(bundle, analysis)

    assert adjudication.finding_results[0].decision == "downgraded"
    assert projection.findings[0].finding.finding_type == "Inference"


def test_projection_truncates_domain_excerpt_but_candidate_retains_full_quote() -> None:
    long_quote = "x" * 2100
    bundle = _bundle(_material("long.txt", long_quote))
    candidate = _evidence(
        "e-long",
        bundle.sources[0].source_id,
        long_quote,
        "A long quoted passage is present.",
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One long evidence candidate was proposed.",
        examined_source_ids=[bundle.sources[0].source_id],
        evidence_candidates=[candidate],
    )

    _, _, projection = _pipeline(bundle, analysis)

    assert len(candidate.quote) == 2100
    assert len(projection.evidence[0].evidence.excerpt) == 2000


def test_projection_rejects_identity_mismatch_and_forged_accepted_quote() -> None:
    bundle = _bundle(_material("README.md", "Metric: accuracy"))
    candidate = _evidence(
        "e-forged",
        bundle.sources[0].source_id,
        "fabricated quote",
        "A fabricated claim.",
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One candidate was proposed.",
        examined_source_ids=[bundle.sources[0].source_id],
        evidence_candidates=[candidate],
    )
    forged_validation = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, analysis)
        .model_copy(
            update={
                "evidence_results": [
                    EvidenceValidationResult(
                        evidence_candidate_id=candidate.candidate_id,
                        decision="accepted",
                        source_verified=True,
                        quote_verified=True,
                        location_verified=True,
                        verified_locator=candidate.locator,
                        resulting_type="Fact",
                    )
                ]
            }
        )
    )
    adjudication = DeterministicCandidateGraphValidator().validate(analysis, forged_validation)

    with pytest.raises(DomainProjectionError, match="逐字 quote"):
        ReadinessDomainProjectionService().project(
            bundle,
            analysis,
            forged_validation,
            adjudication,
        )

    foreign_adjudication = adjudication.model_copy(update={"bundle_id": uuid4()})
    with pytest.raises(DomainProjectionError, match="身份不匹配"):
        ReadinessDomainProjectionService().project(
            bundle,
            analysis,
            forged_validation,
            foreign_adjudication,
        )


def test_projection_rechecks_accepted_type_location_and_human_queue_boundaries() -> None:
    bundle = _bundle(_material("README.md", "Metric: accuracy\nOther line"))
    candidate = _evidence(
        "e-inference",
        bundle.sources[0].source_id,
        "Metric: accuracy",
        "The metric may be accuracy.",
        evidence_type="Inference",
    )
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One inference candidate was proposed.",
        examined_source_ids=[bundle.sources[0].source_id],
        evidence_candidates=[candidate],
    )
    valid = DeterministicEvidenceRuleValidator().validate(bundle, analysis)

    upgraded_validation = valid.model_copy(
        update={
            "evidence_results": [
                valid.evidence_results[0].model_copy(update={"resulting_type": "Fact"})
            ]
        }
    )
    upgraded_adjudication = DeterministicCandidateGraphValidator().validate(
        analysis, upgraded_validation
    )
    with pytest.raises(DomainProjectionError, match="不得改变"):
        ReadinessDomainProjectionService().project(
            bundle,
            analysis,
            upgraded_validation,
            upgraded_adjudication,
        )

    wrong_locator = SourceLocator(
        source_id=bundle.sources[0].source_id,
        location="README.md:lines 2-2",
        line_start=2,
        line_end=2,
    )
    wrong_location_validation = valid.model_copy(
        update={
            "evidence_results": [
                valid.evidence_results[0].model_copy(update={"verified_locator": wrong_locator})
            ]
        }
    )
    wrong_location_adjudication = DeterministicCandidateGraphValidator().validate(
        analysis, wrong_location_validation
    )
    with pytest.raises(DomainProjectionError, match="行号"):
        ReadinessDomainProjectionService().project(
            bundle,
            analysis,
            wrong_location_validation,
            wrong_location_adjudication,
        )

    valid_adjudication = DeterministicCandidateGraphValidator().validate(analysis, valid)
    overlapping_human_queue = valid_adjudication.model_copy(
        update={"human_confirmation_candidate_ids": [candidate.candidate_id]}
    )
    with pytest.raises(DomainProjectionError, match="不能同时"):
        ReadinessDomainProjectionService().project(
            bundle,
            analysis,
            valid,
            overlapping_human_queue,
        )
