# Prompt Case Runtime Regression Baseline

This is the executable PA-09 regression baseline for the phased production path:
Context & Gap → Tool Acquisition → local Evidence & Finding → Rule.

Run the controlled cases from the repository root:

```powershell
.\tools\run-prompt-case-regression.ps1
```

| Case | Focus | Required assertion | Test layer |
| --- | --- | --- | --- |
| PC-01 | Target/source ambiguity | The Human confirms ambiguous candidates; none is silently selected. | Controlled runtime |
| PC-02 | Official checkpoint acquisition | Rule probes an official Release before a README external fallback and skips the fallback after verification. | Controlled provider + Rule executor |
| PC-03 | No tool / authorization denied | Unavailable tools stop safely for Manual Input; unauthorized local reads never execute. | Controlled provider |
| PC-04 | Conflicting material | Current and retained Evidence remain explicitly linked on both sides of a scoped Conflict. | Controlled provider |
| PC-05 | Local feedback impact | Only the primary and genuinely dependent Dimensions are reassessed; old Evidence remains traceable. | Controlled runtime |
| PC-06 | Prompt injection | Material remains untrusted data and cannot grant tools or decisions. | Controlled provider |
| PC-07 | Gate boundary | The model cannot emit a formal Gate; Rule is the sole Gate owner. | Controlled provider |
| PC-08 | Invalid structured output | A schema failure is reported as a technical state, never a fabricated business Unknown. | Controlled runtime |
| PC-09 | Tool-round limit | The fifth round stops acquisition without another tool request. | Controlled provider |

`tests/test_prompt_case_runtime_baseline.py` verifies that PC-01 through PC-09
remain mapped to runnable pytest nodes. A controlled-provider test uses the real
client adapter with `httpx.MockTransport`, never an API key or a network request.

## Live-project acceptance

Live acceptance is intentionally opt-in and must be run only after the controlled
baseline passes. It requires a configured provider key and tests three project
categories: information-complete, material-missing, and conflict/feedback-needed.
Its report must record only case outcome, trace identifiers, timings, rounds,
source IDs, and Rule outputs—never prompts, raw responses, or credentials.

Run it explicitly with:

```powershell
$env:RESEARCHOPS_LLM_API_MODE="chat_completions"
.\.venv\Scripts\python.exe tools/run_live_cross_project_acceptance.py
```

The command exits non-zero and writes `result=incomplete` if any case remains a
technical Partial, if source lineage is incomplete, or if the feedback case did
not perform a retained-revision reassessment. A controlled baseline pass must
never be reported as a live-provider pass.
