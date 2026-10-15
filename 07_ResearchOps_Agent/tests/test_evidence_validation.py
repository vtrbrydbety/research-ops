"""Deterministic source, quote, and location validation tests."""

from uuid import uuid4

import pytest

from researchops.schemas import (
    AIAnalysisResult,
    CollectedMaterial,
    EvidenceCandidate,
    ResolvedTarget,
    SourceLocator,
)
from researchops.services import (
    DeterministicEvidenceRuleValidator,
    EvidenceRuleValidationError,
    MaterialBundleBuilder,
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


def _bundle(*contents: tuple[str, str], max_source_chars: int = 100_000):
    materials = [
        CollectedMaterial(
            material_type="README",
            title=path,
            source_path=path,
            content=content,
            access_scope="public",
            priority=100 - index,
        )
        for index, (path, content) in enumerate(contents)
    ]
    return (
        MaterialBundleBuilder(
            max_total_chars=200_000,
            max_source_chars=max_source_chars,
            max_sources=10,
        )
        .build(_target(), materials)
        .bundle
    )


def _candidate(
    source_id: str,
    quote: str,
    *,
    line_start: int | None = 2,
    line_end: int | None = 2,
    evidence_type: str = "Fact",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        candidate_id="evidence-python",
        condition_key="environment.python.version",
        dimension_ids=["RD-02"],
        evidence_type=evidence_type,
        claim="The project requires Python 3.11.",
        locator=SourceLocator(
            source_id=source_id,
            location="model supplied location",
            line_start=line_start,
            line_end=line_end,
        ),
        quote=quote,
        confidence=0.9,
        rationale="The model interpreted the quoted source text.",
        uncertainty_reason=(
            "The requirement remains unclear." if evidence_type == "Unknown" else None
        ),
    )


def _analysis(bundle, candidate: EvidenceCandidate, *, examined_ids=None) -> AIAnalysisResult:
    return AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="One evidence candidate was proposed.",
        examined_source_ids=examined_ids or [bundle.sources[0].source_id],
        evidence_candidates=[candidate],
    )


def test_exact_quote_and_line_range_are_accepted_with_canonical_locator() -> None:
    bundle = _bundle(("README.md", "Introduction\nPython 3.11 is required.\nUsage"))
    source_id = bundle.sources[0].source_id
    candidate = _candidate(source_id, "Python 3.11 is required.")

    validation = DeterministicEvidenceRuleValidator().validate(bundle, _analysis(bundle, candidate))
    result = validation.evidence_results[0]

    assert result.decision == "accepted"
    assert result.resulting_type == "Fact"
    assert result.source_verified is True
    assert result.quote_verified is True
    assert result.location_verified is True
    assert result.claim_scope_verified is True
    assert result.verified_locator is not None
    assert result.verified_locator.location == "README.md:lines 2-2"


def test_unique_quote_without_model_line_numbers_gets_deterministic_location() -> None:
    bundle = _bundle(("README.md", "Python 3.11 is required."))
    candidate = _candidate(
        bundle.sources[0].source_id,
        "Python 3.11 is required.",
        line_start=None,
        line_end=None,
        evidence_type="Inference",
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate))
        .evidence_results[0]
    )

    assert result.decision == "accepted"
    assert result.resulting_type == "Inference"
    assert result.verified_locator is not None
    assert result.verified_locator.line_start == 1


def test_repeated_quote_without_line_numbers_requires_human_confirmation() -> None:
    bundle = _bundle(("README.md", "same quote\nother\nsame quote"))
    candidate = _candidate(
        bundle.sources[0].source_id,
        "same quote",
        line_start=None,
        line_end=None,
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate))
        .evidence_results[0]
    )

    assert result.decision == "needs_human_confirmation"
    assert result.quote_verified is True
    assert result.location_verified is False
    assert result.issues[0].code == "ambiguous_location"


def test_wrong_model_line_range_downgrades_fact_without_silently_relocating_it() -> None:
    bundle = _bundle(("README.md", "Introduction\nPython 3.11 is required.\nUsage"))
    candidate = _candidate(
        bundle.sources[0].source_id,
        "Python 3.11 is required.",
        line_start=1,
        line_end=1,
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate))
        .evidence_results[0]
    )

    assert result.decision == "downgraded"
    assert result.resulting_type == "Inference"
    assert result.location_verified is False
    assert result.issues[0].code == "location_mismatch"


def test_claim_with_unquoted_version_anchor_is_downgraded_without_semantic_guessing() -> None:
    bundle = _bundle(("README.md", "Introduction\nPython 3.11 is required.\nUsage"))
    candidate = _candidate(bundle.sources[0].source_id, "Python 3.11 is required.")
    candidate = candidate.model_copy(
        update={"claim": "The project requires Python 3.11 and CUDA 12.1."}
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate))
        .evidence_results[0]
    )

    assert result.decision == "downgraded"
    assert result.resulting_type == "Inference"
    assert result.location_verified is True
    assert result.claim_scope_verified is False
    assert result.issues[0].code == "claim_exceeds_source"


def test_missing_source_and_unexamined_source_are_rejected_explicitly() -> None:
    bundle = _bundle(
        ("README.md", "Python 3.11 is required."),
        ("requirements.txt", "python==3.11"),
    )
    missing_candidate = _candidate(
        "src-missing", "Python 3.11 is required.", line_start=1, line_end=1
    )
    missing_validation = DeterministicEvidenceRuleValidator().validate(
        bundle,
        _analysis(bundle, missing_candidate, examined_ids=["src-missing"]),
    )

    assert missing_validation.analysis_source_ids_verified is False
    assert missing_validation.analysis_issues[0].code == "source_missing"
    assert missing_validation.evidence_results[0].decision == "rejected"
    assert missing_validation.evidence_results[0].issues[0].code == "source_missing"

    unexamined_candidate = _candidate(
        bundle.sources[0].source_id,
        "Python 3.11 is required.",
        line_start=1,
        line_end=1,
    )
    unexamined = (
        DeterministicEvidenceRuleValidator()
        .validate(
            bundle,
            _analysis(bundle, unexamined_candidate, examined_ids=[bundle.sources[1].source_id]),
        )
        .evidence_results[0]
    )

    assert unexamined.decision == "rejected"
    assert unexamined.issues[0].code == "source_not_examined"


def test_missing_quote_in_complete_source_is_rejected() -> None:
    bundle = _bundle(("README.md", "Only Python 3.10 is documented."))
    candidate = _candidate(
        bundle.sources[0].source_id,
        "Python 3.11 is required.",
        line_start=1,
        line_end=1,
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate))
        .evidence_results[0]
    )

    assert result.decision == "rejected"
    assert result.source_verified is True
    assert result.quote_verified is False
    assert result.issues[0].code == "quote_mismatch"


def test_quote_absent_from_truncated_source_is_sent_for_confirmation_not_rejected() -> None:
    bundle = _bundle(
        ("README.md", "prefix text\nThe target quote appears after the context boundary."),
        max_source_chars=12,
    )
    candidate = _candidate(
        bundle.sources[0].source_id,
        "target quote",
        line_start=2,
        line_end=2,
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate))
        .evidence_results[0]
    )

    assert bundle.sources[0].is_truncated is True
    assert result.decision == "needs_human_confirmation"
    assert [issue.code for issue in result.issues] == ["source_truncated", "quote_missing"]


def test_chunk_quote_location_is_mapped_to_original_file_line_numbers() -> None:
    bundle = _bundle(
        ("README.md", "Header one\nHeader two\nPython 3.11 is required.\nUsage"),
        max_source_chars=25,
    )
    source = next(item for item in bundle.sources if "Python 3.11" in item.content)
    candidate = _candidate(
        source.source_id,
        "Python 3.11 is required.",
        line_start=3,
        line_end=3,
    )

    result = (
        DeterministicEvidenceRuleValidator()
        .validate(bundle, _analysis(bundle, candidate, examined_ids=[source.source_id]))
        .evidence_results[0]
    )

    assert source.line_start == 3
    assert result.decision == "accepted"
    assert result.verified_locator is not None
    assert result.verified_locator.location == "README.md:lines 3-3"


def test_analysis_for_another_bundle_never_enters_evidence_validation() -> None:
    bundle = _bundle(("README.md", "Python 3.11 is required."))
    candidate = _candidate(
        bundle.sources[0].source_id,
        "Python 3.11 is required.",
        line_start=1,
        line_end=1,
    )
    analysis = _analysis(bundle, candidate).model_copy(update={"bundle_id": uuid4()})

    with pytest.raises(EvidenceRuleValidationError, match="身份不匹配"):
        DeterministicEvidenceRuleValidator().validate(bundle, analysis)
