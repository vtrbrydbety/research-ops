# Time / Interaction Log

Template ID: Time_Interaction_Log_V1
Version: V1
Date: 2026-08-10
Template Status: FREEZE
Record Status: COMPLETED

Baseline:
Baseline C｜Codex App

Test Date:
2026-08-10

## Timing

Start Time:
14:57:00

End Time:
15:04:00

Total Duration:
7 minutes

Timeout:
No

## Interaction

User Follow-up Count:
0

Search Count:
Unknown / Not fully observable

Material Switch Count:
Unknown / Not fully observable

Repository Search / File Lookup Count:
Unknown / Not fully observable

Tool / Command Count:
Unknown / Not fully observable

## Event Log

| Time | Event Type | Action / Material | Result | Notes |
|---|---|---|---|---|
| 14:57 | Start | Submit Same-task Prompt V1 | Baseline C formally started | Local Codex App project already mounted |
| 14:57–15:04 | Tool / Repository Read | Confirm frozen commit and inspect repository | Frozen commit confirmed; repository materials inspected | Exact command count not fully observable |
| 14:57–15:04 | Web Search | BMVC 2024 FGI paper / official public sources | Official paper located and cross-checked | Exact search count not fully observable |
| 14:57–15:04 | Repository Search | README, dependencies, data/preprocessing, training/testing code, dataset lists | Reproduction blockers, parameter inconsistencies and execution path assessed | Exact material-switch count not fully observable |
| 15:04 | Output | Complete six-field response | Decision = 有条件继续 | User Follow-up = 0 |
| 15:04 | Decision | Baseline C completed | COMPLETED | Formal Decision Time = 7 minutes |

## Cost Notes

明显等待：
None observed

报错：
None observed

人工干预：
None during formal task

其他摩擦：
- Exact internal search/command/file-lookup counts were not fully observable in Codex App.
- Codex App required a local repository project setup before the formal task; this cost is recorded separately below.

## Pre-test Setup Cost

Setup Start Time:
14:50:00

Setup End Time:
14:55:00

Setup Duration:
5 minutes

Setup Actions:
- Clone full FGI repository
- Checkout frozen commit 8c9ea77117878924c29dd87bc5e08a239842ed0f
- Open repository as Codex App project

FGI Material Analysis Before Formal Start:
None

Counting Rule:
Pre-test Setup Cost is recorded separately and is NOT included in Formal Decision Time.

Reporting Note:
For later A/B/C efficiency comparison, report both:
- Formal Decision Time = 7 minutes
- Additional Codex Setup Cost = 5 minutes
Do not silently merge or omit the setup cost.
