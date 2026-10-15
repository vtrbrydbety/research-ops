"""Policy and material-boundary tests for deterministic research tool execution."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import httpx

from researchops.schemas import (
    AIResearchPlanResult,
    CollectedMaterial,
    InformationGap,
    MaterialBundle,
    MaterialSource,
    ResolvedTarget,
    ToolRequest,
)
from researchops.services import (
    DeterministicResearchToolExecutor,
    GitHubRepositorySearch,
    PublicSearchHit,
)
from researchops.services.data_access import DatasetAccessProbeResult
from researchops.services.environment_facts import EnvironmentFacts
from researchops.services.external_assets import ExternalAssetProbeResult
from researchops.services.paper_materials import PaperMaterials
from researchops.services.repository_materials import RepositoryMaterials, RepositoryTextFile


def _bundle() -> MaterialBundle:
    content = "Initial paper material."
    return MaterialBundle(
        bundle_id=uuid4(),
        target=ResolvedTarget(
            target_type="doi",
            source_entry="10.1000/example",
            display_name="10.1000/example",
            canonical_id="doi:10.1000/example",
            canonical_url="https://doi.org/10.1000/example",
            resolution_method="normalized_identifier",
        ),
        assembled_at=datetime.now(UTC),
        sources=[
            MaterialSource(
                source_id="src-initial",
                material_type="Paper",
                title="Initial paper",
                source_path="metadata/initial.txt",
                source_url="https://doi.org/10.1000/example",
                content=content,
                content_sha256=sha256(content.encode()).hexdigest(),
                access_scope="public",
            )
        ],
    )


def _checkpoint_bundle() -> MaterialBundle:
    bundle = _bundle()
    readme_content = "## Weights\nDownload checkpoint: https://drive.google.com/file/d/checkpoint-id/view"
    manifest_content = """{
      "repository_url": "https://github.com/example/project",
      "external_asset_references": [{
        "url": "https://drive.google.com/file/d/checkpoint-id/view",
        "source_path": "README.md",
        "line_number": 2,
        "excerpt": "Download checkpoint"
      }]
    }"""
    sources = [
        MaterialSource(
            source_id="src-readme",
            material_type="README",
            title="README.md",
            source_path="README.md",
            source_url="https://github.com/example/project/blob/main/README.md",
            content=readme_content,
            content_sha256=sha256(readme_content.encode()).hexdigest(),
            access_scope="public",
            line_start=1,
            line_end=2,
        ),
        MaterialSource(
            source_id="src-manifest",
            material_type="Repository",
            title="Repository material manifest",
            source_path=".researchops/repository-material-manifest.json",
            source_url="https://github.com/example/project",
            content=manifest_content,
            content_sha256=sha256(manifest_content.encode()).hexdigest(),
            access_scope="public",
            line_start=1,
            line_end=9,
        ),
    ]
    return bundle.model_copy(update={"sources": [*bundle.sources, *sources]})


def _plan(bundle: MaterialBundle, *requests: ToolRequest) -> AIResearchPlanResult:
    gaps = [
        InformationGap(
            gap_id=f"gap-{index}",
            area="rd03_weights_configuration",
            state="missing",
            description=f"Missing material {index}",
            why_needed="Required for evidence extraction.",
            inspected_source_ids=["src-initial"],
        )
        for index, _ in enumerate(requests, start=1)
    ]
    rebound_requests = [
        request.model_copy(update={"gap_ids": [gaps[index].gap_id]})
        for index, request in enumerate(requests)
    ]
    return AIResearchPlanResult(
        plan_id=uuid4(),
        bundle_id=bundle.bundle_id,
        summary="Additional deterministic reads are required.",
        examined_source_ids=["src-initial"],
        state="needs_tool_calls",
        information_gaps=gaps,
        tool_requests=rebound_requests,
    )


def _request(tool_name: str, **arguments: object) -> ToolRequest:
    return ToolRequest(
        request_id=f"request-{tool_name}",
        tool_name=tool_name,
        gap_ids=["temporary-gap"],
        purpose="Collect a bounded source.",
        **arguments,
    )


def _checkpoint_request(request_id: str, url: str) -> ToolRequest:
    return ToolRequest(
        request_id=request_id,
        tool_name="probe_checkpoint_access",
        gap_ids=["temporary-gap"],
        purpose="Collect a bounded checkpoint access source.",
        url=url,
    )


class _EnvironmentService:
    def __init__(self) -> None:
        self.calls = 0

    def acquire(self, mode: str, *, authorized: bool, supplied_text: str | None):
        self.calls += 1
        assert mode == "readonly"
        assert authorized is True
        assert supplied_text is None
        return EnvironmentFacts(source_mode="readonly", python="3.11", cuda="12.1")


class _RepositoryCollector:
    def collect(self, target: ResolvedTarget) -> RepositoryMaterials:
        assert target.canonical_id == "github:example/project"
        return RepositoryMaterials(
            repository_url="https://github.com/example/project",
            default_branch="main",
            readme=RepositoryTextFile(
                path="README.md",
                text="Repository README material.",
                html_url="https://github.com/example/project/blob/main/README.md",
                size=27,
            ),
            dependency_files=(),
            relevant_paths=("README.md",),
            fetched_at=datetime.now(UTC),
        )


class _GitHubFileReader:
    def read_file_url(self, url: str) -> RepositoryTextFile:
        assert url == "https://github.com/example/project/blob/main/LICENSE"
        return RepositoryTextFile(
            path="LICENSE",
            text="Use of the required dataset is permitted for research.",
            html_url=url,
            size=53,
        )


class _PaperCollector:
    def __init__(self) -> None:
        self.calls = 0

    def collect(self, target: ResolvedTarget) -> PaperMaterials:
        self.calls += 1
        return PaperMaterials(
            title=f"Fetched {target.display_name}",
            identifier=target.canonical_id,
            source_url=str(target.canonical_url),
            publisher="Test provider",
            abstract="Bounded fetched paper or page material.",
            fetched_at=datetime.now(UTC),
        )


class _DatasetProbe:
    def probe(self, url: str) -> DatasetAccessProbeResult:
        return DatasetAccessProbeResult(
            source_url=url,
            final_url=url,
            state="public_page",
            detail="The dataset page is publicly readable.",
        )


class _CheckpointProbe:
    def probe(self, url: str) -> ExternalAssetProbeResult:
        return ExternalAssetProbeResult(
            source_url=url,
            final_url=url,
            accessible=True,
            state="verified_public",
            detail="The checkpoint entry is publicly readable.",
        )


class _WebSearch:
    def search(self, query: str) -> tuple[PublicSearchHit, ...]:
        return (
            PublicSearchHit(
                title=f"Result for {query}",
                url="https://example.org/project",
                snippet="Candidate project page.",
            ),
        )


class _HuggingFaceCollector:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def collect(self, url: str) -> CollectedMaterial:
        self.urls.append(url)
        return CollectedMaterial(
            material_type="Checkpoint-Release",
            title="Hugging Face model card: example/model",
            source_path=".researchops/huggingface/models/example/model.json",
            source_url="https://huggingface.co/example/model",
            content='{"gated": false, "siblings": [{"rfilename": "model.safetensors"}]}',
            access_scope="public",
            priority=94,
        )


def test_github_search_uses_fixed_endpoint_and_adds_bounded_material() -> None:
    observed: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["host"] = request.url.host
        observed["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "full_name": "example/project",
                        "html_url": "https://github.com/example/project",
                        "description": "Official implementation",
                    }
                ]
            },
        )

    search = GitHubRepositorySearch(
        client=httpx.Client(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(handler),
        )
    )
    bundle = _bundle()
    plan = _plan(bundle, _request("search_github", query="paper title implementation"))

    result = DeterministicResearchToolExecutor(github_search=search).execute(
        plan.tool_requests, bundle
    )

    assert observed == {"host": "api.github.com", "path": "/search/repositories"}
    assert result.request_results[0].status == "succeeded"
    assert len(result.new_source_ids) == 1
    assert result.output_bundle.sources[0].source_id == "src-initial"
    assert "https://github.com/example/project" in result.output_bundle.sources[-1].content


def test_disabled_tool_and_unconfigured_web_search_are_explicitly_not_executed() -> None:
    bundle = _bundle()
    plan = _plan(bundle, _request("search_web", query="paper title project"))

    disabled = DeterministicResearchToolExecutor(allowed_tools=set()).execute(
        plan.tool_requests, bundle
    )
    unconfigured = DeterministicResearchToolExecutor().execute(plan.tool_requests, bundle)

    assert disabled.request_results[0].status == "denied"
    assert disabled.request_results[0].failure_code == "policy_denied"
    assert unconfigured.request_results[0].status == "not_configured"
    assert unconfigured.request_results[0].failure_code == "provider_not_configured"
    assert disabled.output_bundle.bundle_id == bundle.bundle_id
    assert unconfigured.output_bundle.bundle_id == bundle.bundle_id


def test_configured_web_search_returns_search_results_as_untrusted_material() -> None:
    bundle = _bundle()
    plan = _plan(bundle, _request("search_web", query="paper title project"))

    result = DeterministicResearchToolExecutor(web_search=_WebSearch()).execute(
        plan.tool_requests, bundle
    )

    source = result.output_bundle.sources[-1]
    assert result.request_results[0].status == "succeeded"
    assert source.trust_boundary == "untrusted_data"
    assert "Candidate project page" in source.content


def test_local_environment_is_never_read_without_explicit_executor_authorization() -> None:
    environment = _EnvironmentService()
    bundle = _bundle()
    plan = _plan(
        bundle,
        _request("inspect_local_environment", requires_user_authorization=True),
    )
    executor = DeterministicResearchToolExecutor(environment_service=environment)

    denied = executor.execute(
        plan.tool_requests, bundle, local_environment_authorized=False
    )
    allowed = executor.execute(
        plan.tool_requests, bundle, local_environment_authorized=True
    )

    assert denied.request_results[0].status == "denied"
    assert environment.calls == 1
    assert allowed.request_results[0].status == "succeeded"
    assert allowed.output_bundle.sources[-1].access_scope == "authorized_local"
    assert '"python": "3.11"' in allowed.output_bundle.sources[-1].content


def test_repository_paper_and_project_page_reads_use_existing_bounded_collectors() -> None:
    bundle = _bundle()
    plan = _plan(
        bundle,
        _request("read_github_repository", url="https://github.com/example/project"),
        _request("fetch_paper", identifier="arxiv:2401.12345"),
        _request("fetch_web_page", url="https://example.org/project"),
    )
    result = DeterministicResearchToolExecutor(
        repository_collector=_RepositoryCollector(),
        paper_collector=_PaperCollector(),
        project_page_collector=_PaperCollector(),
    ).execute(plan.tool_requests, bundle)

    assert [item.status for item in result.request_results] == [
        "succeeded",
        "succeeded",
        "succeeded",
    ]
    contents = "\n".join(source.content for source in result.output_bundle.sources)
    assert "Repository README material" in contents
    assert "arxiv:2401.12345" in contents
    assert "project:example.org/project" in contents


def test_fetch_paper_rejects_title_or_url_without_invoking_the_connector() -> None:
    bundle = _bundle()
    valid = _request("fetch_paper", identifier="arxiv:2401.12345").model_copy(
        update={"request_id": "request-paper-valid"}
    )
    invalid = _request(
        "fetch_paper", identifier="A paper title instead of a stable identifier"
    ).model_copy(update={"request_id": "request-paper-invalid"})
    invalid_url = _request(
        "fetch_paper", identifier="https://arxiv.org/abs/2401.12345"
    ).model_copy(update={"request_id": "request-paper-url"})
    plan = _plan(bundle, valid, invalid, invalid_url)
    collector = _PaperCollector()

    result = DeterministicResearchToolExecutor(paper_collector=collector).execute(
        plan.tool_requests, bundle
    )

    assert collector.calls == 1
    assert [item.status for item in result.request_results] == [
        "succeeded",
        "failed",
        "failed",
    ]
    assert result.request_results[0].failure_code is None
    assert result.request_results[1].failure_code == "invalid_tool_argument"
    assert result.request_results[2].failure_code == "invalid_tool_argument"
    assert "paper title" not in result.request_results[1].detail.casefold()
    assert len(result.new_source_ids) == 1


def test_explicit_github_file_read_adds_its_text_to_the_material_bundle() -> None:
    bundle = _bundle()
    plan = _plan(
        bundle,
        _request(
            "read_github_file",
            url="https://github.com/example/project/blob/main/LICENSE",
        ),
    )

    result = DeterministicResearchToolExecutor(
        repository_collector=_GitHubFileReader()
    ).execute(plan.tool_requests, bundle)

    assert result.request_results[0].status == "succeeded"
    source = result.output_bundle.sources[-1]
    assert source.source_path == "LICENSE"
    assert "required dataset" in source.content


def test_huggingface_card_read_is_bounded_public_material_not_a_download() -> None:
    bundle = _bundle()
    declared = bundle.sources[0].model_copy(
        update={
            "content": "Official model card: https://huggingface.co/example/model",
            "content_sha256": sha256(
                b"Official model card: https://huggingface.co/example/model"
            ).hexdigest(),
        }
    )
    bundle = bundle.model_copy(update={"sources": [declared]})
    plan = _plan(
        bundle,
        _request("read_huggingface_card", url="https://huggingface.co/example/model"),
    )
    collector = _HuggingFaceCollector()

    result = DeterministicResearchToolExecutor(
        huggingface_collector=collector
    ).execute(plan.tool_requests, bundle)

    assert collector.urls == ["https://huggingface.co/example/model"]
    assert result.request_results[0].status == "succeeded"
    source = result.output_bundle.sources[-1]
    assert source.trust_boundary == "untrusted_data"
    assert source.material_type == "Checkpoint-Release"
    assert "model.safetensors" in source.content


def test_huggingface_card_read_denies_an_address_not_declared_by_material() -> None:
    bundle = _bundle()
    plan = _plan(
        bundle,
        _request("read_huggingface_card", url="https://huggingface.co/example/model"),
    )
    collector = _HuggingFaceCollector()

    result = DeterministicResearchToolExecutor(
        huggingface_collector=collector
    ).execute(plan.tool_requests, bundle)

    assert result.request_results[0].status == "denied"
    assert "not present in the confirmed target or collected material" in result.request_results[0].detail
    assert collector.urls == []


def test_dataset_and_checkpoint_probes_become_traceable_material_sources() -> None:
    bundle = _checkpoint_bundle()
    plan = _plan(
        bundle,
        _request("probe_dataset_access", url="https://huggingface.co/datasets/example/data"),
        _checkpoint_request(
            "request-checkpoint", "https://drive.google.com/file/d/checkpoint-id/view"
        ),
    )
    result = DeterministicResearchToolExecutor(
        dataset_probe=_DatasetProbe(),
        checkpoint_probe=_CheckpointProbe(),
    ).execute(plan.tool_requests, bundle)

    assert [item.status for item in result.request_results] == ["succeeded", "succeeded"]
    added = [
        source
        for source in result.output_bundle.sources
        if source.source_id in result.new_source_ids
    ]
    assert {source.material_type for source in added} == {
        "Dataset Page",
        "Checkpoint-Release",
    }
    assert any('"state": "verified_public"' in source.content for source in added)


def test_checkpoint_probe_denies_model_supplied_external_url_not_declared_in_readme() -> None:
    class _RecordingProbe:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def probe(self, url: str) -> ExternalAssetProbeResult:
            self.urls.append(url)
            return _CheckpointProbe().probe(url)

    bundle = _checkpoint_bundle()
    probe = _RecordingProbe()
    plan = _plan(
        bundle,
        _checkpoint_request("request-untrusted", "https://drive.google.com/file/d/untrusted/view"),
    )

    result = DeterministicResearchToolExecutor(checkpoint_probe=probe).execute(
        plan.tool_requests, bundle
    )

    assert result.request_results[0].status == "denied"
    assert "neither an official repository Release asset" in result.request_results[0].detail
    assert probe.urls == []


def test_official_release_is_probed_before_and_supersedes_readme_external_fallback() -> None:
    class _RecordingProbe:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def probe(self, url: str) -> ExternalAssetProbeResult:
            self.urls.append(url)
            return _CheckpointProbe().probe(url)

    bundle = _checkpoint_bundle()
    release_url = "https://github.com/example/project/releases/download/v1/model.pt"
    probe = _RecordingProbe()
    # The lower-priority README URL intentionally comes first in model output.
    plan = _plan(
        bundle,
        _checkpoint_request(
            "request-readme-fallback", "https://drive.google.com/file/d/checkpoint-id/view"
        ),
        _checkpoint_request("request-official-release", release_url),
    )

    result = DeterministicResearchToolExecutor(checkpoint_probe=probe).execute(
        plan.tool_requests, bundle
    )

    assert [item.status for item in result.request_results] == ["succeeded", "skipped"]
    assert [item.request_id for item in result.request_results] == [
        "request-official-release",
        "request-readme-fallback",
    ]
    assert probe.urls == [release_url]


def test_readme_external_is_used_only_after_official_release_is_not_public() -> None:
    class _FallbackProbe:
        def __init__(self) -> None:
            self.urls: list[str] = []

        def probe(self, url: str) -> ExternalAssetProbeResult:
            self.urls.append(url)
            if "github.com" in url:
                return ExternalAssetProbeResult(
                    source_url=url,
                    final_url=url,
                    accessible=False,
                    state="verified_inaccessible",
                    detail="Official release asset requires access.",
                )
            return _CheckpointProbe().probe(url)

    bundle = _checkpoint_bundle()
    release_url = "https://github.com/example/project/releases/download/v1/model.pt"
    probe = _FallbackProbe()
    plan = _plan(
        bundle,
        _checkpoint_request("request-readme-fallback", "https://drive.google.com/file/d/checkpoint-id/view"),
        _checkpoint_request("request-official-release", release_url),
    )

    result = DeterministicResearchToolExecutor(checkpoint_probe=probe).execute(
        plan.tool_requests, bundle
    )

    assert [item.status for item in result.request_results] == ["succeeded", "succeeded"]
    assert probe.urls == [release_url, "https://drive.google.com/file/d/checkpoint-id/view"]


def test_connector_failure_is_audited_without_fabricating_material() -> None:
    class _FailingSearch:
        def search(self, query: str) -> tuple[PublicSearchHit, ...]:
            raise RuntimeError(f"technical failure for {query}")

    bundle = _bundle()
    plan = _plan(bundle, _request("search_github", query="secret-looking query"))

    result = DeterministicResearchToolExecutor(github_search=_FailingSearch()).execute(
        plan.tool_requests, bundle
    )

    execution = result.request_results[0]
    assert execution.status == "failed"
    assert execution.failure_code == "connector_failure"
    assert execution.source_ids == []
    assert "secret-looking query" not in execution.detail
    assert result.output_bundle.bundle_id == bundle.bundle_id
