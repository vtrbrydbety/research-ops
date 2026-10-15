# PA-09 Real-model Acceptance

## Current status

The controlled PC-01 through PC-09 runtime baseline passes: 13 targeted tests.
The live-provider matrix is implemented but is not yet marked passed.

The matrix uses three real public projects:

| Case | Profile | Project |
| --- | --- | --- |
| LIVE-01 | information-complete repository material | facebookresearch/detr |
| LIVE-02 | materially incomplete reproduction context | karpathy/minGPT |
| LIVE-03 | conflict or feedback reassessment | aseuteurideu/FGI |

DETR is read from the existing read-only shallow clone. minGPT and FGI use a
fixed `raw.githubusercontent.com` allowlist because anonymous GitHub REST was
intermittently unavailable. This acquisition fallback exists only in the
acceptance runner and is not part of the production Assessment path.

## 2026-09-20 observed results

- PC-01 through PC-09: passed (13/13 targeted tests).
- The provider key was present; no credential value was printed or persisted.
- The configured model returned valid Context/Gap and local Evidence/Finding
  objects in direct phase probes, proving that the current schemas are usable.
- Full live runs remained intermittent: observed failures included a fenced or
  concatenated JSON response, an unknown `source_id`, an unavailable tool, and
  `tool_request` with no concrete request.
- The runtime continued to report these as technical states with no fabricated
  business Unknown or Gate.

The following fixes were applied from those observations:

1. A direct repository target cannot be reopened as target ambiguity.
2. Finding and Conflict Dimension labels are projected onto the Rule-supplied
   Condition Context instead of allowing the model to broaden scope.
3. A single JSON object surrounded by a `json` Markdown fence is accepted;
   multiple objects and arbitrary trailing text remain invalid.
4. Unavailable or empty Tool Acquisition requests stop safely with
   `no_reliable_next_source`, leading to Manual Input instead of connector
   execution or a fabricated readiness result.
5. Live reports retain only bounded outcome, lineage, and Trace data.

## Commands

Controlled baseline:

```powershell
.\tools\run-prompt-case-regression.ps1
```

Live matrix:

```powershell
$env:RESEARCHOPS_LLM_API_MODE="chat_completions"
.\.venv\Scripts\python.exe tools/run_live_cross_project_acceptance.py
```

The live command exits with code 1 and `result=incomplete` until all three
cases meet the runner's acceptance checks. Do not describe PA-09 as fully
passed while that report remains incomplete.
