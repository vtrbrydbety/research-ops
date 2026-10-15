"""Controlled provider and materials for public integration/browser acceptance.

The real model adapter, graph, rules, storage, scheduler and perimeter run unchanged.
Only repository I/O and provider HTTP responses are synthetic; no paid key is used.
"""

import json
from datetime import UTC, datetime
from threading import Lock, get_ident

import httpx

from researchops.core.access_context import current_access
from researchops.core.config import Settings
from researchops.services import (
    DeepSeekAnalysisModel,
    DurableAssessmentReviewStore,
    ModelBackedReadinessWorkflowService,
    ReadinessAssessmentService,
    RepositoryMaterials,
    RepositoryTextFile,
)


class ControlledRepositoryCollector:
    def collect(self, _target):
        text = "# Controlled public-flow material\nPython 3.11 is required."
        return RepositoryMaterials(
            repository_url="https://github.com/example/project",
            default_branch="main",
            readme=RepositoryTextFile(
                path="README.md",
                text=text,
                html_url="https://github.com/example/project/blob/main/README.md",
                size=len(text.encode()),
            ),
            dependency_files=(),
            relevant_paths=("README.md",),
            fetched_at=datetime.now(UTC),
        )


class ControlledProvider:
    def __init__(self):
        self.calls = []
        self.lock = Lock()

    def __call__(self, request):
        payload = json.loads(request.content)
        content = json.loads(payload["messages"][1]["content"])
        stage = content["ANALYSIS_STAGE"]
        context = current_access.get()
        if context is None or context.operation is None:
            raise AssertionError("Model HTTP escaped the principal/operation context")
        with self.lock:
            self.calls.append((stage, context.principal, context.operation, get_ident()))
        if stage == "context_gap":
            result = {
                "analysis_mode": "initial",
                "focus": {"scope_refs": ["RD-01", "RD-02", "RD-03"]},
                "supported_facts": [],
                "information_gaps": [],
                "control": {"target_confirmation_needed": False, "more_information_needed": False},
            }
        elif stage == "feedback_reassessment":
            review = content["MATERIAL_BUNDLE"]["human_review_context"]
            result = {
                "reassessment_id": "00000000-0000-4000-8000-000000000001",
                "bundle_id": content["MATERIAL_BUNDLE"]["bundle_id"],
                "reassessment_required": True,
                "affected_scope": {
                    "finding_refs": [review["original_finding"]["finding_id"]],
                    "dimension_refs": ["RD-01"],
                },
                "change_summary": "A user supplement affects the selected condition.",
                "handoff": "evidence_finding",
            }
        elif stage == "evidence_finding_draft":
            scope = content["EVIDENCE_FINDING_CONTEXT"]
            condition = scope["condition_contexts"][0]
            sources = content["MATERIAL_SCOPE"]["sources"]
            source = next(
                (item for item in sources if item["access_scope"] == "user_provided"), sources[0]
            )
            review = scope["human_review_context"]
            quote = source["content"].splitlines()[0]
            result = {
                "evidence_drafts": [
                    {
                        "local_evidence_id": "local-source",
                        "condition_refs": [condition["condition_ref"]],
                        "source_ref": source["source_id"],
                        "source_type": "User Context" if review else "Material",
                        "evidence_type": "Unknown",
                        "location": f"{source['source_path']}:line 1",
                        "line_start": 1,
                        "line_end": 1,
                        "material_type": source["material_type"],
                        "quote": quote,
                        "claim": "The available material leaves this condition unresolved.",
                        "verification_status": "Located Only",
                    }
                ],
                "finding_drafts": [
                    {
                        "local_finding_id": "local-finding",
                        "operation": "update_existing" if review else "create",
                        "existing_finding_ref": review["original_finding"]["finding_id"]
                        if review
                        else None,
                        "condition": condition["condition_ref"],
                        "summary": "The condition remains unresolved.",
                        "finding_type": "Unknown",
                        "primary_dimension": condition["primary_dimension"],
                        "evidence_refs_local": ["local-source"],
                    }
                ],
                "handoff": {"needs_more_information": False, "ready_for_rule": True},
            }
        else:
            raise AssertionError(f"Unexpected controlled phase: {stage}")
        return httpx.Response(
            200,
            json={
                "id": "controlled-request",
                "choices": [{"message": {"content": json.dumps(result)}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            },
        )


def controlled_workflow(settings: Settings):
    provider = ControlledProvider()
    model_config = settings.model_copy(
        update={
            "llm_api_key": "synthetic-not-a-real-key",
            "llm_api_mode": "chat_completions",
            "llm_max_retries": 0,
        }
    )
    # model_copy deliberately bypasses validation, so construct to retain SecretStr typing.
    model_config = Settings(_env_file=None, **model_config.model_dump())
    model = DeepSeekAnalysisModel(
        model_config, client=httpx.Client(transport=httpx.MockTransport(provider))
    )
    workflow = ModelBackedReadinessWorkflowService(
        ReadinessAssessmentService(repository_material_collector=ControlledRepositoryCollector()),
        evidence_model=model,
        review_store=DurableAssessmentReviewStore(settings),
    )
    return workflow, provider
