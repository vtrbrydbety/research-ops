"""RD-01 数据入口与访问条件核验测试。"""

from datetime import UTC, datetime

import httpx

from researchops.services import (
    DataAccessService,
    DatasetAccessProbeResult,
    DatasetReference,
    PublicDatasetAccessProbe,
    RepositoryMaterials,
    RepositoryTextFile,
)

REPOSITORY_URL = "https://github.com/example/project"


def reference(name: str, url: str, line: int) -> DatasetReference:
    return DatasetReference(
        name=name,
        url=url,
        source_path="README.md",
        line_number=line,
        excerpt=f"Download the {name} dataset from {url}",
    )


def materials(*references: DatasetReference) -> RepositoryMaterials:
    readme = RepositoryTextFile(
        path="README.md",
        text="Dataset instructions",
        html_url=f"{REPOSITORY_URL}/blob/main/README.md",
        size=20,
    )
    return RepositoryMaterials(
        repository_url=REPOSITORY_URL,
        default_branch="main",
        readme=readme,
        dependency_files=(),
        relevant_paths=("README.md",),
        fetched_at=datetime.now(UTC),
        dataset_references=references,
    )


def test_kaggle_competition_entry_preserves_account_and_terms_unknown() -> None:
    url = "https://www.kaggle.com/c/example/data"
    probe = PublicDatasetAccessProbe(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    text="Competition data page",
                    headers={"content-type": "text/html"},
                )
            )
        )
    )

    result = probe.probe(url)

    assert result.state == "account_required"
    assert "terms" in result.detail


def test_public_instructions_can_expose_an_approval_requirement() -> None:
    url = "https://github.com/example/dataset/blob/main/README.md"
    probe = PublicDatasetAccessProbe(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    text="Fill out the request form. Once accepted, access is granted.",
                    headers={"content-type": "text/html"},
                )
            )
        )
    )

    result = probe.probe(url)

    assert result.state == "approval_required"


def test_direct_public_artifact_can_support_ready() -> None:
    url = "https://zenodo.org/records/example/files/data.zip"
    probe = PublicDatasetAccessProbe(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    content=b"bounded-test-content",
                    headers={"content-type": "application/zip"},
                )
            )
        )
    )
    service = DataAccessService(probe)

    evaluation = service.evaluate(materials(reference("Example", url, 2)))

    assert evaluation.status == "Ready"
    assert evaluation.finding_type == "Fact"


def test_http_not_found_is_distinct_from_transport_failure() -> None:
    url = "https://zenodo.org/records/missing/files/data.zip"
    not_found_probe = PublicDatasetAccessProbe(
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _request: httpx.Response(404, text="not found"))
        )
    )

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("synthetic timeout", request=request)

    timeout_probe = PublicDatasetAccessProbe(
        client=httpx.Client(transport=httpx.MockTransport(timeout_handler))
    )

    assert not_found_probe.probe(url).state == "verified_inaccessible"
    assert timeout_probe.probe(url).state == "unreachable"


def test_dataset_redirect_is_blocked_before_requesting_non_allowlisted_host() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.host == "zenodo.org":
            return httpx.Response(
                302,
                headers={"location": "http://127.0.0.1/internal"},
                request=request,
            )
        raise AssertionError("non-allowlisted redirect target must never be requested")

    probe = PublicDatasetAccessProbe(
        client=httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    )

    result = probe.probe("https://zenodo.org/records/example")

    assert result.state == "unsupported"
    assert requested_hosts == ["zenodo.org"]
    assert "blocked" in result.detail


def test_dataset_probe_redacts_sensitive_query_values_from_result() -> None:
    secret = "source-secret-token"
    url = f"https://zenodo.org/records/example?token={secret}&view=1"
    probe = PublicDatasetAccessProbe(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    request=request,
                    text="Public dataset page",
                    headers={"content-type": "text/html"},
                )
            )
        )
    )

    result = probe.probe(url)

    assert secret not in result.source_url
    assert secret not in (result.final_url or "")
    assert "view=1" in result.source_url


def test_multiple_restricted_entries_remain_gate_critical_unknown() -> None:
    class StaticProbe:
        def probe(self, url: str) -> DatasetAccessProbeResult:
            state = "account_required" if "kaggle" in url else "approval_required"
            return DatasetAccessProbeResult(
                source_url=url,
                final_url=url,
                state=state,
                detail=f"Observed access state: {state}.",
            )

    evaluation = DataAccessService(StaticProbe()).evaluate(
        materials(
            reference("DFDC", "https://www.kaggle.com/c/example/data", 2),
            reference(
                "FakeAVCeleb",
                "https://github.com/example/dataset/blob/main/README.md",
                3,
            ),
        )
    )

    assert evaluation.status == "Unknown"
    assert "1 approval-required" in evaluation.summary
    assert "1 account/terms-dependent" in evaluation.summary
    assert evaluation.readiness_impact == "Prevents full PROCEED"
    assert len(evaluation.evidence) == 2
