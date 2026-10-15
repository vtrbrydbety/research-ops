"""Context & Gap prompt tests without network access or API quota."""

import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import httpx

from researchops.core.config import Settings
from researchops.schemas import MaterialBundle, MaterialSource, ResolvedTarget
from researchops.services import DeepSeekAnalysisModel


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


def _context_gap_payload(*, source_ref: str = "src-readme") -> dict[str, object]:
    return {
        "analysis_mode": "initial",
        "focus": {"scope_refs": ["RD-03"], "finding_refs": []},
        "supported_facts": [
            {
                "statement": "A checkpoint acquisition link is documented.",
                "source_ref": source_ref,
                "verification_status": "Located Only",
            }
        ],
        "information_gaps": [
            {
                "gap_id": "GAP-checkpoint-access",
                "question": "Can the documented checkpoint be retrieved?",
                "scope_ref": "RD-03",
                "needed_source_type": "Material",
                "reason": "The link alone does not establish access.",
            }
        ],
        "control": {
            "target_confirmation_needed": False,
            "more_information_needed": True,
            "stop_reason": None,
        },
    }


def _chat_response(payload: dict[str, object]) -> dict[str, object]:
    return {
        "id": "context-gap-request-1",
        "choices": [{"message": {"role": "assistant", "content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
    }


def test_context_gap_accepts_only_a_single_json_object_inside_markdown_fence() -> None:
    response = _chat_response(_context_gap_payload())
    response["choices"][0]["message"]["content"] = (
        "```json\n" + response["choices"][0]["message"]["content"] + "\n```"
    )
    invocation = DeepSeekAnalysisModel(
        _settings(),
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))
        ),
    ).analyze_context_gaps(_bundle())

    assert invocation.result.information_gaps[0].gap_id == "GAP-checkpoint-access"


def test_context_gap_stage_cannot_select_tools_or_emit_final_decisions() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(request.content)
        return httpx.Response(200, json=_chat_response(_context_gap_payload()))

    invocation = DeepSeekAnalysisModel(
        _settings(), client=httpx.Client(transport=httpx.MockTransport(handler))
    ).analyze_context_gaps(_bundle())

    request_payload = observed["payload"]
    assert isinstance(request_payload, dict)
    system_prompt = request_payload["messages"][0]["content"]
    user_payload = json.loads(request_payload["messages"][1]["content"])
    schema_properties = user_payload["OUTPUT_SCHEMA"]["properties"]

    assert user_payload["ANALYSIS_STAGE"] == "context_gap"
    assert "Do not select a tool" in system_prompt
    assert "Tool Acquisition is a separate later phase" in system_prompt
    assert "tool_requests" not in schema_properties
    assert "overall_gate" not in schema_properties
    assert "dimension_status" not in schema_properties
    assert invocation.result.information_gaps[0].gap_id == "GAP-checkpoint-access"
    assert invocation.trace.request_id == "context-gap-request-1"


def test_context_gap_drops_an_unknown_source_reference() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_chat_response(_context_gap_payload(source_ref="src-invented")),
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    invocation = DeepSeekAnalysisModel(_settings(), client=client).analyze_context_gaps(
        _bundle()
    )

    assert invocation.result.supported_facts == []
    assert invocation.result.information_gaps[0].gap_id == "GAP-checkpoint-access"


def test_context_gap_normalizes_duplicate_identity_and_runtime_control() -> None:
    payload = _context_gap_payload()
    payload["supported_facts"] = [
        payload["supported_facts"][0],  # type: ignore[index]
        payload["supported_facts"][0],  # type: ignore[index]
    ]
    payload["information_gaps"] = [
        payload["information_gaps"][0],  # type: ignore[index]
        {
            **payload["information_gaps"][0],  # type: ignore[index]
            "question": "Which official artifact is intended?",
        },
    ]
    payload["control"] = {
        "target_confirmation_needed": True,
        "more_information_needed": False,
        "stop_reason": "no_reliable_next_source",
    }

    invocation = DeepSeekAnalysisModel(
        _settings(),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=_chat_response(payload))
            )
        ),
    ).analyze_context_gaps(_bundle())

    assert len(invocation.result.supported_facts) == 1
    assert [gap.gap_id for gap in invocation.result.information_gaps] == [
        "GAP-checkpoint-access",
        "GAP-checkpoint-access-2",
    ]
    assert invocation.result.control.target_confirmation_needed is False
    assert invocation.result.control.more_information_needed is True
    assert invocation.result.control.stop_reason is None


def test_direct_repository_target_cannot_be_reopened_as_target_ambiguity() -> None:
    payload = _context_gap_payload()
    payload["control"] = {
        "target_confirmation_needed": True,
        "more_information_needed": True,
        "stop_reason": "target_confirmation_required",
    }

    invocation = DeepSeekAnalysisModel(
        _settings(),
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json=_chat_response(payload))
            )
        ),
    ).analyze_context_gaps(_bundle())

    assert invocation.result.control.target_confirmation_needed is False
    assert invocation.result.control.more_information_needed is True
    assert invocation.result.control.stop_reason is None


def test_context_gap_strict_tool_mode_uses_a_data_container_only() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "context-gap-tool-request-1",
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "submit_researchops_context_gap",
                                        "arguments": json.dumps(_context_gap_payload()),
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
    ).analyze_context_gaps(_bundle())

    request_payload = observed["payload"]
    assert isinstance(request_payload, dict)
    assert request_payload["tool_choice"]["function"]["name"] == (
        "submit_researchops_context_gap"
    )
    assert invocation.result.focus.scope_refs == ["RD-03"]


def test_context_gap_async_uses_the_same_contract() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_response(_context_gap_payload()))

    async def run() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            invocation = await DeepSeekAnalysisModel(
                _settings(), async_client=client
            ).analyze_context_gaps_async(_bundle())
        finally:
            await client.aclose()
        assert invocation.result.control.more_information_needed is True

    asyncio.run(run())
