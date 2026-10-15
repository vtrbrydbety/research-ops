"""Frozen Prompt Case PC-01..PC-09 regression-manifest checks.

The cases themselves run through the node IDs below.  This module prevents a
future refactor from silently dropping the mapping, its expected outcome, or
the required controlled-provider coverage.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptCaseBaseline:
    case_id: str
    frozen_focus: str
    expected_assertion: str
    execution_level: str
    test_nodes: tuple[str, ...]


BASELINES = (
    PromptCaseBaseline(
        "PC-01",
        "Target / source ambiguity",
        "An ambiguous target is retained for Human confirmation; no candidate is selected by default.",
        "controlled_runtime",
        ("tests/test_target_resolution.py::test_crossref_candidates_use_real_doi_identity",),
    ),
    PromptCaseBaseline(
        "PC-02",
        "Official checkpoint acquisition order",
        "Rule probes an official Release before a README external fallback and skips that fallback after public verification.",
        "controlled_provider",
        (
            "tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_consumes_declared_gaps_and_runtime_capabilities",
            "tests/test_research_tool_execution.py::test_official_release_is_probed_before_and_supersedes_readme_external_fallback",
        ),
    ),
    PromptCaseBaseline(
        "PC-03",
        "No tool / authorization denied",
        "Unavailable tools and unauthorized local inspection are rejected before connector execution.",
        "controlled_provider",
        (
            "tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_rejects_unknown_gap_and_safely_stops_unavailable_tool",
            "tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_requires_runtime_authorization_for_local_inspection",
        ),
    ),
    PromptCaseBaseline(
        "PC-04",
        "Conflicting material remains traceable",
        "Both sides remain explicitly linked when current material conflicts with retained Evidence.",
        "controlled_provider",
        ("tests/test_deepseek_evidence_finding_draft.py::test_local_evidence_finding_sends_only_scoped_sources_and_no_coverage_graph",),
    ),
    PromptCaseBaseline(
        "PC-05",
        "Feedback local impact",
        "Only the primary and genuinely dependent Dimensions are reassessed; retained Evidence remains linked.",
        "controlled_runtime",
        ("tests/test_model_readiness_graph.py::test_local_feedback_reassesses_only_declared_dependency_scope_and_retains_evidence",),
    ),
    PromptCaseBaseline(
        "PC-06",
        "Prompt injection",
        "Repository text remains untrusted material and does not grant execution or decision authority.",
        "controlled_provider",
        ("tests/test_deepseek_evidence_finding_draft.py::test_prompt_injection_is_quoted_untrusted_data_in_local_evidence_stage",),
    ),
    PromptCaseBaseline(
        "PC-07",
        "Model cannot decide Gate",
        "Context/Gap output admits neither tool selection nor formal Gate fields.",
        "controlled_provider",
        ("tests/test_deepseek_context_gap.py::test_context_gap_stage_cannot_select_tools_or_emit_final_decisions",),
    ),
    PromptCaseBaseline(
        "PC-08",
        "Invalid structured model output",
        "A contract failure is a technical state and never becomes a fabricated business Unknown.",
        "controlled_runtime",
        ("tests/test_model_readiness_graph.py::test_invalid_model_output_has_its_own_failure_state",),
    ),
    PromptCaseBaseline(
        "PC-09",
        "Tool round limit",
        "At the fifth round the model cannot issue another acquisition request.",
        "controlled_provider",
        ("tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_round_limit_cannot_issue_requests",),
    ),
)


def _test_function_exists(node_id: str) -> bool:
    path_part, function_name = node_id.split("::", maxsplit=1)
    source_path = Path(__file__).resolve().parents[1] / path_part
    if not source_path.is_file():
        return False
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
        for node in ast.walk(tree)
    )


def test_prompt_case_baseline_is_complete_and_points_to_runnable_tests() -> None:
    assert [item.case_id for item in BASELINES] == [f"PC-{number:02d}" for number in range(1, 10)]
    assert all(item.frozen_focus and item.expected_assertion for item in BASELINES)
    assert all(item.test_nodes for item in BASELINES)
    assert all(_test_function_exists(node) for item in BASELINES for node in item.test_nodes)


def test_prompt_cases_requiring_provider_coverage_have_a_controlled_provider_path() -> None:
    required = {"PC-02", "PC-03", "PC-04", "PC-06", "PC-07", "PC-09"}
    covered = {
        item.case_id
        for item in BASELINES
        if item.execution_level in {"controlled_provider", "controlled_provider_no_call"}
    }
    assert required <= covered
