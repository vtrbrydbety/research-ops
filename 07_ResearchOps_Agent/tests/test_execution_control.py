"""Bounded work and model attempts under contention and failure."""

from threading import Event

import httpx
import pytest

from researchops.core.access_context import AccessContext, current_access
from researchops.core.config import Settings
from researchops.services.access_store import AccessError, AccessStore
from researchops.services.execution_control import ExecutionController


@pytest.fixture
def execution(tmp_path):
    config = Settings(
        _env_file=None,
        security_store_dir=tmp_path / "s",
        execution_concurrency=1,
        execution_queue_size=1,
    )
    store = AccessStore(config)
    principal, _ = store.create_invitation("alice")
    marker = current_access.set(AccessContext(principal, store))
    yield store, ExecutionController(store)
    current_access.reset(marker)


def test_fixed_capacity_and_shared_principal_limit(execution):
    store, executor = execution
    started, release = Event(), Event()

    def work():
        started.set()
        assert release.wait(3)
        return "done"

    operation, first = executor.submit(work)
    try:
        assert started.wait(1)
        with pytest.raises(AccessError) as exc:
            executor.submit(lambda: None)
        assert exc.value.code == "PRINCIPAL_BUSY"
        other, _ = store.create_invitation("bob")
        marker = current_access.set(AccessContext(other, store))
        _, queued = executor.submit(lambda: "queued")
        current_access.reset(marker)
        third, _ = store.create_invitation("charlie")
        marker = current_access.set(AccessContext(third, store))
        try:
            with pytest.raises(AccessError) as exc:
                executor.submit(lambda: None)
            assert exc.value.status == 503
        finally:
            current_access.reset(marker)
        assert store.operation(operation)["state"] == "running"
    finally:
        release.set()
    assert first.result(3) == "done"
    assert queued.result(3) == "queued"


def test_revoked_queued_task_never_executes(execution):
    store, executor = execution
    started, release = Event(), Event()
    _, first = executor.submit(lambda: (started.set(), release.wait(3)))
    assert started.wait(1)
    bob, _ = store.create_invitation("bob")
    marker = current_access.set(AccessContext(bob, store))
    executed = Event()
    operation, second = executor.submit(executed.set)
    current_access.reset(marker)
    store.update_invitation(bob, revoke=True)
    release.set()
    first.result(3)
    with pytest.raises(AccessError):
        second.result(3)
    assert not executed.is_set()
    assert store.operation(operation)["state"] == "failed"


def test_deepseek_retries_count_before_network(execution):
    from researchops.services.deepseek_analysis import DeepSeekAnalysisModel
    from tests.test_deepseek_context_gap import _bundle

    store, executor = execution
    store.settings.operation_model_attempts = 1
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(503, json={"error": "synthetic outage"})

    config = Settings(_env_file=None, llm_api_key="synthetic", llm_max_retries=2)
    model = DeepSeekAnalysisModel(
        config,
        client=httpx.Client(transport=httpx.MockTransport(transport)),
        retry_backoff_seconds=0,
    )
    with pytest.raises(AccessError) as exc:
        executor.run(lambda: model.analyze_context_gaps(_bundle()))
    assert exc.value.code == "BUDGET_EXHAUSTED"
    assert len(calls) == 1
    with store.transaction() as db:
        assert db.execute("SELECT count FROM usage WHERE kind='model_attempts'").fetchone()[0] == 1


def test_elapsed_operation_does_not_release_slot_until_real_completion(execution):
    store, executor = execution
    store.settings.execution_timeout_seconds = 1
    started, release = Event(), Event()

    def work():
        started.set()
        assert release.wait(3)

    operation, future = executor.submit(work)
    assert started.wait(1)
    with store.transaction() as db:
        db.execute("UPDATE operations SET started=started-2 WHERE id=?", (operation,))
    assert store.operation(operation)["state"] == "running"
    release.set()
    with pytest.raises(AccessError) as exc:
        future.result(3)
    assert exc.value.code == "EXECUTION_TIMEOUT"
    assert store.operation(operation)["state"] == "failed"


def test_async_model_budget_and_secret_redaction(execution):
    import asyncio

    from researchops.core.security import redact_sensitive_text
    from researchops.services.deepseek_analysis import DeepSeekAnalysisModel
    from tests.test_deepseek_context_gap import _bundle

    store, executor = execution
    store.settings.operation_model_attempts = 1
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(503, json={"error": "synthetic outage"})

    config = Settings(_env_file=None, llm_api_key="synthetic", llm_max_retries=2)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            model = DeepSeekAnalysisModel(config, async_client=client, retry_backoff_seconds=0)
            await model.analyze_context_gaps_async(_bundle())

    with pytest.raises(AccessError):
        executor.run(lambda: asyncio.run(run()))
    assert len(calls) == 1
    for key in ["invitation_code", "csrf_token", "session_token", "TunnelSecret", "Cookie"]:
        assert "synthetic-secret-value" not in redact_sensitive_text(
            f'"{key}": "synthetic-secret-value"'
        )


def test_oversized_model_input_never_reaches_provider(execution):
    from researchops.services.deepseek_analysis import DeepSeekAnalysisModel
    from tests.test_deepseek_context_gap import _bundle

    store, executor = execution
    store.settings.model_request_max_bytes = 1
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request)))
    model = DeepSeekAnalysisModel(Settings(_env_file=None, llm_api_key="synthetic"), client=client)
    with pytest.raises(AccessError) as exc:
        executor.run(lambda: model.analyze_context_gaps(_bundle()))
    assert exc.value.code == "MODEL_INPUT_TOO_LARGE" and not calls
