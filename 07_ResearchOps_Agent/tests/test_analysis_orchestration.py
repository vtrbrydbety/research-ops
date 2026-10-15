"""Model analysis orchestration and safe run-retention tests."""

from datetime import UTC, datetime
from uuid import uuid4

from researchops.schemas import (
    AIAnalysisInvocation,
    AIAnalysisResult,
    AIAnalysisRun,
    AIModelTrace,
    CollectedMaterial,
    EvidenceCandidate,
    SourceLocator,
)
from researchops.services import (
    AIAnalysisService,
    AIModelConfigurationError,
    AIModelResponseError,
    AIModelTransportError,
    InMemoryAIAnalysisRunStore,
    MaterialBundleBuilder,
)


def _bundle():
    from researchops.schemas import ResolvedTarget

    target = ResolvedTarget(
        target_type="repository",
        source_entry="https://github.com/example/project",
        display_name="example/project",
        canonical_id="github:example/project",
        canonical_url="https://github.com/example/project",
        resolution_method="direct_url",
    )
    return (
        MaterialBundleBuilder()
        .build(
            target,
            [
                CollectedMaterial(
                    material_type="README",
                    title="README",
                    source_path="README.md",
                    content="Private source phrase: do not store the complete source in the run.",
                    access_scope="user_provided",
                    priority=100,
                )
            ],
        )
        .bundle
    )


def _success_invocation(bundle, *, result_bundle_id=None) -> AIAnalysisInvocation:
    source = bundle.sources[0]
    analysis = AIAnalysisResult(
        analysis_id=uuid4(),
        bundle_id=result_bundle_id or bundle.bundle_id,
        summary="One environment requirement was proposed.",
        examined_source_ids=[source.source_id],
        evidence_candidates=[
            EvidenceCandidate(
                candidate_id="evidence-python",
                condition_key="environment.python.version",
                dimension_ids=["RD-02"],
                evidence_type="Fact",
                claim="The source mentions a private source phrase.",
                locator=SourceLocator(
                    source_id=source.source_id,
                    location="README.md line 1",
                    line_start=1,
                    line_end=1,
                ),
                quote="Private source phrase",
                confidence=0.8,
                rationale="The phrase appears directly in the bounded source.",
            )
        ],
    )
    now = datetime.now(UTC)
    trace = AIModelTrace(
        trace_id=uuid4(),
        model="deepseek-v4-flash",
        request_id="request-1",
        started_at=now,
        completed_at=now,
        duration_ms=10,
        attempts=1,
        status="success",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
    )
    return AIAnalysisInvocation(result=analysis, trace=trace)


def _failure_trace(error_type: str) -> AIModelTrace:
    now = datetime.now(UTC)
    return AIModelTrace(
        trace_id=uuid4(),
        model="deepseek-v4-flash",
        request_id="request-failed",
        started_at=now,
        completed_at=now,
        duration_ms=20,
        attempts=3,
        status="failed",
        error_type=error_type,
    )


class _ReturningModel:
    def __init__(self, invocation: AIAnalysisInvocation) -> None:
        self.invocation = invocation

    def analyze(self, _bundle):
        return self.invocation


class _RaisingModel:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def analyze(self, _bundle):
        raise self.error


def test_successful_analysis_saves_candidates_and_safe_trace_without_raw_bundle() -> None:
    bundle = _bundle()
    store = InMemoryAIAnalysisRunStore()
    service = AIAnalysisService(_ReturningModel(_success_invocation(bundle)), store)

    run = service.analyze(bundle)

    assert run.state == "completed"
    assert run.invocation is not None
    assert run.invocation.result.evidence_candidates[0].candidate_id == "evidence-python"
    assert run.invocation.trace.total_tokens == 150
    assert service.get_run(run.run_id) == run
    assert "do not store the complete source" not in run.model_dump_json()

    retrieved = service.get_run(run.run_id)
    assert retrieved is not None and retrieved.invocation is not None
    retrieved.invocation.result.summary = "mutated by caller"
    stored_again = service.get_run(run.run_id)
    assert stored_again is not None and stored_again.invocation is not None
    assert stored_again.invocation.result.summary == "One environment requirement was proposed."


def test_missing_model_configuration_is_a_distinct_non_invocation_state() -> None:
    bundle = _bundle()
    service = AIAnalysisService(
        _RaisingModel(AIModelConfigurationError("provider detail that must not leak"))
    )

    run = service.analyze(bundle)

    assert run.state == "configuration_required"
    assert run.error_code == "llm_configuration_required"
    assert run.failure_trace is None
    assert "provider detail" not in (run.error_message or "")


def test_transport_failure_is_saved_as_model_unavailable_with_trace() -> None:
    bundle = _bundle()
    error = AIModelTransportError(
        "raw upstream body must not leak",
        trace=_failure_trace("http_503"),
    )

    run = AIAnalysisService(_RaisingModel(error)).analyze(bundle)

    assert run.state == "model_unavailable"
    assert run.error_code == "llm_provider_unavailable"
    assert run.failure_trace is not None
    assert run.failure_trace.error_type == "http_503"
    assert "raw upstream body" not in run.model_dump_json()


def test_invalid_structured_response_is_not_misreported_as_provider_outage() -> None:
    bundle = _bundle()
    error = AIModelResponseError(
        "invalid content detail",
        trace=_failure_trace("ValidationError"),
    )

    run = AIAnalysisService(_RaisingModel(error)).analyze(bundle)

    assert run.state == "invalid_model_response"
    assert run.error_code == "llm_response_invalid"
    assert run.failure_trace is not None
    assert run.failure_trace.error_type == "ValidationError"


def test_orchestrator_rejects_result_for_another_bundle() -> None:
    bundle = _bundle()
    wrong_invocation = _success_invocation(bundle, result_bundle_id=uuid4())

    run = AIAnalysisService(_ReturningModel(wrong_invocation)).analyze(bundle)

    assert run.state == "invalid_model_response"
    assert run.invocation is None
    assert run.failure_trace is not None
    assert run.failure_trace.error_type == "bundle_identity_mismatch"


def _completed_run() -> AIAnalysisRun:
    bundle = _bundle()
    return AIAnalysisRun(
        run_id=uuid4(),
        bundle_id=bundle.bundle_id,
        state="completed",
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        invocation=_success_invocation(bundle),
    )


def test_run_store_expires_entries_without_extending_ttl_on_read() -> None:
    current_time = [100.0]
    store = InMemoryAIAnalysisRunStore(
        ttl_seconds=10,
        max_entries=2,
        clock=lambda: current_time[0],
    )
    run = _completed_run()
    store.save(run)

    current_time[0] = 109.0
    assert store.get(run.run_id) == run
    current_time[0] = 110.0
    assert store.get(run.run_id) is None


def test_run_store_evicts_oldest_entry_when_capacity_is_reached() -> None:
    store = InMemoryAIAnalysisRunStore(ttl_seconds=60, max_entries=1)
    first = _completed_run()
    second = _completed_run()

    store.save(first)
    store.save(second)

    assert store.get(first.run_id) is None
    assert store.get(second.run_id) == second
