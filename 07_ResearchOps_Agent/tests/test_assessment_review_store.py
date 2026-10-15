"""Recovery and retention tests for Human review sessions."""

from datetime import UTC, datetime
from uuid import uuid4

from researchops.schemas import AssessmentRequest
from researchops.services.assessment_review_store import DurableAssessmentReviewStore
from researchops.services.human_review import (
    AssessmentReviewSession,
    InMemoryAssessmentReviewStore,
)
from researchops.services.repository_materials import (
    RepositoryMaterials,
    RepositoryTextFile,
)


def _session() -> AssessmentReviewSession:
    assessment_id = uuid4()
    readme = RepositoryTextFile(
        path="README.md",
        text="bounded public material",
        html_url="https://github.com/example/project/blob/main/README.md",
        size=23,
    )
    return AssessmentReviewSession(
        assessment_id=assessment_id,
        state={
            "request": AssessmentRequest(
                target_type="repository",
                target_entry="https://github.com/example/project",
                environment_mode="later",
            ),
            "repository_materials": RepositoryMaterials(
                repository_url="https://github.com/example/project",
                default_branch="main",
                readme=readme,
                dependency_files=(),
                relevant_paths=("README.md",),
                fetched_at=datetime.now(UTC),
            ),
        },
    )


def test_durable_review_store_recovers_typed_session_after_restart(tmp_path) -> None:
    session = _session()
    first_process = DurableAssessmentReviewStore(
        directory=tmp_path,
        ttl_seconds=60,
    )
    first_process.save(session)

    second_process = DurableAssessmentReviewStore(
        directory=tmp_path,
        ttl_seconds=60,
    )
    recovered = second_process.get(session.assessment_id)

    assert recovered is not None
    assert recovered.assessment_id == session.assessment_id
    assert isinstance(recovered.state["request"], AssessmentRequest)
    assert isinstance(recovered.state["repository_materials"], RepositoryMaterials)
    assert isinstance(recovered.state["repository_materials"].readme, RepositoryTextFile)


def test_durable_review_store_uses_sliding_expiration(tmp_path) -> None:
    now = [100.0]
    session = _session()
    store = DurableAssessmentReviewStore(
        directory=tmp_path,
        ttl_seconds=10,
        clock=lambda: now[0],
    )
    store.save(session)

    now[0] = 109.0
    assert store.get(session.assessment_id) is not None

    restarted = DurableAssessmentReviewStore(
        directory=tmp_path,
        ttl_seconds=10,
        clock=lambda: now[0],
    )
    now[0] = 118.0
    assert restarted.get(session.assessment_id) is not None
    now[0] = 129.0
    assert restarted.get(session.assessment_id) is None


def test_durable_review_store_rejects_corrupt_session_without_deserializing(tmp_path) -> None:
    assessment_id = uuid4()
    (tmp_path / f"{assessment_id}.json").write_text(
        '{"version":1,"expires_at":9999999999,"session":{"$kind":"pydantic",'
        '"class":"builtins:eval","value":{}}}',
        encoding="utf-8",
    )
    store = DurableAssessmentReviewStore(directory=tmp_path, ttl_seconds=60)

    assert store.get(assessment_id) is None
    assert not (tmp_path / f"{assessment_id}.json").exists()


def test_in_memory_review_store_uses_sliding_expiration() -> None:
    now = [100.0]
    session = _session()
    store = InMemoryAssessmentReviewStore(
        ttl_seconds=10,
        clock=lambda: now[0],
    )
    store.save(session)

    now[0] = 109.0
    assert store.get(session.assessment_id) is not None
    now[0] = 118.0
    assert store.get(session.assessment_id) is not None
    now[0] = 129.0
    assert store.get(session.assessment_id) is None
