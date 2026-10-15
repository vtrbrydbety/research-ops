"""Tool Acquisition prompt tests without network access or API quota."""

import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import httpx
import pytest

from researchops.core.config import Settings
from researchops.schemas import (
    AIContextGapResult,
    MaterialBundle,
    MaterialSource,
    ResolvedTarget,
    ToolAcquisitionInput,
)
from researchops.services import AIModelResponseError, DeepSeekAnalysisModel


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


def _context_gap() -> AIContextGapResult:
    return AIContextGapResult(
        analysis_mode="initial",
        focus={"scope_refs": ["RD-03"], "finding_refs": []},
        supported_facts=[
            {
                "statement": "A checkpoint acquisition link is documented.",
                "source_ref": "src-readme",
                "verification_status": "Located Only",
            }
        ],
        information_gaps=[
            {
                "gap_id": "GAP-checkpoint-access",
                "question": "Can the documented checkpoint be retrieved?",
                "scope_ref": "RD-03",
                "needed_source_type": "Material",
                "reason": "The link alone does not establish access.",
            }
        ],
        control={
            "target_confirmation_needed": False,
            "more_information_needed": True,
            "stop_reason": None,
        },
    )


def _input(**overrides: object) -> ToolAcquisitionInput:
    values: dict[str, object] = {
        "bundle": _bundle(),
        "context_gap": _context_gap(),
        "available_tools": ["fetch_web_page", "probe_checkpoint_access"],
        "local_environment_authorized": False,
        "current_round": 0,
        "configured_max_rounds": 5,
        "remaining_tool_requests": 12,
    }
    values.update(overrides)
    return ToolAcquisitionInput(**values)


def _tool_payload(
    *,
    gap_ref: str = "GAP-checkpoint-access",
    tool_ref: str = "probe_checkpoint_access",
) -> dict[str, object]:
    executable_argument = (
        {"query": "official checkpoint source"}
        if tool_ref in {"search_web", "search_github"}
        else {"url": "https://github.com/example/project/releases/download/v1/model.pt"}
        if tool_ref != "inspect_local_environment"
        else {}
    )
    return {
        "acquisition_state": "tool_request",
        "requests": [
            {
                "gap_ref": gap_ref,
                "requested_fact": "Whether the documented checkpoint link can be read.",
                "source_type": "Material",
                "material_type_hint": "Checkpoint-Release",
                "tool_ref": tool_ref,
                "read_scope": "Only the documented official checkpoint URL.",
                **executable_argument,
                "expected_evidence": "A deterministic read-only probe result.",
                "authorization_required": False,
                "alternative_input": None,
            }
        ],
        "loop_control": {
            "current_round": 0,
            "configured_max_rounds": 5,
            "continue_after_result": True,
            "stop_reason": None,
        },
    }


def _stop_payload() -> dict[str, object]:
    return {
        "acquisition_state": "stop_acquisition",
        "requests": [],
        "loop_control": {
            "current_round": 5,
            "configured_max_rounds": 5,
            "continue_after_result": False,
            "stop_reason": "round_limit",
        },
    }


def _chat_response(payload: dict[str, object]) -> dict[str, object]:
    return {
        "id": "tool-acquisition-request-1",
        "choices": [{"message": {"role": "assistant", "content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


def test_tool_acquisition_consumes_declared_gaps_and_runtime_capabilities() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_chat_response(_tool_payload()))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).plan_tool_acquisition(_input())

    request_payload = observed["payload"]
    assert isinstance(request_payload, dict)
    system_prompt = request_payload["messages"][0]["content"]
    user_payload = json.loads(request_payload["messages"][1]["content"])
    schema_properties = user_payload["OUTPUT_SCHEMA"]["properties"]

    assert user_payload["ANALYSIS_STAGE"] == "tool_acquisition"
    assert "TOOL_ACQUISITION_CONTEXT" in user_payload
    assert user_payload["RUNTIME_CAPABILITIES"]["available_tools"] == [
        "fetch_web_page",
        "probe_checkpoint_access",
    ]
    assert user_payload["RUNTIME_CAPABILITIES"]["remaining_tool_requests"] == 12
    assert "Do not invent a new\nbusiness objective" in system_prompt
    assert "overall_gate" not in schema_properties
    assert "tool_results" not in schema_properties
    assert invocation.result.requests[0].gap_ref == "GAP-checkpoint-access"
    assert invocation.trace.request_id == "tool-acquisition-request-1"


def test_tool_acquisition_stops_an_over_budget_plan_without_selecting_a_subset() -> None:
    payload = _tool_payload()
    payload["requests"] = [payload["requests"][0], dict(payload["requests"][0])]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(payload))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).plan_tool_acquisition(_input(remaining_tool_requests=1))

    assert invocation.result.acquisition_state == "stop_acquisition"
    assert invocation.result.requests == []
    assert invocation.result.loop_control.stop_reason == "request_budget_exhausted"


def test_tool_acquisition_rejects_unknown_gap_and_safely_stops_unavailable_tool() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_chat_response(_tool_payload(gap_ref="GAP-invented")),
        )

    with pytest.raises(AIModelResponseError, match="unknown Context & Gap"):
        DeepSeekAnalysisModel(
            _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
        ).plan_tool_acquisition(_input())

    def unavailable_tool_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_chat_response(_tool_payload(tool_ref="search_web")),
        )

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(unavailable_tool_handler))
    ).plan_tool_acquisition(_input())

    assert invocation.result.acquisition_state == "stop_acquisition"
    assert invocation.result.requests == []
    assert invocation.result.loop_control.stop_reason == "no_reliable_next_source"


def test_tool_acquisition_empty_tool_request_safely_stops_for_manual_input() -> None:
    payload = _tool_payload()
    payload["requests"] = []

    invocation = DeepSeekAnalysisModel(
        _settings(),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=_chat_response(payload))
            )
        ),
    ).plan_tool_acquisition(_input())

    assert invocation.result.acquisition_state == "stop_acquisition"
    assert invocation.result.loop_control.stop_reason == "no_reliable_next_source"


def test_tool_acquisition_mislabeled_manual_requests_become_alternative_input() -> None:
    payload = _tool_payload()
    request = payload["requests"][0]  # type: ignore[index]
    request["tool_ref"] = None
    request["read_scope"] = None
    request["url"] = None
    request["alternative_input"] = "manual"

    invocation = DeepSeekAnalysisModel(
        _settings(),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=_chat_response(payload))
            )
        ),
    ).plan_tool_acquisition(_input())

    assert invocation.result.acquisition_state == "alternative_input"
    assert invocation.result.requests[0].alternative_input == "manual"
    assert invocation.result.loop_control.continue_after_result is False
    assert invocation.result.loop_control.stop_reason == "no_reliable_next_source"


def test_tool_acquisition_round_limit_cannot_issue_requests() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(_stop_payload()))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).plan_tool_acquisition(_input(current_round=5))

    assert invocation.result.acquisition_state == "stop_acquisition"
    assert not invocation.result.requests


def test_tool_acquisition_runtime_owns_loop_state() -> None:
    payload = _tool_payload()
    payload["loop_control"]["current_round"] = 1  # type: ignore[index]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(payload))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).plan_tool_acquisition(_input())

    assert invocation.result.loop_control.current_round == 0
    assert invocation.result.loop_control.configured_max_rounds == 5


def test_tool_acquisition_requires_runtime_authorization_for_local_inspection() -> None:
    payload = _tool_payload(tool_ref="inspect_local_environment")
    payload["requests"][0]["authorization_required"] = True  # type: ignore[index]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(payload))

    with pytest.raises(AIModelResponseError, match="runtime authorization"):
        DeepSeekAnalysisModel(
            _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
        ).plan_tool_acquisition(
            _input(available_tools=["inspect_local_environment"])
        )


def test_tool_acquisition_strict_tool_mode_is_only_a_data_container() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "tool-acquisition-tool-request-1",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "submit_researchops_tool_acquisition",
                                        "arguments": json.dumps(_tool_payload()),
                                    }
                                }
                            ]
                        },
                    }
                ],
            },
        )

    invocation = DeepSeekAnalysisModel(
        _settings(llm_api_mode="strict_tools"),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    ).plan_tool_acquisition(_input())

    request_payload = observed["payload"]
    assert isinstance(request_payload, dict)
    assert request_payload["tool_choice"]["function"]["name"] == (
        "submit_researchops_tool_acquisition"
    )
    assert invocation.result.acquisition_state == "tool_request"


def test_tool_acquisition_async_uses_the_same_contract() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(_tool_payload()))

    async def run() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            invocation = await DeepSeekAnalysisModel(
                _settings(), async_client=client
            ).plan_tool_acquisition_async(_input())
        finally:
            await client.aclose()
        assert invocation.result.loop_control.continue_after_result is True

    asyncio.run(run())
