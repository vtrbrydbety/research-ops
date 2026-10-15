"""公开外部模型资产入口核验测试。"""

import httpx

from researchops.services import PublicExternalAssetProbe

CHECKPOINT_URL = "https://drive.google.com/drive/folders/checkpoint-example"


def test_probe_reuses_system_proxy_when_no_explicit_proxy_is_configured(monkeypatch) -> None:
    """No explicit ResearchOps proxy must not force an unreachable direct connection."""

    for name in (
        "RESEARCHOPS_EXTERNAL_ASSET_HTTPS_PROXY",
        "RESEARCHOPS_LLM_HTTPS_PROXY",
        "RESEARCHOPS_HTTPS_PROXY",
    ):
        monkeypatch.delenv(name, raising=False)

    captured: dict[str, object] = {}
    real_client = httpx.Client

    def recording_client(**kwargs):
        captured.update(kwargs)
        return real_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request))
        )

    monkeypatch.setattr(httpx, "Client", recording_client)
    probe = PublicExternalAssetProbe()
    try:
        assert captured["trust_env"] is True
        assert captured["proxy"] is None
    finally:
        probe.close()


def test_public_drive_folder_is_accessible() -> None:
    """无需登录且没有权限提示的 Drive 页面可作为正向可访问证据。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            text="<html><title>checkpoint folder - Google Drive</title></html>",
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    result = PublicExternalAssetProbe(client=client).probe(CHECKPOINT_URL)

    assert result.accessible is True
    assert result.final_url == CHECKPOINT_URL


def test_localized_named_drive_folder_is_accessible() -> None:
    """Drive 品牌被本地化时，不得因缺少英文 Google Drive 文案而误判。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            text="<html><title>checkpoint folder - Google 云端硬盘</title></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PublicExternalAssetProbe(client=client).probe(CHECKPOINT_URL)

    assert result.accessible is True
    assert result.verification_state == "verified_public"


def test_drive_folder_requiring_access_is_not_confirmed() -> None:
    """显示 Request access 的页面不能支持 RD-03 Ready。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request, text="You need access. Request access")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PublicExternalAssetProbe(client=client).probe(CHECKPOINT_URL)

    assert result.accessible is False
    assert "access approval" in result.detail


def test_external_asset_probe_rejects_unapproved_hosts() -> None:
    """README 中的任意 URL 不能绕过外部访问 allowlist。"""

    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: (_ for _ in ()).throw(AssertionError("network should not be called"))
        )
    )
    result = PublicExternalAssetProbe(client=client).probe("https://example.org/private/checkpoint")

    assert result.accessible is False
    assert "allowlist" in result.detail


def test_official_github_release_redirect_is_a_public_checkpoint_probe() -> None:
    """The executor policy, not this probe, determines whether a release is official."""

    release_url = "https://github.com/example/project/releases/download/v1/model.pt"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "github.com":
            return httpx.Response(
                302,
                request=request,
                headers={"location": "https://objects.githubusercontent.com/release/model.pt"},
            )
        return httpx.Response(200, request=request, content=b"checkpoint-bytes")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    result = PublicExternalAssetProbe(client=client).probe(release_url)

    assert result.accessible is True
    assert result.verification_state == "verified_public"
    assert result.final_url == "https://objects.githubusercontent.com/release/model.pt"


def test_generic_drive_success_page_does_not_confirm_checkpoint_identity() -> None:
    """任意 Drive 200 页面不能被提升为 RD-03 的正向资产证据。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            text="<html><title>Google Drive</title><body>Welcome</body></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PublicExternalAssetProbe(client=client).probe(CHECKPOINT_URL)

    assert result.accessible is False
    assert "named public folder" in result.detail


def test_drive_redirect_to_different_resource_is_not_confirmed() -> None:
    """重定向到另一个 Drive 对象时不得沿用原 checkpoint 身份。"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("checkpoint-example"):
            return httpx.Response(
                302,
                request=request,
                headers={"location": "https://drive.google.com/drive/folders/other-resource"},
            )
        return httpx.Response(
            200,
            request=request,
            text="<html><title>Other checkpoint - Google Drive</title></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    result = PublicExternalAssetProbe(client=client).probe(CHECKPOINT_URL)

    assert result.accessible is False


def test_drive_redirect_is_blocked_before_requesting_non_allowlisted_host() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.host == "drive.google.com":
            return httpx.Response(
                302,
                request=request,
                headers={"location": "http://127.0.0.1/internal"},
            )
        raise AssertionError("non-allowlisted redirect target must never be requested")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    result = PublicExternalAssetProbe(client=client).probe(CHECKPOINT_URL)

    assert result.accessible is False
    assert requested_hosts == ["drive.google.com"]
    assert "blocked" in result.detail


def test_transient_timeout_is_retried_before_public_result() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(
            200,
            request=request,
            text="<html><title>checkpoint folder - Google Drive</title></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PublicExternalAssetProbe(client=client, max_attempts=3).probe(CHECKPOINT_URL)

    assert calls == 3
    assert result.accessible is True
    assert result.verification_state == "verified_public"


def test_repeated_timeout_is_an_acquisition_failure_not_inaccessibility() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = PublicExternalAssetProbe(client=client, max_attempts=2).probe(CHECKPOINT_URL)

    assert result.accessible is False
    assert result.verification_state == "acquisition_failure"
    assert "after 2 attempts" in result.detail


def test_recent_success_is_reused_from_short_term_cache() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            request=request,
            text="<html><title>checkpoint folder - Google Drive</title></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    probe = PublicExternalAssetProbe(client=client, cache_ttl_seconds=300)

    first = probe.probe(CHECKPOINT_URL)
    second = probe.probe(CHECKPOINT_URL)

    assert first.accessible is True
    assert second.accessible is True
    assert calls == 1
    assert "cache" in second.detail


def test_asset_probe_reuses_the_explicit_model_proxy_configuration(monkeypatch) -> None:
    monkeypatch.delenv("RESEARCHOPS_EXTERNAL_ASSET_HTTPS_PROXY", raising=False)
    monkeypatch.delenv("RESEARCHOPS_HTTPS_PROXY", raising=False)
    monkeypatch.setenv("RESEARCHOPS_LLM_HTTPS_PROXY", "http://127.0.0.1:7897")

    probe = PublicExternalAssetProbe(
        client=httpx.Client(transport=httpx.MockTransport(lambda _request: None))
    )

    assert probe.proxy_configured is True
    assert probe._configured_proxy() == "http://127.0.0.1:7897"
