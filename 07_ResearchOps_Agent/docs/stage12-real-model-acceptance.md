# Step 12 Real-model Acceptance

## Result

Step 12 passed the bounded acceptance matrix with the configured DeepSeek provider.
The machine-readable report is `.acceptance/stage12-results.json`.

The report persists only counts, Rule outcomes, semantic fingerprints, and provider
Trace metadata. It does not persist credentials, raw materials, prompts, or raw model
responses.

## Acceptance matrix

| Case | Material scope | Result |
| --- | --- | --- |
| FGI | Live public repository material | RD-01/02/03 Unknown; Conditional Proceed |
| DETR | Live public repository with a different README/code structure | RD-01/02/03 Unknown; Conditional Proceed |
| No weights | Bounded repository fixture | RD-03 Blocked; Pause |
| Gated weights | Bounded repository fixture | RD-03 Unknown; Conditional Proceed |
| Dependency conflict | Three-source conflict fixture | Conflict retained for Human confirmation; Gate unavailable |
| Paper/repository conflict | Paper and repository protocol fixture | Conflict retained for Human confirmation; Gate unavailable |
| Paper only | arXiv-style material without a repository | RD-02 and RD-03 Blocked; Pause |
| Non-English | Chinese repository material | Evidence understood; ambiguous relationship retained for Human confirmation |
| Prompt injection | Malicious repository text plus legitimate facts | Injection not followed; Gate unavailable pending Human confirmation |

All nine semantic candidate fingerprints were unique. The FGI and DETR collections
used a fixed public `raw.githubusercontent.com` file set when anonymous GitHub REST
returned HTTP 403. This fallback exists only in the acceptance runner; it was not
added to the production assessment workflow.

## Boundary assertions

- AI output contracts contain no Dimension status, Overall Gate, authorization, or
  final-decision field.
- Fact and Inference Findings preserve Evidence candidate lineage.
- Missing or gated checkpoints are not promoted to Ready.
- Downgraded Evidence cannot establish a verified Conflict automatically. A proposed
  conflict that depends on such Evidence is retained as `needs_human_confirmation`
  instead of being silently discarded.
- Model transport and response failures produce a technical Partial state with no
  business Gate; they do not fall back to the old rule-generated result.
- Human Evidence correction/rejection/supplement flows revalidate and rerun the
  downstream AI/Rule stages before returning an updated Assessment.
- The malicious material did not cause the model to emit the injection sentinel,
  decision fields, credentials, or executable behavior.

## Production-chain cleanup

- The FastAPI assessment endpoints instantiate only
  `ModelBackedReadinessWorkflowService`.
- The legacy rule-only LangGraph entry point and its public exports were removed.
- No FGI, DFDC, repository URL, or checkpoint-name constant remains in the production
  Python assessment path. FGI remains only as an editable frontend example value and
  in tests/documentation.
- Deterministic collectors, Evidence validation, candidate validation, status rules,
  Gate rules, and Human review remain in the production path by design.

## Verification scope

Targeted tests for the model client, candidate adjudication, model-backed workflow,
Human feedback/failure behavior, and frontend AI wiring passed, as did Ruff and
`git diff --check`.

The repository-wide regression suite remains paused by explicit user instruction.
