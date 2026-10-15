"""真实书目候选解析的有界 HTTP 契约测试。"""

import httpx

from researchops.schemas import TargetResolutionRequest
from researchops.services import (
    ArxivPaperMetadataSearch,
    CrossrefPaperMetadataSearch,
    TargetResolutionService,
)


def test_crossref_candidates_use_real_doi_identity() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.crossref.org"
        assert request.url.params["rows"] == "2"
        return httpx.Response(
            200,
            request=request,
            json={
                "message": {
                    "items": [
                        {
                            "DOI": "10.1000/primary",
                            "title": ["Fine-grained Inconsistency Learning"],
                            "author": [{"given": "Ada", "family": "Researcher"}],
                            "published-online": {"date-parts": [[2024, 1, 2]]},
                        },
                        {
                            "DOI": "10.1000/related",
                            "title": ["Fine-grained Inconsistency Learning"],
                            "author": [{"given": "Lin", "family": "Reviewer"}],
                            "published-print": {"date-parts": [[2023]]},
                        },
                    ]
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    resolver = TargetResolutionService(CrossrefPaperMetadataSearch(client))

    result = resolver.resolve(
        TargetResolutionRequest(
            target_type="paper_title",
            target_entry="Fine-grained Inconsistency Learning",
        )
    )

    assert result.status == "requires_confirmation"
    assert result.data_mode == "live_metadata"
    assert [candidate.resolved_target.canonical_id for candidate in result.candidates] == [
        "doi:10.1000/primary",
        "doi:10.1000/related",
    ]
    assert result.candidates[0].description == ("Ada Researcher · 2024 · Crossref DOI metadata")


def test_paper_title_does_not_fabricate_candidates_when_metadata_fails() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, request=request, text="unavailable")
        )
    )
    resolver = TargetResolutionService(CrossrefPaperMetadataSearch(client))

    result = resolver.resolve(
        TargetResolutionRequest(target_type="paper_title", target_entry="Unknown paper")
    )

    assert result.status == "unresolved"
    assert result.data_mode == "live_metadata"
    assert result.analysis_state == "acquisition_failure"
    assert result.candidates == []


def test_paper_candidates_are_cached_for_confirmation_round_trip() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            request=request,
            json={
                "message": {
                    "items": [
                        {"DOI": "10.1000/a", "title": ["Paper A"]},
                        {"DOI": "10.1000/b", "title": ["Paper B"]},
                    ]
                }
            },
        )

    resolver = TargetResolutionService(
        CrossrefPaperMetadataSearch(httpx.Client(transport=httpx.MockTransport(handler)))
    )
    request = TargetResolutionRequest(target_type="paper_title", target_entry="Paper")

    first = resolver.resolve(request)
    second = resolver.resolve(request)

    assert calls == 1
    assert first.candidates == second.candidates


def test_empty_crossref_result_is_unresolved_without_technical_failure() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                request=request,
                json={"message": {"items": []}},
            )
        )
    )
    resolver = TargetResolutionService(CrossrefPaperMetadataSearch(client))

    result = resolver.resolve(
        TargetResolutionRequest(target_type="paper_title", target_entry="No matching paper")
    )

    assert result.status == "unresolved"
    assert result.analysis_state is None


def test_crossref_discards_topically_similar_but_wrong_title() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                request=request,
                json={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1000/wrong",
                                "title": ["Fine-Grained Audio-Visual Event Localization"],
                            }
                        ]
                    }
                },
            )
        )
    )
    resolver = TargetResolutionService(CrossrefPaperMetadataSearch(client))

    result = resolver.resolve(
        TargetResolutionRequest(
            target_type="paper_title",
            target_entry="Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies",
        )
    )

    assert result.status == "unresolved"
    assert result.candidates == []


def test_arxiv_title_search_returns_stable_arxiv_identity() -> None:
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2408.06753v3</id>
        <title>Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies</title>
        <published>2024-08-13T17:59:59Z</published>
        <author><name>Marcella Astrid</name></author>
      </entry>
    </feed>"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search_query"] == (
            "ti:detecting AND ti:audio AND ti:visual AND ti:deepfakes AND "
            "ti:fine AND ti:grained AND ti:inconsistencies"
        )
        assert request.url.params["sortBy"] == "relevance"
        return httpx.Response(200, request=request, content=xml)

    resolver = TargetResolutionService(
        ArxivPaperMetadataSearch(httpx.Client(transport=httpx.MockTransport(handler)))
    )
    result = resolver.resolve(
        TargetResolutionRequest(
            target_type="paper_title",
            target_entry="Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies",
        )
    )

    assert result.status == "identified"
    assert result.resolved_target is not None
    assert result.resolved_target.canonical_id == "arxiv:2408.06753"
    assert str(result.resolved_target.canonical_url) == "https://arxiv.org/abs/2408.06753"


def test_arxiv_title_search_retries_a_transient_connection_failure() -> None:
    attempts = 0
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2408.06753v3</id>
        <title>Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies</title>
        <published>2024-08-13T17:59:59Z</published>
      </entry>
    </feed>"""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectTimeout("temporary timeout", request=request)
        return httpx.Response(200, request=request, content=xml)

    search = ArxivPaperMetadataSearch(
        httpx.Client(transport=httpx.MockTransport(handler)),
        max_attempts=2,
    )
    results = search.search("Detecting Audio-Visual Deepfakes with Fine-Grained Inconsistencies")

    assert attempts == 2
    assert results[0].arxiv_id == "2408.06753"
