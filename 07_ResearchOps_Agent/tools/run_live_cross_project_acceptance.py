"""PA-09 live-provider acceptance over three real public repositories.

This runner uses the production phased workflow. It persists only bounded
status, lineage, and Trace summaries; credentials, prompts, source text, and
raw model responses are never written to the report.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from researchops.core.config import Settings
from researchops.schemas import (
    AssessmentFeedbackRequest,
    AssessmentRequest,
    HumanSourceSubmission,
    ReadinessAssessment,
)
from researchops.services import (
    DeepSeekAnalysisModel,
    DeterministicResearchToolExecutor,
    ModelBackedReadinessWorkflowService,
    ReadinessAssessmentService,
)
from researchops.services.phased_research_loop import PhasedResearchLoopService
from researchops.services.repository_materials import (
    GitHubRepositoryMaterialCollector,
    RepositoryCollectionError,
    RepositoryMaterials,
    RepositoryTextFile,
)


@dataclass(frozen=True)
class LiveCase:
    case_id: str
    profile: str
    repository_url: str
    exercise_feedback: bool = False


CASES = (
    LiveCase("LIVE-01", "information_complete", "https://github.com/facebookresearch/detr"),
    LiveCase("LIVE-02", "material_missing", "https://github.com/karpathy/minGPT"),
    LiveCase(
        "LIVE-03",
        "conflict_or_feedback",
        "https://github.com/aseuteurideu/FGI",
        exercise_feedback=True,
    ),
)

_REPOSITORY_FILES = {
    "github:facebookresearch/detr": (
        "main",
        "detr",
        ("README.md", "requirements.txt", "main.py", "engine.py", "datasets/coco_eval.py"),
    ),
    "github:karpathy/minGPT": (
        "master",
        None,
        ("README.md", "mingpt/model.py", "mingpt/trainer.py"),
    ),
    "github:aseuteurideu/FGI": (
        "master",
        None,
        ("README.md", "package-list.txt", "write_csv.py", "dataset_3d.py"),
    ),
}


class AcceptanceRepositoryCollector:
    """Read only a frozen public-file allowlist for repeatable live LLM acceptance."""

    def __init__(self, settings: Settings) -> None:
        proxy = settings.llm_https_proxy.strip() if settings.llm_https_proxy else None
        self.client = httpx.Client(timeout=30, follow_redirects=False, proxy=proxy)
        self.root = Path(__file__).resolve().parents[1] / ".acceptance"

    def collect(self, target) -> RepositoryMaterials:
        specification = _REPOSITORY_FILES.get(target.canonical_id)
        if specification is None:
            raise RepositoryCollectionError("PA-09 target is outside the acceptance allowlist")
        branch, local_name, paths = specification
        owner_repo = target.canonical_id.removeprefix("github:")
        files = [
            self._read(owner_repo, branch, local_name, path)
            for path in paths
        ]
        readme = next(item for item in files if item.path.casefold() == "readme.md")
        dependencies = tuple(
            item
            for item in files
            if item.path.casefold() in {"requirements.txt", "package-list.txt"}
        )
        evaluation = tuple(
            item for item in files if item is not readme and item not in dependencies
        )
        repository_url = f"https://github.com/{owner_repo}"
        return RepositoryMaterials(
            repository_url=repository_url,
            default_branch=branch,
            readme=readme,
            dependency_files=dependencies,
            evaluation_files=evaluation,
            relevant_paths=tuple(item.path for item in files),
            fetched_at=datetime.now(UTC),
            external_asset_references=(
                GitHubRepositoryMaterialCollector._extract_external_asset_references(readme)
            ),
            dataset_references=(
                GitHubRepositoryMaterialCollector._extract_dataset_references(readme)
            ),
        )

    def read_file_url(self, url: str) -> RepositoryTextFile:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or len(parts) < 5
            or parts[2] != "blob"
        ):
            raise RepositoryCollectionError("PA-09 file URL is outside the GitHub allowlist")
        owner_repo = "/".join(parts[:2])
        branch = parts[3]
        path = "/".join(parts[4:])
        canonical_id = f"github:{owner_repo}"
        specification = _REPOSITORY_FILES.get(canonical_id)
        if (
            specification is None
            or branch != specification[0]
            or not path
            or len(path) > 500
            or any(part in {"", ".", ".."} for part in path.split("/"))
        ):
            raise RepositoryCollectionError("PA-09 file is outside the frozen file allowlist")
        return self._read(owner_repo, branch, specification[1], path)

    def _read(
        self,
        owner_repo: str,
        branch: str,
        local_name: str | None,
        path: str,
    ) -> RepositoryTextFile:
        local_path = self.root / local_name / Path(path) if local_name is not None else None
        if local_path is not None and local_path.is_file():
            content = local_path.read_text(
                encoding="utf-8", errors="replace"
            )
        else:
            url = f"https://raw.githubusercontent.com/{owner_repo}/{branch}/{path}"
            response = self.client.get(url)
            response.raise_for_status()
            content = response.text
        return RepositoryTextFile(
            path=path,
            text=content,
            html_url=f"https://github.com/{owner_repo}/blob/{branch}/{path}",
            size=len(content.encode()),
        )


def _workflow(settings: Settings, *, max_rounds: int, max_tool_requests: int):
    collector = AcceptanceRepositoryCollector(settings)
    assessment_service = ReadinessAssessmentService(
        repository_material_collector=collector
    )
    model = DeepSeekAnalysisModel(settings)
    executor = DeterministicResearchToolExecutor(
        repository_collector=assessment_service.repository_material_collector,
        paper_collector=assessment_service.paper_material_collector,
        dataset_probe=assessment_service.data_access_service.probe,
        checkpoint_probe=assessment_service.external_asset_probe,
        environment_service=assessment_service.environment_fact_service,
    )
    loop = PhasedResearchLoopService(
        model,
        executor,
        settings,
        max_rounds=max_rounds,
        max_tool_requests=max_tool_requests,
    )
    return ModelBackedReadinessWorkflowService(
        assessment_service,
        evidence_model=model,
        research_loop=loop,
    )


def _fingerprint(assessment: ReadinessAssessment) -> str:
    payload = {
        "gate": assessment.overall_gate,
        "dimensions": [
            {
                "id": dimension.dimension_id,
                "status": dimension.status,
                "findings": sorted(
                    (finding.condition, finding.finding_type, finding.gate_critical)
                    for finding in dimension.findings
                ),
            }
            for dimension in assessment.dimensions
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    return sha256(encoded).hexdigest()[:16]


def _lineage_issues(assessment: ReadinessAssessment) -> list[str]:
    issues: list[str] = []
    for dimension in assessment.dimensions:
        for finding in dimension.findings:
            for evidence in finding.evidence:
                if not evidence.source_id:
                    issues.append(f"{finding.finding_id}:missing_source_id")
                if not evidence.location:
                    issues.append(f"{finding.finding_id}:missing_location")
                if (evidence.line_start is None) != (evidence.line_end is None):
                    issues.append(f"{finding.finding_id}:partial_line_range")
    return issues


def _connector_audit(assessment: ReadinessAssessment) -> list[dict[str, Any]]:
    """Expose only content-free connector outcomes in the acceptance report."""
    events: list[dict[str, Any]] = []
    for event in assessment.audit_trail:
        if event.stage != "research_tool_execution":
            continue
        results: list[dict[str, str]] = []
        for ref in event.refs:
            if not ref.startswith("tool_result:"):
                continue
            _, request_id, tool_name, status, failure_code = ref.split(":", 4)
            results.append(
                {
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "status": status,
                    "failure_code": failure_code,
                }
            )
        events.append(
            {
                "outcome": event.outcome,
                "duration_ms": event.duration_ms,
                "results": results,
            }
        )
    return events


def _summary(case: LiveCase, assessment: ReadinessAssessment) -> dict[str, Any]:
    findings = [
        finding for dimension in assessment.dimensions for finding in dimension.findings
    ]
    evidence = [item for finding in findings for item in finding.evidence]
    return {
        "case_id": case.case_id,
        "profile": case.profile,
        "repository": case.repository_url,
        "status": assessment.status,
        "analysis_state": assessment.analysis_state,
        "gate_available": assessment.gate_available,
        "overall_gate": assessment.overall_gate,
        "dimension_statuses": {
            item.dimension_id: item.status for item in assessment.dimensions
        },
        "finding_count": len(findings),
        "evidence_count": len(evidence),
        "lineage_issues": _lineage_issues(assessment),
        "trace": assessment.trace_summary,
        "connector_audit": _connector_audit(assessment),
        "fingerprint": _fingerprint(assessment),
    }


def _feedback_acceptance(workflow, assessment: ReadinessAssessment) -> dict[str, Any]:
    target = next(
        (
            finding
            for dimension in assessment.dimensions
            for finding in dimension.findings
            if finding.evidence
        ),
        None,
    )
    if target is None:
        return {"attempted": False, "reason": "no_source_bound_finding"}
    response = workflow.submit_feedback(
        assessment.assessment_id,
        AssessmentFeedbackRequest(
            target_type="finding",
            target_id=target.finding_id,
            action="supplement",
            comment=(
                "Reassess only this Finding and its real dependent scope using the "
                "supplied maintainer clarification."
            ),
            source_submission=HumanSourceSubmission(
                material_type="Other",
                title="PA-09 maintainer clarification",
                source_path="user/pa09-maintainer-clarification.txt",
                content=(
                    "For this acceptance run, the project maintainer asks that the targeted "
                    "condition be re-evaluated together with its existing source material."
                ),
            ),
        ),
    )
    history = workflow.get_assessment_revision_history(assessment.assessment_id)
    latest_change = history.changes[-1] if history.changes else None
    return {
        "attempted": True,
        "performed": response.reassessment_performed,
        "state": response.reassessment_state,
        "revision": response.revision,
        "changed_dimension_ids": (
            latest_change.changed_dimension_ids if latest_change is not None else []
        ),
        "prior_assessment_preserved_on_failure": (
            response.reassessment_performed or response.assessment == assessment
        ),
    }


def _run_case(
    case: LiveCase,
    settings: Settings,
    *,
    max_rounds: int,
    max_tool_requests: int,
) -> dict[str, Any]:
    workflow = _workflow(
        settings,
        max_rounds=max_rounds,
        max_tool_requests=max_tool_requests,
    )
    assessment = workflow.create_assessment(
        AssessmentRequest(
            target_type="repository",
            target_entry=case.repository_url,
            environment_mode="later",
        )
    )
    result = _summary(case, assessment)
    if case.exercise_feedback and assessment.status == "completed":
        result["feedback"] = _feedback_acceptance(workflow, assessment)
    return result


def _passed(results: list[dict[str, Any]]) -> bool:
    if len(results) != 3 or any(item["status"] != "completed" for item in results):
        return False
    if any(item["lineage_issues"] for item in results):
        return False
    feedback = next(item for item in results if item["profile"] == "conflict_or_feedback").get(
        "feedback", {}
    )
    return bool(
        feedback.get("attempted")
        and feedback.get("performed")
        and feedback.get("prior_assessment_preserved_on_failure")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[item.case_id for item in CASES])
    parser.add_argument("--max-rounds", type=int, default=2, choices=range(1, 6))
    parser.add_argument("--max-tool-requests", type=int, default=6, choices=range(1, 13))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".acceptance/pa09-live-results.json"),
    )
    args = parser.parse_args()

    settings = Settings()
    if not settings.llm_api_key or not settings.llm_api_key.get_secret_value().strip():
        print(json.dumps({"result": "blocked", "reason": "LLM key is not configured"}))
        return 2

    selected = [item for item in CASES if args.case is None or item.case_id == args.case]
    results: list[dict[str, Any]] = []
    for case in selected:
        try:
            result = _run_case(
                case,
                settings,
                max_rounds=args.max_rounds,
                max_tool_requests=args.max_tool_requests,
            )
        except Exception as exc:  # CLI boundary: retain safe type metadata only.
            result = {
                "case_id": case.case_id,
                "profile": case.profile,
                "repository": case.repository_url,
                "status": "runner_failure",
                "error_type": type(exc).__name__,
            }
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    report = {
        "result": "passed" if args.case is None and _passed(results) else "incomplete",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "api_mode": settings.llm_api_mode,
        "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.output), "result": report["result"]}))
    return 0 if report["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
