param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment Python was not found: $python"
}

$nodes = @(
    'tests/test_prompt_case_runtime_baseline.py',
    'tests/test_target_resolution.py::test_crossref_candidates_use_real_doi_identity',
    'tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_consumes_declared_gaps_and_runtime_capabilities',
    'tests/test_research_tool_execution.py::test_official_release_is_probed_before_and_supersedes_readme_external_fallback',
    'tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_rejects_unknown_gap_and_safely_stops_unavailable_tool',
    'tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_requires_runtime_authorization_for_local_inspection',
    'tests/test_deepseek_evidence_finding_draft.py::test_local_evidence_finding_sends_only_scoped_sources_and_no_coverage_graph',
    'tests/test_model_readiness_graph.py::test_local_feedback_reassesses_only_declared_dependency_scope_and_retains_evidence',
    'tests/test_deepseek_evidence_finding_draft.py::test_prompt_injection_is_quoted_untrusted_data_in_local_evidence_stage',
    'tests/test_deepseek_context_gap.py::test_context_gap_stage_cannot_select_tools_or_emit_final_decisions',
    'tests/test_model_readiness_graph.py::test_invalid_model_output_has_its_own_failure_state',
    'tests/test_deepseek_tool_acquisition.py::test_tool_acquisition_round_limit_cannot_issue_requests'
)

Push-Location $root
try {
    & $python -m pytest @nodes
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
