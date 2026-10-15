"""Reusable fake-model boundary tests."""

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from researchops.schemas import (
    AIAnalysisInvocation,
    AIAnalysisResult,
    AIEvidenceExtractionInvocation,
    AIEvidenceExtractionResult,
    AIModelTrace,
    EvidenceAreaCoverage,
    EvidenceCandidate,
    MaterialBundle,
    MaterialSource,
    ResolvedTarget,
    SourceLocator,
)
from researchops.services import AIModelTransportError
from researchops.testing import FakeEvidenceExtractionModel, FakeMaterialAnalysisModel


def _bundle() -> MaterialBundle:
    content = "Synthetic README material."
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
        sources=[
            MaterialSource(
                source_id="src-readme",
                material_type="README",
                title="README",
                source_path="README.md",
                source_url="https://github.com/example/project/blob/main/README.md",
                content=content,
                content_sha256=sha256(content.encode()).hexdigest(),
                access_scope="public",
            )
        ],
    )


def _invocation(bundle: MaterialBundle) -> AIAnalysisInvocation:
    now = datetime.now(UTC)
    return AIAnalysisInvocation(
        result=AIAnalysisResult(
            analysis_id=uuid4(),
            bundle_id=bundle.bundle_id,
            summary="Synthetic analysis.",
            examined_source_ids=["src-readme"],
        ),
        trace=AIModelTrace(
            trace_id=uuid4(),
            model="fake-model",
            request_id="fake-request-1",
            started_at=now,
            completed_at=now,
            duration_ms=0,
            attempts=1,
            status="success",
        ),
    )


def test_fake_model_returns_deep_copies_and_records_bundle_identity() -> None:
    bundle = _bundle()
    expected = _invocation(bundle)
    fake = FakeMaterialAnalysisModel([expected, expected])

    first = fake.analyze(bundle)
    first.result.summary = "mutated by test"
    second = asyncio.run(fake.analyze_async(bundle))

    assert second.result.summary == "Synthetic analysis."
    assert fake.bundle_ids == [bundle.bundle_id, bundle.bundle_id]
    assert fake.call_count == 2


def test_fake_model_raises_queued_failure_and_fails_loudly_when_exhausted() -> None:
    bundle = _bundle()
    fake = FakeMaterialAnalysisModel([AIModelTransportError("synthetic outage")])

    with pytest.raises(AIModelTransportError, match="synthetic outage"):
        fake.analyze(bundle)
    with pytest.raises(AssertionError, match="没有剩余"):
        fake.analyze(bundle)


def test_fake_evidence_model_implements_sync_and_async_extraction_boundary() -> None:
    bundle = _bundle()
    now = datetime.now(UTC)
    evidence = EvidenceCandidate(
        candidate_id="evidence-synthetic",
        condition_key="environment.synthetic",
        dimension_ids=["RD-02"],
        evidence_type="Fact",
        claim="Synthetic README material.",
        locator=SourceLocator(
            source_id="src-readme",
            location="README.md line 1",
            line_start=1,
            line_end=1,
        ),
        quote="Synthetic README material.",
        confidence=1,
        rationale="The exact statement is present.",
    )
    areas = [
        "rd01_data_access",
        "rd02_environment_dependency",
        "rd03_weights_configuration",
        "resource_constraint",
        "evaluation_conditions",
    ]
    invocation = AIEvidenceExtractionInvocation(
        result=AIEvidenceExtractionResult(
            extraction_id=uuid4(),
            bundle_id=bundle.bundle_id,
            summary="Synthetic evidence extraction.",
            examined_source_ids=["src-readme"],
            evidence_candidates=[evidence],
            coverage=[
                EvidenceAreaCoverage(
                    area=area,
                    state="evidence_found",
                    summary="Synthetic coverage.",
                    evidence_candidate_ids=["evidence-synthetic"],
                )
                for area in areas
            ],
        ),
        trace=AIModelTrace(
            trace_id=uuid4(),
            model="fake-model",
            request_id="fake-evidence-request",
            started_at=now,
            completed_at=now,
            duration_ms=0,
            attempts=1,
            status="success",
        ),
    )
    fake = FakeEvidenceExtractionModel([invocation, invocation])

    first = fake.extract_evidence(bundle)
    first.result.summary = "mutated"
    second = asyncio.run(fake.extract_evidence_async(bundle))

    assert second.result.summary == "Synthetic evidence extraction."
    assert fake.bundle_ids == [bundle.bundle_id, bundle.bundle_id]
