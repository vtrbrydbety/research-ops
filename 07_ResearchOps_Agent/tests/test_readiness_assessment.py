"""Sprint 3 Readiness Assessment 契约与 API 测试。"""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api import main as api_main
from researchops.schemas import (
    AIEvidenceFindingDraftInvocation,
    AIEvidenceFindingDraftResult,
    AssessmentRequest,
    Evidence,
    EvidenceConflict,
)
from researchops.services import (
    DataAccessService,
    DatasetAccessProbeResult,
    DatasetReference,
    ExternalAssetProbeResult,
    ExternalAssetReference,
    PaperMaterialCollectionError,
    PaperMaterials,
    PaperMetadata,
    ReadinessAssessmentService,
    RepositoryMaterials,
    RepositoryTextFile,
)
from researchops.services.readiness_workflow import ModelBackedReadinessWorkflowService
from tests.test_model_readiness_graph import (
    FeedbackReassessmentStub,
    PassthroughResearchLoop,
    QuestionOnlyEvidenceModel,
    _trace,
)

client = TestClient(api_main.app)

FGI_REPOSITORY = "https://github.com/aseuteurideu/FGI"


class StaticRepositoryCollector:
    """API 测试使用的确定性 Repository 材料源。"""

    def collect(self, _target: object) -> RepositoryMaterials:
        readme = RepositoryTextFile(
            path="README.md",
            text=(
                "# FGI\n"
                "Download the DFDC dataset from "
                "https://www.kaggle.com/c/deepfake-detection-challenge/data\n"
                "Download the FakeAVCeleb dataset from "
                "https://github.com/DASH-Lab/FakeAVCeleb/blob/main/dataset/README.md\n"
                "Final model weight file: "
                "https://drive.google.com/drive/folders/checkpoint-example\n"
                "python my_train.py --test log/model/model_best_epoch99.pth.tar\n"
            ),
            html_url=f"{FGI_REPOSITORY}/blob/master/README.md",
            size=120,
        )
        dependencies = RepositoryTextFile(
            path="package-list.txt",
            text=(
                "cudatoolkit=11.6.0=hecad31d_10\n"
                "python=3.7.16=h7a1cb2a_0\n"
                "torch=1.12.1+cu116=pypi_0\n"
            ),
            html_url=f"{FGI_REPOSITORY}/blob/master/package-list.txt",
            size=23,
        )
        split_writer = RepositoryTextFile(
            path="write_csv.py",
            text="write_list(test_set, os.path.join(root, 'test_split.csv'))\n",
            html_url=f"{FGI_REPOSITORY}/blob/master/write_csv.py",
            size=62,
        )
        split_loader = RepositoryTextFile(
            path="dataset_3d.py",
            text=(
                "split = os.path.join(root, 'test_imbalance_split.csv')\n"
                "video_info = pd.read_csv(split, header=None)\n"
            ),
            html_url=f"{FGI_REPOSITORY}/blob/master/dataset_3d.py",
            size=108,
        )
        return RepositoryMaterials(
            repository_url=FGI_REPOSITORY,
            default_branch="master",
            readme=readme,
            dependency_files=(dependencies,),
            relevant_paths=("README.md", "package-list.txt"),
            fetched_at=datetime.now(UTC),
            evaluation_files=(split_writer, split_loader),
            external_asset_references=(
                ExternalAssetReference(
                    url="https://drive.google.com/drive/folders/checkpoint-example",
                    source_path="README.md",
                    line_number=4,
                    excerpt=(
                        "Final model weight file: "
                        "https://drive.google.com/drive/folders/checkpoint-example"
                    ),
                ),
            ),
            dataset_references=(
                DatasetReference(
                    name="DFDC",
                    url="https://www.kaggle.com/c/deepfake-detection-challenge/data",
                    source_path="README.md",
                    line_number=2,
                    excerpt="Download the DFDC dataset from Kaggle.",
                ),
                DatasetReference(
                    name="FakeAVCeleb",
                    url=("https://github.com/DASH-Lab/FakeAVCeleb/blob/main/dataset/README.md"),
                    source_path="README.md",
                    line_number=3,
                    excerpt="Download the FakeAVCeleb dataset from its public instructions.",
                ),
            ),
        )


class StaticExternalAssetProbe:
    """API 测试使用的确定性公开权重入口。"""

    def probe(self, url: str) -> ExternalAssetProbeResult:
        return ExternalAssetProbeResult(
            source_url=url,
            final_url=url,
            accessible=True,
            detail="Public checkpoint folder is readable.",
        )


class InaccessibleExternalAssetProbe:
    """模拟需要额外权限的权重入口。"""

    def probe(self, url: str) -> ExternalAssetProbeResult:
        return ExternalAssetProbeResult(
            source_url=url,
            final_url=url,
            accessible=False,
            detail="External asset page requires additional access approval.",
        )


class SelectiveExternalAssetProbe:
    """仅将第二个权重入口视为公开可读。"""

    def probe(self, url: str) -> ExternalAssetProbeResult:
        accessible = "checkpoint-public" in url
        return ExternalAssetProbeResult(
            source_url=url,
            final_url=url,
            accessible=accessible,
            detail=(
                "Public checkpoint folder is readable."
                if accessible
                else "External asset page requires additional access approval."
            ),
        )


class StaticDatasetAccessProbe:
    """确定性模拟 FGI 两个数据入口的不同访问条件。"""

    def probe(self, url: str) -> DatasetAccessProbeResult:
        state = "account_required" if "kaggle.com" in url else "approval_required"
        detail = (
            "Kaggle account and dataset terms are required."
            if state == "account_required"
            else "The dataset instructions require an access request and approval."
        )
        return DatasetAccessProbeResult(
            source_url=url,
            final_url=url,
            state=state,
            detail=detail,
        )


class StaticPaperMetadataSearch:
    """API 测试使用的确定性公开书目候选。"""

    def search(self, _title: str) -> tuple[PaperMetadata, ...]:
        return (
            PaperMetadata(
                title="FGI paper",
                doi="10.1000/fgi-primary",
                description="A. Researcher · 2024 · Crossref DOI metadata",
            ),
            PaperMetadata(
                title="FGI paper: extended study",
                doi="10.1000/fgi-extended",
                description="B. Researcher · 2025 · Crossref DOI metadata",
            ),
        )


class StaticPaperMaterialCollector:
    """返回可定位的真实形态论文元数据材料。"""

    def collect(self, target: object) -> PaperMaterials:
        target_type = getattr(target, "target_type", "paper_title")
        return PaperMaterials(
            title="FGI paper",
            identifier=(
                "project:example.org/project"
                if target_type == "project_page"
                else "doi:10.1000/fgi-primary"
            ),
            source_url=(
                "https://example.org/project"
                if target_type == "project_page"
                else "https://doi.org/10.1000/fgi-primary"
            ),
            publisher="example.org" if target_type == "project_page" else "Test Publisher",
            abstract=("We evaluate a deepfake benchmark dataset and release pretrained weights."),
            fetched_at=datetime.now(UTC),
            material_type="Project Page" if target_type == "project_page" else "Paper",
        )


class FailingPaperMaterialCollector:
    def collect(self, target: object) -> PaperMaterials:
        raise PaperMaterialCollectionError("Crossref paper metadata request failed")


class ApiScopedDraftModel(QuestionOnlyEvidenceModel):
    """Offline provider using real acquired material and per-condition Rule admission."""

    def draft_evidence_findings(self, context):
        super().draft_evidence_findings(context)
        condition = context.condition_contexts[0]
        manual = next(
            (
                item
                for item in context.bundle.sources
                if item.source_path == ".researchops/environment-facts.json"
            ),
            None,
        )
        source = (
            manual
            if manual and condition.primary_dimension == "RD-02"
            else context.bundle.sources[0]
        )
        fact = source is manual
        quote = source.content if fact else source.content.splitlines()[0]
        return AIEvidenceFindingDraftInvocation(
            result=AIEvidenceFindingDraftResult(
                evidence_drafts=[
                    {
                        "local_evidence_id": "api-evidence",
                        "condition_refs": [condition.condition_ref],
                        "source_ref": source.source_id,
                        "source_type": "User Context" if fact else "Material",
                        "evidence_type": "Fact" if fact else "Unknown",
                        "location": f"{source.source_path}:line 1",
                        "line_start": 1,
                        "line_end": len(quote.splitlines()),
                        "material_type": source.material_type,
                        "quote": quote,
                        "claim": quote,
                        "verification_status": "Located Only",
                    }
                ],
                finding_drafts=[
                    {
                        "local_finding_id": "api-finding",
                        "operation": "create",
                        "condition": condition.condition_ref,
                        "summary": "Controlled source-bound API fixture.",
                        "finding_type": "Fact" if fact else "Unknown",
                        "primary_dimension": condition.primary_dimension,
                        "evidence_refs_local": ["api-evidence"],
                    }
                ],
                handoff={"needs_more_information": False, "ready_for_rule": True},
            ),
            trace=_trace("api-local-draft"),
        )


@pytest.fixture(autouse=True)
def use_static_repository_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    """阻止 API 测试访问真实网络。"""

    monkeypatch.setattr(
        api_main.readiness_assessment_service,
        "repository_material_collector",
        StaticRepositoryCollector(),
    )
    monkeypatch.setattr(
        api_main.readiness_assessment_service,
        "external_asset_probe",
        StaticExternalAssetProbe(),
    )
    monkeypatch.setattr(
        api_main.readiness_assessment_service,
        "data_access_service",
        DataAccessService(StaticDatasetAccessProbe()),
    )
    paper_search = StaticPaperMetadataSearch()
    monkeypatch.setattr(
        api_main.target_resolution_service,
        "paper_metadata_search",
        paper_search,
    )
    monkeypatch.setattr(
        api_main.readiness_assessment_service.target_resolution_service,
        "paper_metadata_search",
        paper_search,
    )
    monkeypatch.setattr(
        api_main.readiness_assessment_service,
        "paper_material_collector",
        StaticPaperMaterialCollector(),
    )
    monkeypatch.setattr(
        api_main,
        "readiness_workflow_service",
        ModelBackedReadinessWorkflowService(
            api_main.readiness_assessment_service,
            evidence_model=ApiScopedDraftModel(),
            research_loop=PassthroughResearchLoop(),
            feedback_model=FeedbackReassessmentStub(),
        ),
    )


def test_assessment_request_accepts_resolved_target_input() -> None:
    """Assessment 请求接受统一目标字段。"""

    request = AssessmentRequest(
        target_type="repository",
        target_entry=FGI_REPOSITORY,
    )

    assert request.target_type == "repository"
    assert request.environment_mode == "readonly"


def test_assessment_endpoint_returns_frontend_contract() -> None:
    """Assessment API 返回三维状态、Gate、Evidence 与 Next Action。"""

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "repository",
            "target_entry": FGI_REPOSITORY,
            "environment_mode": "readonly",
        },
    )

    assert response.status_code == 201
    payload = response.json()

    UUID(payload["assessment_id"])
    assert payload["status"] == "completed"
    assert payload["analysis_state"] is None
    assert payload["gate_available"] is True
    assert payload["data_mode"] == "live_repository"
    assert payload["overall_gate"] == "CONDITIONAL PROCEED"
    assert payload["trigger_refs"]
    assert [item["dimension_id"] for item in payload["dimensions"]] == ["RD-01", "RD-02", "RD-03"]
    assert {item["status"] for item in payload["dimensions"]} == {"Unknown"}
    assert payload["conflicts"] == []
    for dimension in payload["dimensions"]:
        assert dimension["findings"]
        evidence = dimension["findings"][0]["evidence"][0]
        assert evidence["source"] == "README.md"
        assert evidence["line_start"] == evidence["line_end"] == 1
        assert evidence["excerpt"] == "# FGI"
    assert payload["resource_signal"]["status"] == "Unknown"
    assert payload["resource_signal"]["items"][0]["required"] == "Not confirmed"
    assert payload["first_next_action"]["title"]
    assert payload["first_next_action"]["priority"] == 1
    assert payload["first_next_action"]["reason_refs"] == payload["trigger_refs"]
    assert any(item.startswith("resolve_target: success") for item in payload["trace_summary"])
    assert any("material_bundle" in item for item in payload["trace_summary"])
    assert any("ai_local_evidence_finding: completed" in item for item in payload["trace_summary"])
    assert any(item.startswith("validate_output: success") for item in payload["trace_summary"])


def test_evidence_conflict_is_input_agnostic_and_can_span_dimensions() -> None:
    """冲突属于证据条件，可关联任意 Readiness Dimension。"""

    source_a = Evidence(
        evidence_type="Fact",
        verification_status="Located Only",
        source_type="Material",
        material_type="README",
        summary="README requires Python 3.10.",
        source="README.md",
        location="Requirements",
        excerpt="Python 3.10 is required.",
    )
    source_b = Evidence(
        evidence_type="Fact",
        verification_status="Located Only",
        source_type="Material",
        material_type="Config",
        summary="The environment file pins Python 3.11.",
        source="environment.yml",
        location="dependencies",
        excerpt="python=3.11",
    )

    conflict = EvidenceConflict(
        conflict_id="conflict-python-version",
        condition_key="runtime.python.version",
        dimension_ids=["RD-01", "RD-03"],
        summary="Two materials specify incompatible Python versions.",
        gate_critical=True,
        sources=[source_a, source_b],
    )

    assert conflict.dimension_ids == ["RD-01", "RD-03"]
    assert conflict.gate_critical is True
    assert len(conflict.sources) == 2


def test_repository_statuses_follow_frozen_readiness_rules() -> None:
    """无环境事实时 RD-02 为 Unknown；外部权重不可访问时 RD-03 也为 Unknown。"""

    service = ReadinessAssessmentService(
        repository_material_collector=StaticRepositoryCollector(),
        external_asset_probe=InaccessibleExternalAssetProbe(),
        data_access_service=DataAccessService(StaticDatasetAccessProbe()),
    )
    assessment = service.create_assessment(
        AssessmentRequest(target_type="repository", target_entry=FGI_REPOSITORY)
    )

    assert assessment.dimensions[1].status == "Unknown"
    assert assessment.dimensions[2].status == "Unknown"
    assert assessment.dimensions[1].findings[0].gate_critical is True
    assert assessment.dimensions[2].findings[0].gate_critical is True
    assert assessment.dimensions[2].findings[0].evidence[0].verification_status == "Unverifiable"


def test_conflicting_dependency_materials_are_preserved_for_rd02() -> None:
    """多个依赖文件给出不同版本时，RD-02 保留双方证据并保持 Unknown。"""

    class ConflictingDependencyCollector(StaticRepositoryCollector):
        def collect(self, target: object) -> RepositoryMaterials:
            materials = super().collect(target)
            conflicting = RepositoryTextFile(
                path="environment.yml",
                text="python=3.11\ntorch=1.12.1+cu116\ncudatoolkit=11.6\n",
                html_url=f"{FGI_REPOSITORY}/blob/master/environment.yml",
                size=52,
            )
            return replace(
                materials,
                dependency_files=(*materials.dependency_files, conflicting),
            )

    service = ReadinessAssessmentService(
        repository_material_collector=ConflictingDependencyCollector(),
        external_asset_probe=StaticExternalAssetProbe(),
        data_access_service=DataAccessService(StaticDatasetAccessProbe()),
    )
    assessment = service.create_assessment(
        AssessmentRequest(target_type="repository", target_entry=FGI_REPOSITORY)
    )

    python_conflicts = [
        conflict
        for conflict in assessment.conflicts
        if conflict.condition_key == "runtime.python.version"
    ]
    rd02 = assessment.dimensions[1]

    assert rd02.status == "Unknown"
    assert rd02.findings[0].gate_critical is True
    assert len(python_conflicts) == 1
    assert python_conflicts[0].dimension_ids == ["RD-02"]
    assert python_conflicts[0].gate_critical is True
    assert [source.source for source in python_conflicts[0].sources] == [
        "package-list.txt",
        "environment.yml",
    ]
    assert {evidence.source for evidence in rd02.findings[0].evidence} >= {
        "package-list.txt",
        "environment.yml",
    }


def test_all_checkpoint_references_are_probed_and_preserved_for_rd03() -> None:
    """首个入口不可访问时，后续可访问入口仍能支持 RD-03 Ready。"""

    class MultipleCheckpointCollector(StaticRepositoryCollector):
        def collect(self, target: object) -> RepositoryMaterials:
            materials = super().collect(target)
            first = materials.external_asset_references[0]
            public = ExternalAssetReference(
                url="https://drive.google.com/drive/folders/checkpoint-public",
                source_path="README.md",
                line_number=5,
                excerpt="Backup checkpoint: public Drive folder",
            )
            return replace(
                materials,
                external_asset_references=(first, public),
            )

    service = ReadinessAssessmentService(
        repository_material_collector=MultipleCheckpointCollector(),
        external_asset_probe=SelectiveExternalAssetProbe(),
        data_access_service=DataAccessService(StaticDatasetAccessProbe()),
    )
    assessment = service.create_assessment(
        AssessmentRequest(target_type="repository", target_entry=FGI_REPOSITORY)
    )
    rd03 = assessment.dimensions[2]

    assert rd03.status == "Ready"
    assert rd03.findings[0].gate_critical is False
    assert len(rd03.findings[0].evidence) == 2
    assert [evidence.verification_status for evidence in rd03.findings[0].evidence] == [
        "Unverifiable",
        "Corroborated",
    ]
    assert str(rd03.findings[0].evidence[1].source_url).endswith("checkpoint-public")


def test_manual_environment_input_can_support_rd02_ready() -> None:
    """现有 Manual Input 字段通过 API 接入后可与项目依赖形成正向比较。"""

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "repository",
            "target_entry": FGI_REPOSITORY,
            "environment_mode": "manual",
            "environment_input": (
                "OS: Ubuntu 18.04\nPython: 3.7.12\nPyTorch: 1.12.1+cu116\nCUDA: 11.6\n"
            ),
        },
    )

    assert response.status_code == 201
    rd02 = response.json()["dimensions"][1]
    assert rd02["status"] == "Ready"
    assert rd02["findings"][0]["finding_type"] == "Fact"
    assert rd02["findings"][0]["evidence"][0]["source"] == "Current environment facts"
    assert any(
        source.access_scope == "user_provided" and '"source_mode": "manual"' in source.content
        for item in api_main.readiness_workflow_service.evidence_model.local_inputs
        for source in item.bundle.sources
    )


def test_confirmed_resource_shortfall_triggers_pause() -> None:
    """明确项目最低要求与当前资源短缺可以通过附加 Signal 触发 PAUSE。"""

    class ResourceBlockingCollector(StaticRepositoryCollector):
        def collect(self, target: object) -> RepositoryMaterials:
            materials = super().collect(target)
            assert materials.readme is not None
            text = materials.readme.text + "Requires at least 12 GB VRAM and 500 GB disk.\n"
            return replace(
                materials,
                readme=replace(materials.readme, text=text, size=len(text.encode())),
            )

    service = ReadinessAssessmentService(
        repository_material_collector=ResourceBlockingCollector(),
        external_asset_probe=StaticExternalAssetProbe(),
        data_access_service=DataAccessService(StaticDatasetAccessProbe()),
    )
    assessment = service.create_assessment(
        AssessmentRequest(
            target_type="repository",
            target_entry=FGI_REPOSITORY,
            environment_mode="manual",
            environment_input=(
                "Python: 3.7.12\nPyTorch: 1.12.1+cu116\nCUDA: 11.6\n"
                "GPU: Example GPU\nVRAM: 8 GB\nAvailable disk: 300 GB\n"
            ),
        )
    )

    assert assessment.resource_signal is not None
    assert assessment.resource_signal.status == "Blocked"
    assert assessment.overall_gate == "PAUSE"
    assert assessment.first_next_action.action_type == "Resolve Blocker"


def test_assessment_endpoint_rejects_unresolved_repository() -> None:
    """Assessment API 不为未解析 Repository 生成结论。"""

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "repository",
            "target_entry": "https://example.com/owner/repository",
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "TARGET_NOT_RESOLVED"


def test_assessment_endpoint_returns_safe_error_for_unexpected_failure(monkeypatch) -> None:
    """未预期异常不泄漏内部细节，并保持统一错误契约。"""

    def fail_assessment(_request: object) -> None:
        raise RuntimeError("sensitive internal failure detail")

    monkeypatch.setattr(
        api_main.readiness_workflow_service,
        "create_assessment",
        fail_assessment,
    )
    response = client.post(
        "/api/v1/assessments",
        json={"target_type": "doi", "target_entry": "10.1000/example"},
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "READINESS_EXECUTION_FAILED"
    assert "sensitive" not in response.text


def test_readonly_environment_rejects_forged_authorization_token() -> None:
    """客户端布尔值和伪造 token 不得触发本机读取。"""

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "repository",
            "target_entry": FGI_REPOSITORY,
            "environment_mode": "readonly",
            "environment_authorized": True,
            "environment_authorization_token": "x" * 32,
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "ENVIRONMENT_AUTHORIZATION_INVALID"


def test_readonly_environment_accepts_short_lived_server_grant() -> None:
    """授权按钮对应的服务端令牌允许执行一次只读 Assessment。"""

    grant_response = client.post("/api/v1/environment-authorizations")
    grant = grant_response.json()
    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "repository",
            "target_entry": FGI_REPOSITORY,
            "environment_mode": "readonly",
            "environment_authorized": True,
            "environment_authorization_token": grant["authorization_token"],
        },
    )

    assert grant_response.status_code == 200
    assert grant["access_mode"] == "read-only"
    assert response.status_code == 201


@pytest.mark.parametrize(
    ("target_type", "target_entry", "canonical_id"),
    [
        ("repository", FGI_REPOSITORY, "github:aseuteurideu/FGI"),
        ("project_page", "https://example.org/fgi", "project:example.org/fgi"),
        ("doi", "https://doi.org/10.1000/example", "doi:10.1000/example"),
        ("arxiv", "https://arxiv.org/abs/2401.12345", "arxiv:2401.12345"),
    ],
)
def test_target_resolution_endpoint_identifies_deterministic_inputs(
    target_type: str,
    target_entry: str,
    canonical_id: str,
) -> None:
    """URL 和标准标识符可以在不访问网络时完成规范化。"""

    response = client.post(
        "/api/v1/targets/resolve",
        json={"target_type": target_type, "target_entry": target_entry},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "identified"
    assert payload["data_mode"] == "deterministic"
    assert payload["resolved_target"]["canonical_id"] == canonical_id
    assert payload["candidates"] == []


def test_paper_title_resolution_requests_candidate_confirmation() -> None:
    """论文标题进入候选确认，不被解释为 Evidence 冲突。"""

    response = client.post(
        "/api/v1/targets/resolve",
        json={
            "target_type": "paper_title",
            "target_entry": "Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "requires_confirmation"
    assert payload["data_mode"] == "live_metadata"
    assert len(payload["candidates"]) == 2
    assert payload["resolved_target"] is None


def test_paper_title_assessment_requires_candidate_confirmation() -> None:
    """直接调用 Assessment 不能绕过论文候选确认。"""

    response = client.post(
        "/api/v1/assessments",
        json={"target_type": "paper_title", "target_entry": "FGI paper"},
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "TARGET_NOT_RESOLVED"


def test_assessment_rejects_forged_resolved_target() -> None:
    """客户端不能把另一个同类型目标伪装成当前已确认对象。"""

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "doi",
            "target_entry": "10.1000/expected",
            "resolved_target": {
                "target_type": "doi",
                "source_entry": "10.1000/expected",
                "display_name": "10.9999/forged",
                "canonical_id": "doi:10.9999/forged",
                "canonical_url": "https://doi.org/10.9999/forged",
                "resolution_method": "normalized_identifier",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "TARGET_NOT_RESOLVED"


def test_project_page_creates_live_metadata_assessment() -> None:
    """Project Page 公开材料可以进入保守的三维 Assessment。"""

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "project_page",
            "target_entry": "https://example.org/project",
            "environment_mode": "later",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["data_mode"] == "live_metadata"
    assert payload["analysis_state"] is None
    assert payload["gate_available"] is True
    assert payload["overall_gate"] == "CONDITIONAL PROCEED"
    assert payload["conflicts"] == []
    assert {item["status"] for item in payload["dimensions"]} == {"Unknown"}
    assert payload["dimensions"][0]["findings"][0]["evidence"][0]["material_type"] == (
        "Project Page"
    )
    assert "conflict" not in payload["main_risk"].lower()


def test_project_page_linked_repository_enters_repository_analysis() -> None:
    class LinkedProjectCollector:
        def collect(self, _target: object) -> PaperMaterials:
            return PaperMaterials(
                title="FGI Project",
                identifier="project:example.org/fgi",
                source_url="https://example.org/fgi",
                publisher="example.org",
                abstract="Code and project materials. threshold=0.5",
                fetched_at=datetime.now(UTC),
                material_type="Project Page",
                repository_urls=(FGI_REPOSITORY,),
            )

    class RecordingRepositoryCollector(StaticRepositoryCollector):
        def __init__(self) -> None:
            self.target_types: list[str] = []

        def collect(self, target: object) -> RepositoryMaterials:
            self.target_types.append(str(getattr(target, "target_type", "")))
            materials = super().collect(target)
            code_setting = RepositoryTextFile(
                path="evaluate.py",
                text="threshold=0.7\n",
                html_url=f"{FGI_REPOSITORY}/blob/master/evaluate.py",
                size=14,
            )
            return replace(
                materials,
                evaluation_files=(*materials.evaluation_files, code_setting),
            )

    repository_collector = RecordingRepositoryCollector()
    service = ReadinessAssessmentService(
        paper_material_collector=LinkedProjectCollector(),
        repository_material_collector=repository_collector,
        external_asset_probe=StaticExternalAssetProbe(),
        data_access_service=DataAccessService(StaticDatasetAccessProbe()),
    )
    assessment = service.create_assessment(
        AssessmentRequest(
            target_type="project_page",
            target_entry="https://example.org/fgi",
            environment_mode="later",
        )
    )

    assert repository_collector.target_types == ["repository"]
    assert assessment.target_type == "project_page"
    assert assessment.resolved_target.target_type == "project_page"
    assert assessment.data_mode == "live_repository"
    assert all(
        any(evidence.material_type == "Project Page" for evidence in finding.evidence)
        for dimension in assessment.dimensions
        for finding in dimension.findings
    )
    assert any(
        item.startswith("Discovered linked public Repository") for item in assessment.trace_summary
    )
    assert any(
        conflict.condition_key == "evaluation.setting.threshold"
        for conflict in assessment.conflicts
    )


def test_confirmed_paper_candidate_creates_live_metadata_assessment() -> None:
    """用户确认候选后，论文标题进入真实元数据 Assessment 主链。"""

    resolution = client.post(
        "/api/v1/targets/resolve",
        json={"target_type": "paper_title", "target_entry": "FGI paper"},
    ).json()
    selected = resolution["candidates"][0]["resolved_target"]

    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "paper_title",
            "target_entry": "FGI paper",
            "resolved_target": selected,
            "environment_mode": "later",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["data_mode"] == "live_metadata"
    assert payload["overall_gate"] == "CONDITIONAL PROCEED"
    assert {dimension["status"] for dimension in payload["dimensions"]} == {"Unknown"}
    assert payload["dimensions"][0]["findings"][0]["evidence"][0]["material_type"] == ("Paper")


def test_arxiv_target_creates_live_metadata_assessment() -> None:
    response = client.post(
        "/api/v1/assessments",
        json={
            "target_type": "arxiv",
            "target_entry": "2401.01234",
            "environment_mode": "later",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["data_mode"] == "live_metadata"
    assert payload["overall_gate"] == "CONDITIONAL PROCEED"


def test_doi_metadata_acquisition_failure_remains_partial() -> None:
    """DOI 已识别但元数据获取失败时不伪造业务状态或 Gate。"""

    service = ReadinessAssessmentService(paper_material_collector=FailingPaperMaterialCollector())
    assessment = service.create_assessment(
        AssessmentRequest(target_type="doi", target_entry="10.1000/fgi-primary")
    )

    assert assessment.status == "partial"
    assert assessment.analysis_state == "acquisition_failure"
    assert assessment.gate_available is False
    assert assessment.overall_gate is None
    assert {dimension.status for dimension in assessment.dimensions} == {None}
    assert {dimension.analysis_state for dimension in assessment.dimensions} == {
        "acquisition_failure"
    }


def test_mvp_frontend_is_served_by_fastapi() -> None:
    """V3.6 visual structure and production API wiring are served together."""

    page = client.get("/mvp/")
    script = client.get("/mvp/mvp-api.js")

    assert page.status_code == 200
    baseline_path = (
        Path(__file__).resolve().parents[2]
        / "06_Product_Versions"
        / "20260809_Sprint2"
        / "03_Figma"
        / "ResearchOps_FROZEN_HTML_V3.6_REVISION.html"
    )
    baseline_lines = baseline_path.read_text(encoding="utf-8").splitlines()
    baseline = "\n".join(baseline_lines)
    assert "conditionalEvidenceData" in baseline
    assert "conditionalEvidenceData" not in page.text
    assert "evidenceDataByScenario" not in page.text
    assert "Readiness Overview" in page.text
    assert '<script src="mvp-api.js?v=' in page.text
    assert '<script src="ui.js' in page.text
    assert '<script src="access.js' in page.text
    assert "<script>" not in page.text
    assert client.get("/mvp/styles.css").status_code == 200
    assert script.status_code == 200
    assert "/api/v1/targets/resolve" in script.text
    assert "/api/v1/assessments" in script.text
    assert "conflict.condition_key.startsWith('evaluation.')" in script.text
    assert "evaluationEvidenceLink.addEventListener" in script.text
    assert "dimensionConflictsByScenario" not in script.text
    assert "dimensionEvidenceByScenario" in script.text
    assert "dimensionEvidenceByScenario[scenario][target.key] = inspectableEvidence" in script.text
    assert "(finding.evidence || []).filter(hasInspectableEvidence)" in script.text
    assert "dimension.findings.flatMap" not in script.text
    assert "openApiDimensionEvidence" in script.text
    assert "relatedNextActionFor(dimension, finding)" in script.text
    assert "nextAction: relatedNextAction.title" in script.text
    assert "nextAction: assessment.first_next_action.title" not in script.text
    assert "document.getElementById('dimension-view-evidence')" in script.text
    assert "environment_authorized" in script.text
    assert "/api/v1/environment-authorizations" in script.text
    assert "environment_authorization_token" in script.text
    assert "environment_input" in script.text
    assert "readEnvironmentInput" in script.text
    assert "applyResourceSignal(assessment.resource_signal)" in script.text
    assert "assessment.overall_gate === 'PAUSE'" not in script.text
    assert "assessment.overall_gate === 'PROCEED'" not in script.text
    assert "applyCompletedAssessment(assessment)" in script.text
    assert "applyPartialResult(assessment)" in script.text
    assert "applyGateUnavailableAssessment(assessment)" in script.text
    assert "applyAcquisitionFailure(assessment)" in script.text
    assert "None detected" not in script.text
    assert "No conflict details" not in script.text
    assert "API contract · waiting" not in page.text
    assert "conflictCard.style.display = 'none'" not in script.text
    assert "supports GitHub Repository input only" not in script.text
