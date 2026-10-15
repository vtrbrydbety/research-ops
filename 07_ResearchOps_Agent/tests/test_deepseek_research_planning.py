"""Research-planning model tests without network access or API quota."""

import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import httpx
import pytest

from researchops.core.config import Settings
from researchops.schemas import (
    Finding,
    HumanReviewContext,
    MaterialBundle,
    MaterialSource,
    ResolvedTarget,
)
from researchops.services import AIModelResponseError, DeepSeekAnalysisModel
from tests.test_deepseek_context_gap import _context_gap_payload
from tests.test_deepseek_tool_acquisition import _input, _tool_payload


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "llm_api_key": "test-secret-never-log",
        "llm_api_mode": "chat_completions",
        "llm_model": "deepseek-v4-flash",
        "llm_max_retries": 0,
    }
    values.update(overrides)
    return Settings(**values)


def _bundle() -> MaterialBundle:
    content = "Weights: https://drive.google.com/file/d/checkpoint-id/view"
    return MaterialBundle(
        bundle_id=uuid4(),
        target=ResolvedTarget(
            target_type="repository",
            source_entry="https://github.com/example/project",
            display_name="example/project",
            canonical_id="github:example/project",
            canonical_url="https://github.com/example/project",
            resolution_method="direct_url",
        ),
        assembled_at=datetime.now(UTC),
        sources=[
            MaterialSource(
                source_id="src-readme",
                material_type="README",
                title="README",
                source_path="README.md",
                source_url="https://github.com/example/project/blob/main/README.md",
                content=content,
                content_sha256=sha256(content.encode()).hexdigest(),
                access_scope="public",
            )
        ],
    )


# Research planning now uses separate Context & Gap and Tool Acquisition contracts.


def _chat_response(payload):
    return {
        "id": "planner-request-1",
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


def test_research_planning_calls_real_provider_contract_without_executing_tools():
    observed = {}

    def handler(request):
        observed.update(json.loads(request.content))
        return httpx.Response(200, json=_chat_response(_tool_payload()))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).plan_tool_acquisition(_input())
    content = json.loads(observed["messages"][1]["content"])
    assert content["ANALYSIS_STAGE"] == "tool_acquisition"
    properties = content["OUTPUT_SCHEMA"]["properties"]
    assert not {"overall_gate", "dimension_status", "evidence_candidates"} & properties.keys()
    assert content["RUNTIME_CAPABILITIES"]["remaining_tool_requests"] == 12
    assert invocation.result.requests[0].tool_ref == "probe_checkpoint_access"
    assert invocation.trace.request_id == "planner-request-1"
    assert invocation.trace.total_tokens == 30


def test_research_planning_rejects_non_allowlisted_tool_name():
    payload = _tool_payload(tool_ref="run_shell")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_chat_response(payload)))
    )
    with pytest.raises(AIModelResponseError):
        DeepSeekAnalysisModel(_settings(), client=client).plan_tool_acquisition(_input())


def test_research_planning_rejects_unknown_material_source_reference():
    payload = _tool_payload(gap_ref="invented-gap")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_chat_response(payload)))
    )
    with pytest.raises(AIModelResponseError, match="Gap|gap"):
        DeepSeekAnalysisModel(_settings(), client=client).plan_tool_acquisition(_input())


def test_research_planning_strict_tool_mode_uses_output_container_only():
    observed = {}

    def handler(request):
        observed.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "submit_researchops_tool_acquisition",
                                        "arguments": json.dumps(_tool_payload()),
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        )

    invocation = DeepSeekAnalysisModel(
        _settings(llm_api_mode="strict_tools"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ).plan_tool_acquisition(_input())
    assert observed["tool_choice"]["function"]["name"] == "submit_researchops_tool_acquisition"
    assert len(observed["tools"]) == 1
    assert '"format": "uri"' not in json.dumps(observed["tools"])
    assert invocation.result.acquisition_state == "tool_request"


def test_research_planning_async_uses_same_contract():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=_chat_response(_tool_payload()))
            )
        ) as client:
            invocation = await DeepSeekAnalysisModel(
                _settings(), async_client=client
            ).plan_tool_acquisition_async(_input())
        assert invocation.result.acquisition_state == "tool_request"

    asyncio.run(run())


def test_research_planning_passes_human_context_to_controlled_provider():
    bundle = _bundle().model_copy(
        update={
            "human_review_context": HumanReviewContext(
                target_type="finding",
                target_id="finding-dataset-access",
                action="supplement",
                comment="I can access the required dataset.",
                original_finding=Finding(
                    finding_id="finding-dataset-access",
                    condition="rd01.dataset_access",
                    title="Verify dataset access",
                    summary="Access was not established.",
                    finding_type="Unknown",
                    readiness_impact="Access remains unresolved.",
                ),
            )
        }
    )
    observed = {}

    def handler(request):
        observed.update(json.loads(request.content))
        payload = _context_gap_payload()
        payload["supported_facts"] = []
        payload["information_gaps"] = []
        payload["control"]["more_information_needed"] = False
        return httpx.Response(200, json=_chat_response(payload))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).analyze_context_gaps(bundle)
    content = json.loads(observed["messages"][1]["content"])
    context = content["MATERIAL_BUNDLE"]["human_review_context"]
    assert context["target_id"] == "finding-dataset-access"
    assert context["comment"] == "I can access the required dataset."
    assert invocation.result.information_gaps == []
    assert invocation.result.control.more_information_needed is False


def test_research_planning_stops_when_controlled_provider_reports_sufficient_evidence():
    payload = _context_gap_payload()
    payload["information_gaps"] = []
    payload["control"]["more_information_needed"] = False
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_chat_response(payload)))
    )
    invocation = DeepSeekAnalysisModel(_settings(), client=client).analyze_context_gaps(_bundle())
    assert invocation.result.information_gaps == []
    assert invocation.result.control.more_information_needed is False
    assert not hasattr(invocation.result, "tool_requests")


def test_feedback_reassessment_uses_a_dedicated_provider_stage() -> None:
    bundle = _bundle().model_copy(
        update={
            "human_review_context": HumanReviewContext(
                target_type="finding",
                target_id="finding-access",
                action="supplement",
                comment="I can access the dataset.",
                original_finding=Finding(
                    finding_id="finding-access",
                    condition="rd01.dataset_access",
                    title="Verify access",
                    summary="Access was unknown.",
                    finding_type="Unknown",
                    readiness_impact="Access remains unresolved.",
                ),
            )
        }
    )
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json=_chat_response(
                {
                    "reassessment_required": True,
                    "affected_scope": {
                        "finding_refs": ["finding-access"],
                        "evidence_refs": [],
                        "dimension_refs": ["RD-01"],
                        "signal_refs": [],
                    },
                    "change_summary": "The customer supplied a first-party access fact.",
                    "information_gaps": [],
                    "handoff": "evidence_finding",
                }
            ),
        )

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).reassess_feedback(bundle)

    payload = observed["payload"]
    assert isinstance(payload, dict)
    request_context = json.loads(payload["messages"][1]["content"])
    assert request_context["ANALYSIS_STAGE"] == "feedback_reassessment"
    assert request_context["FEEDBACK_SCOPE_CONSTRAINTS"] == {
        "target_type": "finding",
        "target_id": "finding-access",
        "required_finding_id": "finding-access",
        "required_evidence_id": None,
        "required_dimension_id": "RD-01",
        "instruction": (
            "For a required reassessment, include the exact required IDs above in "
            "affected_scope. Do not invent identifiers."
        ),
    }
    assert invocation.result.affected_scope.finding_refs == ["finding-access"]
    assert invocation.result.handoff == "evidence_finding"
