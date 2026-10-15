"""Safety and provenance tests for the bounded public Hugging Face connector."""

import httpx
import pytest

from researchops.services.huggingface_materials import (
    HuggingFaceMaterialCollectionError,
    PublicHuggingFaceMaterialCollector,
)


def test_public_model_card_uses_fixed_api_and_preserves_source_identity() -> None:
    observed: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["host"] = request.url.host
        observed["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "id": "org/model",
                "sha": "abc123",
                "private": False,
                "gated": False,
                "tags": ["pytorch"],
                "siblings": [{"rfilename": "model.safetensors"}],
                "cardData": {"license": "apache-2.0"},
            },
        )

    collector = PublicHuggingFaceMaterialCollector(
        client=httpx.Client(
            base_url="https://huggingface.co",
            transport=httpx.MockTransport(handler),
        )
    )
    material = collector.collect("https://huggingface.co/org/model")

    assert observed == {"host": "huggingface.co", "path": "/api/models/org/model"}
    assert material.material_type == "Checkpoint-Release"
    assert material.source_path == ".researchops/huggingface/models/org/model.json"
    assert str(material.source_url) == "https://huggingface.co/org/model"
    assert '"gated": false' in material.content
    assert "model.safetensors" in material.content


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/org/model",
        "https://evil.example/org/model",
        "https://huggingface.co/org/model/resolve/main/model.safetensors",
        "https://huggingface.co/datasets/org/data?download=true",
        "https://token@huggingface.co/org/model",
    ],
)
def test_public_card_rejects_non_card_or_credentialed_urls(url: str) -> None:
    with pytest.raises(HuggingFaceMaterialCollectionError):
        PublicHuggingFaceMaterialCollector.parse_public_card_url(url)


def test_public_dataset_card_uses_dataset_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/datasets/org/data"
        return httpx.Response(200, json={"id": "org/data", "gated": "auto"})

    collector = PublicHuggingFaceMaterialCollector(
        client=httpx.Client(
            base_url="https://huggingface.co",
            transport=httpx.MockTransport(handler),
        )
    )
    material = collector.collect("https://huggingface.co/datasets/org/data")

    assert material.material_type == "Dataset Page"
    assert material.source_path == ".researchops/huggingface/datasets/org/data.json"
