"""Explicit, bounded live-provider check using synthetic material and temporary state.

Run only when authorized: .venv/bin/python tools/check_live_model.py --run-live
This can incur provider charges. It never uses production invitations/review data.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-live", action="store_true", help="明确启用一次真实模型验收")
    args = parser.parse_args()
    if not args.run_live:
        parser.error("必须显式传入 --run-live")
    from researchops.core.access_context import AccessContext, current_access
    from researchops.core.config import Settings
    from researchops.schemas import EvidenceFindingInput
    from researchops.services import DeepSeekAnalysisModel, LocalEvidenceFindingRuleService
    from researchops.services.access_store import AccessStore
    from researchops.services.execution_control import ExecutionController
    from tests.test_deepseek_live import _synthetic_bundle

    report = {"material": "synthetic", "attempt_limit": 2, "output_token_limit": 1200}
    with tempfile.TemporaryDirectory(prefix="researchops-live-check-") as directory:
        config = Settings(
            deployment_mode="public",
            security_store_dir=Path(directory) / "security",
            assessment_review_store_dir=Path(directory) / "reviews",
            operation_model_attempts=2,
            global_daily_model_attempts=2,
            execution_timeout_seconds=90,
            llm_timeout_seconds=40,
            llm_max_retries=0,
            llm_max_output_tokens=1200,
        )
        if not config.llm_api_key or not config.llm_api_key.get_secret_value().strip():
            report.update(status="not_run", reason="model_key_missing", attempts=0)
            print(json.dumps(report))
            return 1
        store = AccessStore(config)
        principal, _ = store.create_invitation("isolated-live-check", limit=1)
        executor = ExecutionController(store)
        marker = current_access.set(AccessContext(principal, store))
        try:
            bundle = _synthetic_bundle()
            context = EvidenceFindingInput(
                bundle=bundle,
                focus={"scope_refs": ["RD-02"]},
                condition_contexts=[
                    {"condition_ref": "rd02.software_requirements", "primary_dimension": "RD-02"}
                ],
                relevant_source_ids=["synthetic-readme"],
            )
            invocation = executor.run(
                lambda: DeepSeekAnalysisModel(config).draft_evidence_findings(context)
            )
            outcome = LocalEvidenceFindingRuleService().adjudicate(context, invocation.result)
            if not outcome.candidate_adjudication.admitted_evidence_candidate_ids:
                raise ValueError("Live result has no source-validated Evidence")
            report.update(
                status="passed",
                tokens=invocation.trace.total_tokens,
                evidence_accepted=len(
                    outcome.candidate_adjudication.admitted_evidence_candidate_ids
                ),
                rule_gate=outcome.readiness.overall_gate,
            )
        except Exception as exc:
            # No raw provider body, prompt, secret or exception text is printed.
            report.update(status="failed", error_type=type(exc).__name__)
        finally:
            current_access.reset(marker)
        with store.transaction() as db:
            rows = db.execute("SELECT attempts,state FROM operations").fetchall()
            report["operations"] = len(rows)
            report["attempts"] = sum(row["attempts"] for row in rows)
            report["terminal_states"] = [row["state"] for row in rows]
            report["counted_operations"] = db.execute(
                "SELECT COALESCE(SUM(count),0) FROM usage WHERE kind='operations' AND principal != '*'"
            ).fetchone()[0]
        assert report["attempts"] <= 2
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
