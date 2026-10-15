"""Security ledger invariants, using isolated clocks and on-disk state."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError

from researchops.core.config import Settings
from researchops.services.access_store import AccessError, AccessStore


@pytest.fixture
def ledger(tmp_path):
    clock = [1792000000.0]
    config = Settings(_env_file=None, security_store_dir=tmp_path / "security")
    store = AccessStore(config, clock=lambda: clock[0])
    return store, clock


def test_configuration_is_closed_by_default(monkeypatch):
    monkeypatch.delenv("RESEARCHOPS_DEPLOYMENT_MODE", raising=False)
    assert Settings(_env_file=None).deployment_mode == "public"
    assert Settings(_env_file=None, deployment_mode="local").security_store_dir != Path(
        ".runtime/security"
    )
    for values in (
        {"api_host": "0.0.0.0"},
        {"public_origin": "http://unsafe.test"},
        {"public_origin": "https://safe.test/path"},
        {"trusted_proxy_ips": ["1.1.1.1"]},
    ):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **values)


def test_session_lifecycle_and_no_raw_tokens(ledger):
    store, clock = ledger
    principal, invitation = store.create_invitation("alice")
    token, session = store.exchange(invitation)
    assert store.authenticate(token)["principal_id"] == principal
    assert session["expires_at"] == clock[0] + store.settings.session_seconds
    assert invitation.encode() not in store.path.read_bytes()
    assert token.encode() not in store.path.read_bytes()
    assert "hash" not in store.list_invitations()[0]
    store.logout(token)
    with pytest.raises(AccessError) as exc:
        store.authenticate(token)
    assert exc.value.status == 401
    token, _ = store.exchange(invitation)
    store.update_invitation(principal, revoke=True)
    with pytest.raises(AccessError):
        store.authenticate(token)
    with pytest.raises(AccessError):
        store.exchange(invitation)


def test_expiry_is_absolute_and_ownership_survives_restart(ledger):
    store, clock = ledger
    a, code = store.create_invitation("a")
    b, _ = store.create_invitation("b")
    token, _ = store.exchange(code)
    store.bind("assessment", "resource", a, expires=clock[0] + 100)
    recovered = AccessStore(store.settings, clock=lambda: clock[0])
    recovered.authorize("assessment", "resource", a)
    with pytest.raises(AccessError) as exc:
        recovered.authorize("assessment", "resource", b)
    assert exc.value.status == 404
    clock[0] += 101
    with pytest.raises(AccessError):
        recovered.authorize("assessment", "resource", a)
    clock[0] += store.settings.session_seconds
    with pytest.raises(AccessError):
        recovered.authenticate(token)


def test_last_daily_slot_is_atomic_and_restart_does_not_reset(ledger):
    store, clock = ledger
    store.settings.global_daily_limit = 1
    principals = [store.create_invitation(str(i))[0] for i in range(8)]

    def reserve(principal):
        try:
            return store.reserve(principal)
        except AccessError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(reserve, principals))
    assert sum(result is not None for result in results) == 1
    operation = next(result for result in results if result)
    store.start(operation)
    store.finish(operation)
    recovered = AccessStore(store.settings, clock=lambda: clock[0])
    with pytest.raises(AccessError) as exc:
        recovered.reserve(principals[-1])
    assert exc.value.code == "BUDGET_EXHAUSTED"


def test_attempts_revocation_and_idempotent_refund(ledger):
    store, clock = ledger
    principal, _ = store.create_invitation("a", limit=1)
    operation = store.reserve(principal)
    store.finish(operation, "failed")  # never started, refund once
    store.finish(operation, "failed")
    operation = store.reserve(principal)
    store.start(operation)
    store.settings.operation_model_attempts = 1
    store.attempt(operation, 100)
    with pytest.raises(AccessError):
        store.attempt(operation, 100)
    assert store.operation(operation)["attempts"] == 1
    store.update_invitation(principal, revoke=True)
    with pytest.raises(AccessError):
        store.check_operation(operation)


def test_rate_cleanup_preserves_live_operations(ledger):
    store, clock = ledger
    principal, _ = store.create_invitation("a")
    operation = store.reserve(principal)
    store.rate_limit([("ip", 1, 60)])
    with pytest.raises(AccessError) as exc:
        store.rate_limit([("ip", 1, 60)])
    assert exc.value.status == 429 and exc.value.retry_after > 0
    clock[0] += 61
    store.cleanup()
    store.rate_limit([("ip", 1, 60)])
    assert store.operation(operation)["state"] == "queued"


def test_instance_lock_and_interrupted_state(ledger):
    store, clock = ledger
    principal, _ = store.create_invitation("a")
    operation = store.reserve(principal)
    store.start(operation)
    store.acquire_instance()
    assert store.operation(operation)["state"] == "interrupted"
    second = AccessStore(store.settings, clock=lambda: clock[0])
    with pytest.raises(RuntimeError, match="Another"):
        second.acquire_instance()
    store.release_instance()
    second.acquire_instance()
    second.release_instance()


def test_storage_unavailable_and_permissions_fail_closed(ledger):
    store, _ = ledger
    assert store.path.stat().st_mode & 0o777 == 0o600
    assert store.directory.stat().st_mode & 0o777 == 0o700
    store.path.unlink()
    with pytest.raises(RuntimeError, match="unavailable"):
        store.exchange("anything")


def test_public_retention_is_absolute_and_removes_owner(ledger, tmp_path):
    from researchops.core.access_context import AccessContext, current_access
    from researchops.services.assessment_review_store import DurableAssessmentReviewStore
    from tests.test_assessment_review_store import _session

    store, clock = ledger
    principal, _ = store.create_invitation("a")
    session = _session()
    reviews = DurableAssessmentReviewStore(
        directory=tmp_path / "reviews", ttl_seconds=10, clock=lambda: clock[0]
    )
    marker = current_access.set(AccessContext(principal, store))
    try:
        reviews.save(session)
        store.bind("assessment", session.assessment_id, principal)
        clock[0] += 9
        assert reviews.get(session.assessment_id) is not None
        clock[0] += 2
        assert reviews.get(session.assessment_id) is None
        with pytest.raises(AccessError):
            store.authorize("assessment", session.assessment_id, principal)
    finally:
        current_access.reset(marker)


def test_local_cli_metadata_and_explicit_legacy_binding(ledger, tmp_path, monkeypatch, capsys):
    import json
    import sys

    from researchops import access

    store, _ = ledger
    monkeypatch.setattr(access, "get_settings", lambda: store.settings)
    monkeypatch.setattr(access, "AccessStore", lambda settings: store)

    def command(*arguments):
        monkeypatch.setattr(sys, "argv", ["access", *arguments])
        access.main()
        return capsys.readouterr().out

    created = json.loads(command("create", "--label", "cli", "--limit", "2"))
    listed = command("list")
    assert created["invitation_code"] not in listed and "hash" not in listed
    principal = created["principal_id"]
    command("update", principal, "--limit", "3")
    assert store.list_invitations()[0]["daily_limit"] == 3
    from uuid import uuid4

    assessment = uuid4()
    store.settings.assessment_review_store_dir = tmp_path / "reviews"
    store.settings.assessment_review_store_dir.mkdir()
    (store.settings.assessment_review_store_dir / f"{assessment}.json").write_text(
        json.dumps({"expires_at": store.clock() + 60})
    )
    with pytest.raises(AccessError):
        store.authorize("assessment", assessment, principal)
    command("bind", str(assessment), principal)
    store.authorize("assessment", assessment, principal)
    command("revoke", principal)
    with pytest.raises(AccessError):
        store.exchange(created["invitation_code"])


def test_midnight_refund_and_global_model_attempt_limit(ledger):
    store, clock = ledger
    principal, _ = store.create_invitation("a", limit=1)
    operation = store.reserve(principal)
    original_day = store.operation(operation)["day"]
    clock[0] += 86400
    store.finish(operation, "failed")
    with store.transaction() as db:
        assert (
            db.execute(
                "SELECT count FROM usage WHERE day=? AND principal=?", (original_day, principal)
            ).fetchone()[0]
            == 0
        )
    store.settings.global_daily_model_attempts = 1
    operation = store.reserve(principal)
    store.start(operation)
    store.attempt(operation, 10)
    with pytest.raises(AccessError):
        store.attempt(operation, 10)
    assert store.operation(operation)["attempts"] == 1
