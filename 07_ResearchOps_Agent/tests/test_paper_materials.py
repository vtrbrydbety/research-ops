"""Crossref 论文材料采集的有界 HTTP 契约测试。"""

import httpx
import pytest

from researchops.schemas import ResolvedTarget
from researchops.services import (
    ArxivPaperMaterialCollector,
    CrossrefPaperMaterialCollector,
    PaperMaterialCollectionError,
    ProjectPageMaterialCollector,
)


def _target() -> ResolvedTarget:
    return ResolvedTarget(
        target_type="doi",
        source_entry="10.1000/example",
        display_name="10.1000/example",
        canonical_id="doi:10.1000/example",
        canonical_url="https://doi.org/10.1000/example",
        resolution_method="normalized_identifier",
    )


def test_crossref_paper_material_preserves_title_abstract_and_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.crossref.org"
        assert request.url.raw_path == b"/works/10.1000%2Fexample"
        return httpx.Response(
            200,
            request=request,
            json={
                "message": {
                    "title": ["Example Paper"],
                    "publisher": "Example Publisher",
                    "abstract": "<jats:p>Uses a public dataset and pretrained weights.</jats:p>",
                }
            },
        )

    collector = CrossrefPaperMaterialCollector(httpx.Client(transport=httpx.MockTransport(handler)))
    materials = collector.collect(_target())

    assert materials.title == "Example Paper"
    assert materials.abstract == "Uses a public dataset and pretrained weights."
    assert materials.identifier == "doi:10.1000/example"
    assert materials.source_url == "https://doi.org/10.1000/example"


def test_crossref_paper_material_failure_is_explicit() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, request=request, text="unavailable")
        )
    )

    with pytest.raises(PaperMaterialCollectionError):
        CrossrefPaperMaterialCollector(client).collect(_target())


def test_arxiv_material_preserves_requested_identity_and_abstract() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2401.01234v2</id>
        <title>Example arXiv Paper</title>
        <summary>Uses a benchmark dataset and a pretrained checkpoint.</summary>
      </entry>
    </feed>"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "export.arxiv.org"
        assert request.url.params["id_list"] == "2401.01234"
        return httpx.Response(200, request=request, content=xml)

    target = ResolvedTarget(
        target_type="arxiv",
        source_entry="2401.01234",
        display_name="arXiv:2401.01234",
        canonical_id="arxiv:2401.01234",
        canonical_url="https://arxiv.org/abs/2401.01234",
        resolution_method="normalized_identifier",
    )
    collector = ArxivPaperMaterialCollector(httpx.Client(transport=httpx.MockTransport(handler)))
    materials = collector.collect(target)

    assert materials.identifier == "arxiv:2401.01234"
    assert materials.title == "Example arXiv Paper"
    assert materials.abstract == "Uses a benchmark dataset and a pretrained checkpoint."


def test_arxiv_material_retries_a_transient_server_failure() -> None:
    attempts = 0
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>https://arxiv.org/abs/2401.01234v2</id>
        <title>Example arXiv Paper</title>
        <summary>Public abstract.</summary>
      </entry>
    </feed>"""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, request=request, text="temporary failure")
        return httpx.Response(200, request=request, content=xml)

    target = ResolvedTarget(
        target_type="arxiv",
        source_entry="2401.01234",
        display_name="arXiv:2401.01234",
        canonical_id="arxiv:2401.01234",
        canonical_url="https://arxiv.org/abs/2401.01234",
        resolution_method="normalized_identifier",
    )
    collector = ArxivPaperMaterialCollector(
        httpx.Client(transport=httpx.MockTransport(handler)),
        max_attempts=2,
    )

    assert collector.collect(target).title == "Example arXiv Paper"
    assert attempts == 2


def test_project_page_collects_bounded_public_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "researchops.services.paper_materials.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/html; charset=utf-8"},
            text=(
                "<html><title>Example Project</title><body>Public dataset and checkpoint "
                "instructions. <a href='https://github.com/example/repro'>Code</a>"
                "</body></html>"
            ),
        )

    target = ResolvedTarget(
        target_type="project_page",
        source_entry="https://example.org/project",
        display_name="example.org/project",
        canonical_id="project:example.org/project",
        canonical_url="https://example.org/project",
        resolution_method="direct_url",
    )
    collector = ProjectPageMaterialCollector(httpx.Client(transport=httpx.MockTransport(handler)))
    materials = collector.collect(target)

    assert materials.material_type == "Project Page"
    assert materials.title == "Example Project"
    assert "Public dataset and checkpoint instructions" in (materials.abstract or "")
    assert materials.repository_urls == ("https://github.com/example/repro",)


def test_project_page_rejects_private_network_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "researchops.services.paper_materials.socket.getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("127.0.0.1", 80))],
    )
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: (_ for _ in ()).throw(AssertionError("network should not be called"))
        )
    )
    target = ResolvedTarget(
        target_type="project_page",
        source_entry="http://localhost/project",
        display_name="localhost/project",
        canonical_id="project:localhost/project",
        canonical_url="http://localhost/project",
        resolution_method="direct_url",
    )

    with pytest.raises(PaperMaterialCollectionError, match="not a public Internet host"):
        ProjectPageMaterialCollector(client).collect(target)
