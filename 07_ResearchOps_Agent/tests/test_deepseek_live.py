"""Explicitly enabled live-provider acceptance test using only synthetic material."""

import asyncio
import os
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from researchops.core.config import Settings
from researchops.schemas import (
    ContextGapFocus,
    EvidenceFindingConditionContext,
    EvidenceFindingInput,
    MaterialBundle,
    MaterialSource,
    ResolvedTarget,
)
from researchops.services import DeepSeekAnalysisModel


def _live_test_is_enabled() -> bool:
    if os.getenv("RESEARCHOPS_RUN_LIVE_LLM_TESTS") != "1":
        return False
    secret = Settings().llm_api_key
    return bool(secret and secret.get_secret_value().strip())


@pytest.mark.skipif(
    not _live_test_is_enabled(),
    reason="requires an explicit live-test switch and a locally configured rotated API key",
)
def test_deepseek_live_returns_contract_valid_context_gap_output() -> None:
    bundle = _synthetic_bundle()

    invocation = asyncio.run(
        DeepSeekAnalysisModel(Settings()).analyze_context_gaps_async(bundle)
    )

    assert invocation.result.analysis_mode == "initial"
    assert invocation.result.focus.scope_refs
    assert invocation.trace.status == "success"
    assert invocation.trace.request_id


@pytest.mark.skipif(
    not _live_test_is_enabled(),
    reason="requires an explicit live-test switch and a locally configured rotated API key",
)
def test_deepseek_live_returns_contract_valid_local_evidence_finding_draft() -> None:
    bundle = _synthetic_bundle()
    context = EvidenceFindingInput(
        bundle=bundle,
        focus=ContextGapFocus(scope_refs=["RD-02"]),
        condition_contexts=[
            EvidenceFindingConditionContext(
                condition_ref="rd02.software_requirements",
                primary_dimension="RD-02",
            )
        ],
        relevant_source_ids=["synthetic-readme"],
    )

    invocation = asyncio.run(
        DeepSeekAnalysisModel(Settings()).draft_evidence_findings_async(context)
    )

    assert invocation.result.evidence_drafts
    assert invocation.result.evidence_drafts[0].source_ref == "synthetic-readme"
    assert invocation.trace.status == "success"
    assert invocation.trace.request_id


def _synthetic_bundle() -> MaterialBundle:
    content = "Synthetic test material: this project explicitly requires Python 3.11."
    return MaterialBundle(
        bundle_id=uuid4(),
        target=ResolvedTarget(
            target_type="repository",
            source_entry="https://github.com/example/synthetic",
            display_name="example/synthetic",
            canonical_id="github:example/synthetic",
            canonical_url="https://github.com/example/synthetic",
            resolution_method="direct_url",
        ),
        assembled_at=datetime.now(UTC),
        sources=[
            MaterialSource(
                source_id="synthetic-readme",
                material_type="README",
                title="Synthetic README",
                source_path="README.md",
                source_url="https://github.com/example/synthetic/blob/main/README.md",
                content=content,
                content_sha256=sha256(content.encode()).hexdigest(),
                access_scope="public",
            )
        ],
    )
