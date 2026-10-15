"""Sprint 3 首个 Readiness Assessment 竖切服务。"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from researchops.schemas import (
    AnalysisState,
    AssessmentRequest,
    Evidence,
    EvidenceConflict,
    Finding,
    NextAction,
    ReadinessAssessment,
    ReadinessDimension,
    ResolvedTarget,
    TargetResolutionRequest,
)
from researchops.services.data_access import DataAccessService
from researchops.services.environment_facts import (
    EnvironmentComparison,
    EnvironmentFacts,
    EnvironmentFactService,
    ProjectEnvironmentRequirements,
)
from researchops.services.evaluation_conflicts import EvaluationConflictService
from researchops.services.external_assets import (
    ExternalAssetProbe,
    ExternalAssetProbeResult,
    PublicExternalAssetProbe,
)
from researchops.services.gate_decision import GateDecisionService
from researchops.services.paper_materials import (
    PaperMaterialCollectionError,
    PaperMaterialCollector,
    PaperMaterials,
    PublicPaperMaterialCollector,
)
from researchops.services.repository_materials import (
    ExternalAssetReference,
    GitHubRepositoryMaterialCollector,
    RepositoryCollectionError,
    RepositoryMaterialCollector,
    RepositoryMaterials,
    RepositoryTextFile,
)
from researchops.services.resource_signals import ResourceSignalService
from researchops.services.target_resolution import TargetResolutionService


class TargetResolutionError(ValueError):
    """Assessment 请求缺少可用的规范化目标。"""


class ReadinessAssessmentService:
    """将目标解析、受限材料采集与 Readiness 契约组合起来。"""

    def __init__(
        self,
        target_resolution_service: TargetResolutionService | None = None,
        repository_material_collector: RepositoryMaterialCollector | None = None,
        external_asset_probe: ExternalAssetProbe | None = None,
        environment_fact_service: EnvironmentFactService | None = None,
        resource_signal_service: ResourceSignalService | None = None,
        gate_decision_service: GateDecisionService | None = None,
        evaluation_conflict_service: EvaluationConflictService | None = None,
        data_access_service: DataAccessService | None = None,
        paper_material_collector: PaperMaterialCollector | None = None,
    ) -> None:
        self.target_resolution_service = target_resolution_service or TargetResolutionService()
        self.repository_material_collector = (
            repository_material_collector or GitHubRepositoryMaterialCollector()
        )
        self.external_asset_probe = external_asset_probe or PublicExternalAssetProbe()
        self.environment_fact_service = environment_fact_service or EnvironmentFactService()
        self.resource_signal_service = resource_signal_service or ResourceSignalService()
        self.gate_decision_service = gate_decision_service or GateDecisionService()
        self.evaluation_conflict_service = (
            evaluation_conflict_service or EvaluationConflictService()
        )
        self.data_access_service = data_access_service or DataAccessService()
        self.paper_material_collector = paper_material_collector or PublicPaperMaterialCollector()

    def create_assessment(self, request: AssessmentRequest) -> ReadinessAssessment:
        """顺序执行一次 Assessment；主要供图外调用与向后兼容使用。"""

        resolved_target = self.resolve_target(request)
        if request.target_type != "repository":
            return self.create_from_context(request, resolved_target)

        try:
            materials = self.collect_repository_materials(resolved_target)
        except RepositoryCollectionError as exc:
            return self.create_from_context(
                request,
                resolved_target,
                collection_error=str(exc),
            )

        return self.create_from_context(request, resolved_target, materials=materials)

    def resolve_target(self, request: AssessmentRequest) -> ResolvedTarget:
        """解析并校验 Assessment 目标，供 LangGraph 的独立节点复用。"""

        resolution = self.target_resolution_service.resolve(
            TargetResolutionRequest(
                target_type=request.target_type,
                target_entry=request.target_entry,
            )
        )
        resolved_target = request.resolved_target
        if resolved_target is not None:
            if resolved_target.target_type != request.target_type:
                raise TargetResolutionError("resolved_target 与 target_type 不一致。")
            if resolved_target.source_entry.strip() != request.target_entry.strip():
                raise TargetResolutionError("resolved_target 与当前 target_entry 不一致。")

            allowed_targets = [
                target
                for target in (
                    resolution.resolved_target,
                    *(candidate.resolved_target for candidate in resolution.candidates),
                )
                if target is not None
            ]
            if not any(
                target.canonical_id == resolved_target.canonical_id
                and target.canonical_url == resolved_target.canonical_url
                and target.resolution_method == resolved_target.resolution_method
                for target in allowed_targets
            ):
                raise TargetResolutionError("resolved_target 不是当前解析结果中的可信目标。")
        else:
            resolved_target = resolution.resolved_target

        if resolved_target is None:
            raise TargetResolutionError("目标尚未完成解析或候选确认，无法创建 Assessment。")

        return resolved_target

    def collect_repository_materials(
        self,
        resolved_target: ResolvedTarget,
    ) -> RepositoryMaterials:
        """只读采集 Repository 材料，供工作流采集节点调用。"""

        return self.repository_material_collector.collect(resolved_target)

    def create_from_context(
        self,
        request: AssessmentRequest,
        resolved_target: ResolvedTarget,
        *,
        materials: RepositoryMaterials | None = None,
        collection_error: str | None = None,
    ) -> ReadinessAssessment:
        """根据工作流已取得的上下文生成最终或 Partial Assessment。"""

        if request.target_type in {"paper_title", "doi", "arxiv", "project_page"}:
            try:
                paper_materials = self.paper_material_collector.collect(resolved_target)
            except PaperMaterialCollectionError as exc:
                return self._create_paper_collection_failure(
                    request,
                    resolved_target,
                    str(exc),
                )
            linked_repository = self._collect_linked_repository(paper_materials)
            if linked_repository is not None:
                repository_url, repository_materials = linked_repository
                repository_materials = self._merge_target_material(
                    repository_materials,
                    paper_materials,
                )
                assessment = self._create_repository_assessment(
                    request,
                    resolved_target,
                    repository_materials,
                )
                dimensions = [
                    dimension.model_copy(
                        update={
                            "findings": [
                                finding.model_copy(
                                    update={
                                        "evidence": [
                                            *finding.evidence,
                                            self._target_material_evidence(
                                                paper_materials,
                                                dimension.dimension_id,
                                            ),
                                        ]
                                    }
                                )
                                for finding in dimension.findings
                            ]
                        }
                    )
                    for dimension in assessment.dimensions
                ]
                return assessment.model_copy(
                    update={
                        "dimensions": dimensions,
                        "trace_summary": [
                            f"Discovered linked public Repository: {repository_url}",
                            *assessment.trace_summary,
                        ],
                    }
                )
            return self._create_paper_assessment(request, resolved_target, paper_materials)
        if request.target_type != "repository":
            return self._create_partial_assessment(request, resolved_target)

        if collection_error is not None:
            return self._create_repository_collection_failure(
                request,
                resolved_target,
                collection_error,
            )

        if materials is None:
            raise ValueError("Repository Assessment 缺少采集材料。")

        return self._create_repository_assessment(request, resolved_target, materials)

    def _collect_linked_repository(
        self,
        materials: PaperMaterials,
    ) -> tuple[str, RepositoryMaterials] | None:
        """只采集公开材料中明确链接且能再次规范化的首个 GitHub Repository。"""

        for repository_url in materials.repository_urls:
            resolution = self.target_resolution_service.resolve(
                TargetResolutionRequest(
                    target_type="repository",
                    target_entry=repository_url,
                )
            )
            repository_target = resolution.resolved_target
            if repository_target is None:
                continue
            try:
                return (
                    repository_url,
                    self.repository_material_collector.collect(repository_target),
                )
            except RepositoryCollectionError:
                continue
        return None

    @staticmethod
    def _merge_target_material(
        repository_materials: RepositoryMaterials,
        target_materials: PaperMaterials,
    ) -> RepositoryMaterials:
        """让 Paper/Project Page 文本参与后续 Paper-Code setting 比较。"""

        text = f"{target_materials.title}\n{target_materials.abstract or ''}"
        material = RepositoryTextFile(
            path=f"{target_materials.material_type} abstract",
            text=text,
            html_url=target_materials.source_url,
            size=len(text.encode("utf-8")),
        )
        return replace(
            repository_materials,
            evaluation_files=(material, *repository_materials.evaluation_files),
        )

    @staticmethod
    def _target_material_evidence(
        materials: PaperMaterials,
        dimension_id: str,
    ) -> Evidence:
        condition_labels = {
            "RD-01": "data and access",
            "RD-02": "environment and dependencies",
            "RD-03": "weights and configuration",
        }
        label = condition_labels.get(dimension_id, "reproduction")
        return Evidence(
            evidence_type="Fact",
            verification_status="Located Only",
            source_type="Material",
            material_type=materials.material_type,
            summary=f"Original target material retained for {label} comparison.",
            source=f"{materials.publisher} public material",
            location="Bounded public text",
            excerpt=(materials.abstract or materials.title)[:2000],
            source_url=materials.source_url,
        )

    def _create_paper_assessment(
        self,
        request: AssessmentRequest,
        resolved_target: ResolvedTarget,
        materials: PaperMaterials,
    ) -> ReadinessAssessment:
        """从真实论文题录/摘要形成保守的三维 Unknown，而不把缺失内容猜成 Ready。"""

        content = f"{materials.title}\n{materials.abstract or ''}".casefold()
        material_label = materials.material_type
        definitions = (
            (
                "RD-01",
                "Data & Access Readiness",
                "Dataset entry, access, split, and input requirements",
                ("dataset", "data set", "corpus", "benchmark"),
            ),
            (
                "RD-02",
                "Environment & Dependency Readiness",
                "Python, framework, CUDA, and dependency requirements",
                ("python", "pytorch", "tensorflow", "cuda", "dependency"),
            ),
            (
                "RD-03",
                "Weights & Configuration Readiness",
                "Checkpoint, pretrained weight, and configuration requirements",
                ("checkpoint", "pretrained", "weight", "configuration", "config"),
            ),
        )
        dimensions: list[ReadinessDimension] = []
        for dimension_id, name, condition, terms in definitions:
            mentioned = any(term in content for term in terms)
            material_scope = "title and abstract" if materials.abstract else "bibliographic title"
            evidence = Evidence(
                evidence_type="Fact" if mentioned else "Unknown",
                verification_status="Located Only",
                source_type="Material",
                material_type=materials.material_type,
                summary=(
                    f"The public {material_scope} mentions this condition, but does not establish "
                    "the complete operational requirement."
                    if mentioned
                    else f"No explicit details for this condition were located in the public "
                    f"{material_scope}."
                ),
                source=f"{materials.publisher} public material",
                location="Abstract" if materials.abstract else "Bibliographic title",
                excerpt=(materials.abstract or materials.title)[:2000],
                source_url=materials.source_url,
            )
            dimensions.append(
                ReadinessDimension(
                    dimension_id=dimension_id,
                    name=name,
                    status="Unknown",
                    summary=(
                        f"The available {material_label} material does not yet establish "
                        f"{condition.lower()}."
                    ),
                    gate_impact="Leaves this gate-critical reproduction condition Unknown.",
                    findings=[
                        Finding(
                            finding_id=f"{dimension_id}-F01",
                            condition=condition,
                            title=f"{condition} remain incomplete",
                            summary=(
                                f"The bounded public {material_label} material was inspected, but "
                                "additional "
                                "Paper, Repository, Supplementary, or project material is required."
                            ),
                            finding_type="Unknown",
                            gate_critical=True,
                            readiness_impact="Gate-critical Unknown",
                            evidence=[evidence],
                        )
                    ],
                )
            )

        gate_decision = self.gate_decision_service.resolve(dimensions, None, None)
        return ReadinessAssessment(
            assessment_id=uuid4(),
            status="completed",
            data_mode="live_metadata",
            target_type=request.target_type,
            target_entry=request.target_entry,
            resolved_target=resolved_target,
            generated_at=datetime.now(UTC),
            dimensions=dimensions,
            gate_available=True,
            overall_gate=gate_decision.overall_gate,
            trigger_refs=list(gate_decision.trigger_refs),
            main_risk=gate_decision.main_risk,
            first_next_action=gate_decision.first_next_action,
            conflicts=[],
            trace_summary=[
                f"Collected public {material_label} material for '{materials.identifier}'.",
                f"Read bounded public text: {'yes' if materials.abstract else 'no'}.",
                "Withheld Ready/Warning/Blocked claims that require full Paper or project materials.",
                f"Resolved Overall Gate: {gate_decision.overall_gate} from "
                f"{len(gate_decision.trigger_refs)} trigger reference(s).",
            ],
        )

    def _create_paper_collection_failure(
        self,
        request: AssessmentRequest,
        resolved_target: ResolvedTarget,
        reason: str,
    ) -> ReadinessAssessment:
        assessment = self._create_partial_assessment(
            request,
            resolved_target,
            dimension_analysis_state="acquisition_failure",
        )
        material_label = "Project Page" if request.target_type == "project_page" else "Paper"
        return assessment.model_copy(
            update={
                "data_mode": "live_metadata",
                "analysis_state": "acquisition_failure",
                "main_risk": (
                    f"The {material_label} target was identified, but its public material could "
                    "not be "
                    "collected, so an Overall Gate is not available."
                ),
                "first_next_action": NextAction(
                    action_id="action-retry-paper-metadata-acquisition",
                    title=f"Retry public {material_label} material collection",
                    description=reason[:1000],
                    action_type="Minimum Validation",
                    reason_refs=["paper_metadata_acquisition"],
                ),
                "trace_summary": [
                    f"Validated the {material_label} target identity.",
                    f"{material_label} material collection stopped: {reason[:500]}",
                    f"Withheld Overall Gate because {material_label} acquisition failed.",
                ],
            }
        )

    def _create_repository_assessment(
        self,
        request: AssessmentRequest,
        resolved_target: ResolvedTarget,
        materials: RepositoryMaterials,
    ) -> ReadinessAssessment:
        readme = materials.readme
        weight_match = self._find_line(
            readme,
            ("weight", "checkpoint", "model_best", "pretrained", "--test"),
        )
        configuration_match = self._find_line(
            readme,
            ("--test", "model_best_epoch", "change the path of model file"),
        )
        dependency_file = materials.dependency_files[0] if materials.dependency_files else None
        external_asset_results = [
            (reference, self.external_asset_probe.probe(reference.url))
            for reference in materials.external_asset_references
        ]
        weight_path = next(
            (
                path
                for path in materials.relevant_paths
                if "weight" in path.casefold() or "checkpoint" in path.casefold()
            ),
            None,
        )

        data_access = self.data_access_service.evaluate(materials)
        requirements, environment_conflicts = self._environment_requirements(materials)
        environment_facts = self.environment_fact_service.acquire(
            request.environment_mode,
            authorized=request.environment_authorized,
            supplied_text=request.environment_input,
        )
        environment_comparison = (
            EnvironmentComparison(
                status="Unknown",
                summary="Collected dependency files specify conflicting environment requirements.",
                finding_title="Environment requirements conflict across dependency materials",
                finding_summary=" ".join(conflict.summary for conflict in environment_conflicts)[
                    :2000
                ],
                finding_type="Unknown",
                readiness_impact="Gate-critical Unknown",
                excerpt=" | ".join(
                    evidence.excerpt
                    for conflict in environment_conflicts
                    for evidence in conflict.sources
                )[:2000],
            )
            if environment_conflicts
            else self.environment_fact_service.compare(requirements, environment_facts)
        )
        resource_signal = self.resource_signal_service.create(
            readme,
            environment_facts,
            repository_url=materials.repository_url,
        )
        evaluation_signal, evaluation_conflicts = self.evaluation_conflict_service.create(materials)
        conflicts = [*environment_conflicts, *evaluation_conflicts]
        dependency_evidence = self._environment_evidence(
            materials,
            dependency_file,
            environment_facts,
            environment_comparison,
        )
        weight_evidence = (
            [
                self._weight_evidence(
                    materials,
                    weight_match=weight_match,
                    weight_path=weight_path,
                    configuration_match=configuration_match,
                    external_asset_reference=reference,
                    external_asset_result=result,
                )
                for reference, result in external_asset_results
            ]
            if external_asset_results
            else [
                self._weight_evidence(
                    materials,
                    weight_match=weight_match,
                    weight_path=weight_path,
                    configuration_match=configuration_match,
                    external_asset_reference=None,
                    external_asset_result=None,
                )
            ]
        )

        weight_ready = bool(
            weight_match
            and configuration_match
            and any(result.accessible for _, result in external_asset_results)
        )
        asset_acquisition_failed = bool(
            external_asset_results
            and not any(result.accessible for _, result in external_asset_results)
            and any(
                result.verification_state == "acquisition_failure"
                for _, result in external_asset_results
            )
        )
        asset_verified_inaccessible = bool(
            external_asset_results
            and all(
                result.verification_state == "verified_inaccessible"
                for _, result in external_asset_results
            )
        )
        weight_status = "Ready" if weight_ready else "Unknown"

        dimensions = [
            ReadinessDimension(
                dimension_id="RD-01",
                name="Data & Access Readiness",
                status=data_access.status,
                summary=data_access.summary,
                gate_impact=data_access.gate_impact,
                findings=[
                    Finding(
                        finding_id="RD-01-F01",
                        condition="Dataset entry and access conditions",
                        title=data_access.finding_title,
                        summary=data_access.finding_summary,
                        finding_type=data_access.finding_type,
                        gate_critical=data_access.status != "Ready",
                        readiness_impact=data_access.readiness_impact,
                        evidence=list(data_access.evidence),
                    )
                ],
            ),
            ReadinessDimension(
                dimension_id="RD-02",
                name="Environment & Dependency Readiness",
                status=environment_comparison.status,
                summary=environment_comparison.summary,
                gate_impact=(
                    "No current blocker from environment or dependency readiness."
                    if environment_comparison.status == "Ready"
                    else "Adds a non-blocking compatibility risk to the current decision."
                    if environment_comparison.status == "Warning"
                    else "Leaves environment compatibility Unknown."
                ),
                findings=[
                    Finding(
                        finding_id="RD-02-F01",
                        condition="Environment compatibility",
                        title=environment_comparison.finding_title,
                        summary=environment_comparison.finding_summary,
                        finding_type=environment_comparison.finding_type,
                        gate_critical=environment_comparison.status == "Unknown",
                        readiness_impact=environment_comparison.readiness_impact,
                        evidence=(
                            [
                                evidence
                                for conflict in environment_conflicts
                                for evidence in conflict.sources
                            ]
                            if environment_conflicts
                            else [dependency_evidence]
                        ),
                    )
                ],
            ),
            ReadinessDimension(
                dimension_id="RD-03",
                name="Weights & Configuration Readiness",
                status=weight_status,
                summary=(
                    "The required checkpoint has a publicly accessible entry and its testing "
                    "configuration relationship is sufficiently identified."
                    if weight_ready
                    else "Checkpoint accessibility verification did not complete because the "
                    "external asset request failed technically."
                    if asset_acquisition_failed
                    else "The checkpoint entry was reached, but public access was not confirmed."
                    if asset_verified_inaccessible
                    else "Checkpoint accessibility or its configuration relationship remains "
                    "insufficiently verified."
                ),
                gate_impact=(
                    "No current blocker from weights or configuration."
                    if weight_ready
                    else "Leaves weights and configuration readiness Unknown."
                ),
                findings=[
                    Finding(
                        finding_id="RD-03-F01",
                        condition="Checkpoint and configuration mapping",
                        title=(
                            "Checkpoint entry and testing configuration are sufficiently identified"
                            if weight_ready
                            else "Checkpoint accessibility verification did not complete"
                            if asset_acquisition_failed
                            else "Checkpoint entry is not confirmed as publicly accessible"
                            if asset_verified_inaccessible
                            else "Checkpoint or configuration evidence remains incomplete"
                        ),
                        summary=(
                            "The Repository links a publicly readable checkpoint location and maps "
                            "that artifact to the documented test command. Ready does not claim "
                            "that the checkpoint has been downloaded or loaded successfully."
                            if weight_ready
                            else "A technical acquisition failure prevented the public checkpoint "
                            "entry from being verified in this assessment. This does not prove "
                            "that the checkpoint is missing or access-restricted."
                            if asset_acquisition_failed
                            else "The checkpoint entry responded, but the response did not establish "
                            "anonymous public access."
                            if asset_verified_inaccessible
                            else "The bounded materials do not yet establish both a publicly "
                            "accessible checkpoint entry and its testing configuration mapping."
                        ),
                        finding_type="Fact" if weight_ready else "Unknown",
                        gate_critical=not weight_ready,
                        readiness_impact="No current blocker"
                        if weight_ready
                        else "Readiness Unknown",
                        evidence=weight_evidence,
                    )
                ],
            ),
        ]

        gate_decision = self.gate_decision_service.resolve(
            dimensions,
            resource_signal,
            evaluation_signal,
        )
        return ReadinessAssessment(
            assessment_id=uuid4(),
            status="completed",
            data_mode="live_repository",
            target_type=request.target_type,
            target_entry=request.target_entry,
            resolved_target=resolved_target,
            generated_at=datetime.now(UTC),
            dimensions=dimensions,
            gate_available=True,
            overall_gate=gate_decision.overall_gate,
            trigger_refs=list(gate_decision.trigger_refs),
            main_risk=gate_decision.main_risk,
            first_next_action=gate_decision.first_next_action,
            conflicts=conflicts,
            evaluation_signal=evaluation_signal,
            resource_signal=resource_signal,
            trace_summary=[
                f"Collected public Repository metadata from branch '{materials.default_branch}'.",
                f"Read README material: {'yes' if materials.readme else 'no'}.",
                f"Read {len(materials.dependency_files)} bounded dependency file(s).",
                f"Probed {len(materials.dataset_references)} documented dataset entry or entries.",
                "Probed public checkpoint entries without downloading model artifacts: "
                f"{sum(result.accessible for _, result in external_asset_results)} of "
                f"{len(external_asset_results)} publicly readable.",
                "Compared bounded evaluation materials: "
                f"{len(materials.evaluation_files)} file(s).",
                f"Preserved {len(conflicts)} unresolved evidence conflict(s) across all signals.",
                f"Environment acquisition mode '{request.environment_mode}': "
                f"{'facts acquired' if environment_facts is not None else 'facts unavailable'}.",
                f"Resolved Overall Gate: {gate_decision.overall_gate} from "
                f"{len(gate_decision.trigger_refs)} trigger reference(s).",
            ],
        )

    @staticmethod
    def _find_line(
        material: RepositoryTextFile | None,
        terms: tuple[str, ...],
    ) -> tuple[int, str] | None:
        if material is None:
            return None
        for line_number, line in enumerate(material.text.splitlines(), start=1):
            normalized = line.strip()
            if normalized and any(term in normalized.casefold() for term in terms):
                return line_number, normalized[:1000]
        return None

    def _environment_requirements(
        self,
        materials: RepositoryMaterials,
    ) -> tuple[ProjectEnvironmentRequirements, list[EvidenceConflict]]:
        extracted = [
            (material, self.environment_fact_service.extract_requirements(material.text))
            for material in materials.dependency_files
        ]
        values: dict[str, str | None] = {}
        conflicts: list[EvidenceConflict] = []
        for field, label in (
            ("python", "Python"),
            ("framework", "Framework"),
            ("cuda", "CUDA"),
        ):
            located = [
                (material, value)
                for material, requirements in extracted
                if (value := getattr(requirements, field)) is not None
            ]
            values[field] = located[0][1] if located else None
            for left_index, source_a in enumerate(located):
                for right_index, source_b in enumerate(
                    located[left_index + 1 :],
                    start=left_index + 1,
                ):
                    if source_a[1].casefold() == source_b[1].casefold():
                        continue
                    sources = [
                        Evidence(
                            evidence_type="Fact",
                            verification_status="Located Only",
                            source_type="Material",
                            material_type="Config",
                            summary=f"{label} requirement from {material.path}",
                            source=material.path,
                            location=material.path,
                            excerpt=value,
                            source_url=material.html_url,
                        )
                        for material, value in (source_a, source_b)
                    ]
                    conflicts.append(
                        EvidenceConflict(
                            conflict_id=(f"environment-{field}-version-{left_index}-{right_index}"),
                            condition_key=f"runtime.{field}.version",
                            dimension_ids=["RD-02"],
                            summary=(
                                f"Dependency materials specify different {label} requirements: "
                                f"'{source_a[1]}' and '{source_b[1]}'."
                            ),
                            gate_critical=True,
                            sources=sources,
                        )
                    )
        return ProjectEnvironmentRequirements(**values), conflicts

    @staticmethod
    def _readme_evidence(
        materials: RepositoryMaterials,
        match: tuple[int, str] | None,
        *,
        summary: str,
    ) -> Evidence:
        if materials.readme and match:
            line_number, excerpt = match
            return Evidence(
                evidence_type="Fact",
                verification_status="Located Only",
                source_type="Material",
                material_type="README",
                summary=summary,
                source=materials.readme.path,
                location=f"{materials.readme.path}:line {line_number}",
                excerpt=excerpt,
                source_url=materials.readme.html_url,
            )
        return Evidence(
            evidence_type="Unknown",
            verification_status="Unverifiable",
            source_type="Material",
            material_type="Repository",
            summary=summary,
            source="Bounded Repository material scan",
            location=f"branch:{materials.default_branch}",
            excerpt="No matching dataset access line was located.",
            source_url=materials.repository_url,
        )

    @staticmethod
    def _environment_evidence(
        materials: RepositoryMaterials,
        dependency_file: RepositoryTextFile | None,
        environment_facts: EnvironmentFacts | None,
        comparison: EnvironmentComparison,
    ) -> Evidence:
        if dependency_file:
            environment_source = (
                environment_facts.source_mode.replace("_", " ")
                if environment_facts
                else "environment not acquired"
            )
            return Evidence(
                evidence_type=comparison.finding_type,
                verification_status="Corroborated" if environment_facts else "Located Only",
                source_type="User Context" if environment_facts else "Material",
                material_type=None if environment_facts else "Config",
                summary=(
                    "Project dependency requirements were compared with supplied environment "
                    f"facts. {comparison.excerpt}"
                    if environment_facts
                    else "Project requirements were located, but current environment facts are "
                    f"not sufficiently available for comparison. {comparison.excerpt}"
                )[:1000],
                source=f"{dependency_file.path} + {environment_source}",
                location=f"{dependency_file.path} + environment:{environment_source}",
                excerpt=comparison.excerpt,
                source_url=dependency_file.html_url,
            )
        return Evidence(
            evidence_type="Unknown",
            verification_status="Unverifiable",
            source_type="Material",
            material_type="Repository",
            summary="No recognized dependency specification was collected.",
            source="Repository file tree",
            location=f"branch:{materials.default_branch}",
            excerpt="No supported dependency manifest path was located.",
            source_url=materials.repository_url,
        )

    @staticmethod
    def _weight_evidence(
        materials: RepositoryMaterials,
        *,
        weight_match: tuple[int, str] | None,
        weight_path: str | None,
        configuration_match: tuple[int, str] | None,
        external_asset_reference: ExternalAssetReference | None,
        external_asset_result: ExternalAssetProbeResult | None,
    ) -> Evidence:
        if (
            external_asset_reference
            and external_asset_result
            and external_asset_result.accessible
            and configuration_match
        ):
            configuration_line, configuration_excerpt = configuration_match
            return Evidence(
                evidence_type="Fact",
                verification_status="Corroborated",
                source_type="Material",
                material_type="Checkpoint-Release",
                summary=(
                    "The public checkpoint entry is readable and Repository documentation maps "
                    "the artifact to a testing configuration."
                ),
                source=f"{external_asset_reference.source_path} + public checkpoint entry",
                location=(
                    f"{external_asset_reference.source_path}:line "
                    f"{external_asset_reference.line_number}; configuration line "
                    f"{configuration_line}"
                ),
                excerpt=(f"{external_asset_reference.excerpt} | {configuration_excerpt}")[:2000],
                source_url=external_asset_reference.url,
            )
        if external_asset_reference:
            return Evidence(
                evidence_type="Unknown",
                verification_status="Unverifiable",
                source_type="Material",
                material_type="Checkpoint-Release",
                summary=(
                    external_asset_result.detail
                    if external_asset_result
                    else "The checkpoint entry was located but not probed."
                ),
                source=external_asset_reference.source_path,
                location=(
                    f"{external_asset_reference.source_path}:line "
                    f"{external_asset_reference.line_number}"
                ),
                excerpt=external_asset_reference.excerpt,
                source_url=external_asset_reference.url,
            )
        if materials.readme and weight_match:
            line_number, excerpt = weight_match
            return Evidence(
                evidence_type="Fact",
                verification_status="Located Only",
                source_type="Material",
                material_type="README",
                summary=(
                    "Repository documentation contains a model artifact reference, but no "
                    "publicly readable asset entry was confirmed."
                ),
                source=materials.readme.path,
                location=f"{materials.readme.path}:line {line_number}",
                excerpt=excerpt,
                source_url=materials.readme.html_url,
            )
        if weight_path:
            return Evidence(
                evidence_type="Fact",
                verification_status="Located Only",
                source_type="Material",
                material_type="Repository",
                summary="A weight or checkpoint-related path was located in the Repository tree.",
                source="Repository file tree",
                location=weight_path,
                excerpt=weight_path,
                source_url=materials.repository_url,
            )
        return Evidence(
            evidence_type="Unknown",
            verification_status="Unverifiable",
            source_type="Material",
            material_type="Repository",
            summary="No model artifact reference was found in the bounded materials.",
            source="Bounded Repository material scan",
            location=f"branch:{materials.default_branch}",
            excerpt="No matching weight or checkpoint reference was located.",
            source_url=materials.repository_url,
        )

    def _create_repository_collection_failure(
        self,
        request: AssessmentRequest,
        resolved_target: ResolvedTarget,
        reason: str,
    ) -> ReadinessAssessment:
        """网络或 GitHub API 不可用时保留 Partial Result，而不回退到 Mock 结论。"""

        assessment = self._create_partial_assessment(
            request,
            resolved_target,
            dimension_analysis_state="acquisition_failure",
        )
        return assessment.model_copy(
            update={
                "data_mode": "live_repository",
                "analysis_state": "acquisition_failure",
                "main_risk": (
                    "Repository target was identified, but its public materials could not be "
                    "collected, so an Overall Gate is not available."
                ),
                "first_next_action": NextAction(
                    action_id="action-retry-repository-acquisition",
                    title="Retry public Repository material collection",
                    description=reason[:1000],
                    action_type="Minimum Validation",
                    reason_refs=["repository_material_acquisition"],
                ),
                "trace_summary": [
                    "Validated GitHub Repository input.",
                    "Attempted bounded read-only collection through the GitHub API.",
                    f"Material collection stopped: {reason[:500]}",
                    "Withheld Overall Gate because Repository evidence is incomplete.",
                ],
            }
        )

    def _create_partial_assessment(
        self,
        request: AssessmentRequest,
        resolved_target: ResolvedTarget,
        *,
        dimension_analysis_state: AnalysisState = "empty",
    ) -> ReadinessAssessment:
        """对已识别但尚未形成业务判断的目标返回 Gate 不可用结果。"""

        dimension_definitions = [
            ("RD-01", "Data & Access Readiness", "Data and access materials"),
            (
                "RD-02",
                "Environment & Dependency Readiness",
                "Environment and dependency materials",
            ),
            (
                "RD-03",
                "Weights & Configuration Readiness",
                "Weights and configuration materials",
            ),
        ]
        dimensions = [
            ReadinessDimension(
                dimension_id=dimension_id,
                name=name,
                analysis_state=dimension_analysis_state,
                summary=(
                    f"{material_name} have not been acquired for this "
                    f"{request.target_type.replace('_', ' ')} input yet."
                ),
                gate_impact="Overall Gate cannot be aggregated from incomplete findings.",
                findings=[],
            )
            for dimension_id, name, material_name in dimension_definitions
        ]

        input_label = request.target_type.replace("_", " ")
        return ReadinessAssessment(
            assessment_id=uuid4(),
            status="partial",
            data_mode=(
                "live_metadata" if request.target_type == "paper_title" else "normalized_target"
            ),
            target_type=request.target_type,
            target_entry=request.target_entry,
            resolved_target=resolved_target,
            generated_at=datetime.now(UTC),
            dimensions=dimensions,
            gate_available=False,
            overall_gate=None,
            main_risk=(
                f"The {input_label} target is identified, but its materials have not been "
                "acquired, so an Overall Gate is not available."
            ),
            first_next_action=NextAction(
                action_id="action-acquire-target-materials",
                title=f"Acquire materials for the resolved {input_label}",
                description=(
                    "Run the matching read-only material adapter before generating Evidence, "
                    "Readiness statuses, or an Overall Gate."
                ),
                action_type="Minimum Validation",
                reason_refs=["resolved_target", *[item.dimension_id for item in dimensions]],
            ),
            trace_summary=[
                f"Accepted {input_label} input.",
                "Resolved or confirmed the target identity.",
                "Left all three core Dimensions without a business status until acquisition.",
                "Withheld Overall Gate until material acquisition is complete.",
            ],
        )


# 保留旧导入名，避免现有调用方在本次竖切中被破坏。
MockReadinessAssessmentService = ReadinessAssessmentService
