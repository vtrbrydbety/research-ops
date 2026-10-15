"""公开 GitHub Repository 材料采集测试。"""

import base64

import httpx

from researchops.schemas import AssessmentRequest, ResolvedTarget
from researchops.services import (
    GitHubRepositoryMaterialCollector,
    ReadinessAssessmentService,
    RepositoryCollectionError,
)


def encoded_file(path: str, text: str) -> dict[str, object]:
    """生成 GitHub Contents API 风格的文本响应。"""

    raw = text.encode()
    return {
        "name": path.rsplit("/", 1)[-1],
        "path": path,
        "size": len(raw),
        "encoding": "base64",
        "content": base64.b64encode(raw).decode(),
        "html_url": f"https://github.com/example/project/blob/main/{path}",
    }


def test_collector_reads_only_bounded_repository_materials() -> None:
    """Collector 读取元数据、README、文件树和受支持的依赖文件。"""

    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        responses: dict[str, dict[str, object]] = {
            "/repos/example/project": {
                "default_branch": "main",
                "html_url": "https://github.com/example/project",
            },
            "/repos/example/project/readme": encoded_file(
                "README.md",
                "Download the Example dataset from "
                "https://www.kaggle.com/datasets/example/project\n"
                "Final model weight file: "
                "https://drive.google.com/drive/folders/checkpoint-example\n",
            ),
            "/repos/example/project/git/trees/main": {
                "tree": [
                    {"path": "README.md", "type": "blob"},
                    {"path": "package-list.txt", "type": "blob"},
                    {"path": "configs/eval.yaml", "type": "blob"},
                    {"path": "src/main.py", "type": "blob"},
                ]
            },
            "/repos/example/project/contents/package-list.txt": encoded_file(
                "package-list.txt",
                "python=3.11\ntorch=2.2\n",
            ),
            "/repos/example/project/contents/configs/eval.yaml": encoded_file(
                "configs/eval.yaml",
                "metric: auc\n",
            ),
        }
        payload = responses.get(request.url.path)
        if payload is None:
            return httpx.Response(404, json={"message": "Not Found"})
        return httpx.Response(200, json=payload)

    client = httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(handler),
    )
    collector = GitHubRepositoryMaterialCollector(client=client)
    target = ResolvedTarget(
        target_type="repository",
        source_entry="https://github.com/example/project",
        display_name="example/project",
        canonical_id="github:example/project",
        canonical_url="https://github.com/example/project",
        resolution_method="direct_url",
    )

    materials = collector.collect(target)
    cached_materials = collector.collect(target)

    assert materials.default_branch == "main"
    assert materials.readme is not None
    assert materials.readme.path == "README.md"
    assert [item.path for item in materials.dependency_files] == ["package-list.txt"]
    assert [item.path for item in materials.evaluation_files] == ["configs/eval.yaml"]
    assert materials.relevant_paths == (
        "README.md",
        "configs/eval.yaml",
        "package-list.txt",
    )
    assert [item.url for item in materials.external_asset_references] == [
        "https://drive.google.com/drive/folders/checkpoint-example"
    ]
    assert [item.url for item in materials.dataset_references] == [
        "https://www.kaggle.com/datasets/example/project"
    ]
    assert cached_materials.dataset_references == materials.dataset_references
    assert requested_paths == [
        "/repos/example/project",
        "/repos/example/project/readme",
        "/repos/example/project/git/trees/main",
        "/repos/example/project/contents/package-list.txt",
        "/repos/example/project/contents/configs/eval.yaml",
    ]


def test_collector_rejects_non_github_resolved_target() -> None:
    """Collector 不接受任意 URL，防止目标解析边界被绕过。"""

    collector = GitHubRepositoryMaterialCollector(
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: None))
    )
    target = ResolvedTarget(
        target_type="project_page",
        source_entry="https://example.org/project",
        display_name="example.org/project",
        canonical_id="project:example.org/project",
        canonical_url="https://example.org/project",
        resolution_method="direct_url",
    )

    try:
        collector.collect(target)
    except RuntimeError as exc:
        assert "GitHub Repository" in str(exc)
    else:
        raise AssertionError("non-GitHub target should not be collected")


def test_collector_reads_one_explicit_public_github_blob_file() -> None:
    requested: list[tuple[str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append((request.url.path, request.url.params.get("ref")))
        if request.url.path == "/repos/example/project/contents/LICENSE":
            return httpx.Response(200, json=encoded_file("LICENSE", "Dataset terms apply.\n"))
        return httpx.Response(404, json={"message": "Not Found"})

    collector = GitHubRepositoryMaterialCollector(
        client=httpx.Client(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(handler),
        )
    )

    material = collector.read_file_url(
        "https://github.com/example/project/blob/main/LICENSE"
    )

    assert material is not None
    assert material.path == "LICENSE"
    assert material.text == "Dataset terms apply.\n"
    assert requested == [("/repos/example/project/contents/LICENSE", "main")]


def test_optional_evaluation_file_failure_does_not_abort_collection() -> None:
    """可选 Evaluation Signal 材料失败不得拖垮核心仓库采集。"""

    def handler(request: httpx.Request) -> httpx.Response:
        responses: dict[str, dict[str, object]] = {
            "/repos/example/project": {
                "default_branch": "main",
                "html_url": "https://github.com/example/project",
            },
            "/repos/example/project/readme": encoded_file("README.md", "Project setup.\n"),
            "/repos/example/project/git/trees/main": {
                "tree": [{"path": "configs/eval.yaml", "type": "blob"}]
            },
        }
        payload = responses.get(request.url.path)
        if payload is None:
            return httpx.Response(503, json={"message": "Temporary failure"})
        return httpx.Response(200, json=payload)

    collector = GitHubRepositoryMaterialCollector(
        client=httpx.Client(
            base_url="https://api.github.com",
            transport=httpx.MockTransport(handler),
        )
    )
    target = ResolvedTarget(
        target_type="repository",
        source_entry="https://github.com/example/project",
        display_name="example/project",
        canonical_id="github:example/project",
        canonical_url="https://github.com/example/project",
        resolution_method="direct_url",
    )

    materials = collector.collect(target)

    assert materials.readme is not None
    assert materials.evaluation_files == ()


def test_assessment_withholds_gate_when_repository_collection_fails() -> None:
    """真实采集失败时返回 Partial Result，不退回虚构的 Mock Gate。"""

    class FailingCollector:
        def collect(self, _target: object) -> None:
            raise RepositoryCollectionError("GitHub API timeout")

    service = ReadinessAssessmentService(repository_material_collector=FailingCollector())
    assessment = service.create_assessment(
        AssessmentRequest(
            target_type="repository",
            target_entry="https://github.com/example/project",
        )
    )

    assert assessment.status == "partial"
    assert assessment.analysis_state == "acquisition_failure"
    assert assessment.data_mode == "live_repository"
    assert assessment.gate_available is False
    assert assessment.overall_gate is None
    assert {dimension.status for dimension in assessment.dimensions} == {None}
    assert {dimension.analysis_state for dimension in assessment.dimensions} == {
        "acquisition_failure"
    }
    assert assessment.first_next_action.title == "Retry public Repository material collection"
