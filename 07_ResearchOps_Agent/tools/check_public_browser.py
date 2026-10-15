"""Exercise the real public ASGI app in Chromium, without opening a network port.

Run: .venv/bin/python tools/check_public_browser.py
Requires the dev Playwright package and `python -m playwright install chromium`.
Uses temporary stores and controlled model HTTP responses; no paid calls or production credentials.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    with tempfile.TemporaryDirectory(prefix="researchops-browser-") as directory:
        os.environ["RESEARCHOPS_DEPLOYMENT_MODE"] = "public"
        os.environ["RESEARCHOPS_SECURITY_STORE_DIR"] = directory + "/security"
        os.environ["RESEARCHOPS_ASSESSMENT_REVIEW_STORE_DIR"] = directory + "/reviews"
        from fastapi.testclient import TestClient
        from playwright.sync_api import sync_playwright

        from apps.api import main as api
        from researchops.services.assessment_jobs import AssessmentJobService
        from researchops.testing.public_workflow import controlled_workflow

        app, get_access_store = api.app, api.get_access_store
        workflow, provider = controlled_workflow(api.settings)
        api.readiness_workflow_service = workflow
        api.assessment_job_service = AssessmentJobService(workflow)

        origin = "https://researchops-agent.com"
        with TestClient(app, base_url=origin) as client, sync_playwright() as playwright:
            store = get_access_store()
            _, invitation = store.create_invitation("browser-test")
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            errors = []
            malicious_label = '<img src=x onerror="window.xssExecuted=true">'

            def route_request(route):
                request = route.request
                if request.url.endswith("/api/v1/targets/resolve") and "untrusted paper title" in (
                    request.post_data or ""
                ):
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps(
                            {
                                "status": "requires_confirmation",
                                "candidates": [
                                    {
                                        "label": malicious_label,
                                        "description": malicious_label,
                                        "resolved_target": {
                                            "target_type": "repository",
                                            "canonical_id": "test",
                                            "canonical_url": "https://github.com/example/project",
                                        },
                                    }
                                ],
                            }
                        ),
                    )
                    return
                client.cookies.clear()
                headers = {**request.all_headers(), "host": "researchops-agent.com"}
                response = client.request(
                    request.method,
                    request.url,
                    headers=headers,
                    content=request.post_data_buffer,
                    follow_redirects=False,
                )
                route.fulfill(
                    status=response.status_code,
                    headers=dict(response.headers),
                    body=response.content,
                )

            context.route(origin + "/**", route_request)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/mvp/")
            page.wait_for_function("() => document.body.dataset.access === 'locked'")
            assert page.locator("#access-gate").is_visible()
            assert not page.locator(".app-shell").is_visible()
            page.locator("#invitation-code").fill(invitation)
            page.locator("#access-submit").click()
            page.wait_for_function("() => document.body.dataset.access === 'ready'")
            assert page.locator(".app-shell").is_visible()
            assert not page.locator('[data-mode="readonly"]').is_visible()
            assert page.locator('[data-mode="manual"]').get_attribute("class").endswith("active")
            assert page.locator("#invitation-code").input_value() == ""
            cookie = next(item for item in context.cookies() if item["name"].startswith("__Host-"))
            assert cookie["secure"] and cookie["httpOnly"] and cookie["sameSite"] == "Strict"
            assert "__Host-researchops_session" not in page.evaluate("document.cookie")
            assert page.evaluate("localStorage.length") == 0
            assert page.evaluate("typeof window.ResearchOpsAccess.fetch") == "function"
            page.reload()
            page.wait_for_function("() => document.body.dataset.access === 'ready'")
            page.locator('[data-mode="later"]').click()
            page.locator("#target-entry").fill("https://github.com/example/project")
            page.locator("#continue-btn").click()
            page.locator("#identified-continue").click()
            page.locator("#screen-overview.active").wait_for(timeout=15000)
            assert len(provider.calls) == 10
            page.locator("#rd01-view-details").click()
            page.locator("#dimension-feedback-btn").click()
            page.locator('[data-feedback="evidence"]').click()
            page.locator("#feedback-textarea").fill("Access still needs confirmation.")
            page.locator("#feedback-submit").click()
            page.wait_for_function(
                "() => document.getElementById('feedback-success').textContent.includes('recalculated')"
            )
            assert len(provider.calls) == 12
            page.locator("#feedback-close").click()
            if page.locator("#dimension-back-btn").is_visible():
                page.locator("#dimension-back-btn").click()
            page.locator("#final-decision-value").select_option("decline")
            page.locator("#final-decision-rationale").fill("Controlled browser acceptance.")
            page.locator("#final-decision-submit").click()
            page.wait_for_function(
                "() => document.getElementById('final-decision-status').textContent.includes('Decision recorded: decline')"
            )
            assert len(provider.calls) == 12  # Human decisions do not invoke the model.
            with store.transaction() as db:
                operations = db.execute(
                    "SELECT attempts,state FROM operations ORDER BY created"
                ).fetchall()
                assert [(item["attempts"], item["state"]) for item in operations] == [
                    (10, "completed"),
                    (2, "completed"),
                ]
            page.reload()
            page.wait_for_function("() => document.body.dataset.access === 'ready'")
            page.locator('[data-mode="later"]').click()
            page.locator("#target-entry").fill("untrusted paper title")
            page.locator("#continue-btn").click()
            page.locator("#screen-target-confirm.active").wait_for()
            assert page.locator(".candidate-name").first.inner_text() == malicious_label
            assert page.locator(".candidate-name img").count() == 0
            assert not page.evaluate("Boolean(window.xssExecuted)")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.locator("#access-logout").is_visible()
            page.locator("#access-logout").click()
            page.wait_for_function("() => document.body.dataset.access === 'locked'")
            assert not page.locator(".app-shell").is_visible()
            assert not errors, errors
            browser.close()
        print(
            "Browser passed: login/session, full controlled assessment, feedback, final decision, budget ledger, XSS, mobile and logout."
        )


if __name__ == "__main__":
    main()
