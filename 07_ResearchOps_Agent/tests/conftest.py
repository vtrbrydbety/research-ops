"""Existing domain/API contracts use explicit isolated local-development mode."""

import os
import tempfile

_runtime = tempfile.TemporaryDirectory(prefix="researchops-tests-")
os.environ["RESEARCHOPS_DEPLOYMENT_MODE"] = "local"
os.environ["RESEARCHOPS_ASSESSMENT_REVIEW_STORE_DIR"] = _runtime.name + "/reviews"
# Ordinary regression tests must never pick up a paid API key from the project's .env.
# Explicit live tests can supply a key in the process environment themselves.
os.environ.setdefault("RESEARCHOPS_LLM_API_KEY", "")
