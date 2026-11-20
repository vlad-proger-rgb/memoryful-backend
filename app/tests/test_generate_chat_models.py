from pathlib import Path
from typing import Any

import pytest

from app.enums import Gateway, Provider
from scripts.python import generate_chat_models as generator
from scripts.python.generate_chat_models import CatalogEntry, PriceOverrides, build_catalog


def _models_dev(
    host: str, model_id: str, name: str = "Model", input_price: float = 1.0
) -> dict[str, Any]:
    entry = {
        "name": name,
        "cost": {"input": input_price, "output": 2.0, "cache_read": 0.1},
        "limit": {"context": 1000, "output": 100},
    }
    return {host: {"models": {model_id: entry}}}


def test_the_committed_input_list_loads() -> None:
    assert generator.load_entries()


@pytest.mark.parametrize(
    ("source", "provider", "gateway", "slug"),
    [
        ("google-vertex/gemini-x", Provider.google, Gateway.google, "gemini-x"),
        ("google-vertex/xai/grok-x", Provider.xai, Gateway.vertex_maas, "grok-x"),
        ("anthropic/claude-x", Provider.anthropic, Gateway.anthropic, "claude-x"),
        ("openai/gpt-x", Provider.openai, Gateway.openai, "gpt-x"),
    ],
)
def test_fields_are_derived_from_the_models_dev_key(
    source: str, provider: Provider, gateway: Gateway, slug: str
) -> None:
    host, model_id = source.split("/", 1)

    [spec] = build_catalog([CatalogEntry(source=source)], _models_dev(host, model_id, "X")).models

    assert (spec.provider, spec.gateway, spec.slug) == (provider, gateway, slug)
    assert (spec.provider_model, spec.label) == (model_id, "X")
    assert (spec.input_price, spec.cached_input_price, spec.output_limit) == (1.0, 0.1, 100)


def test_hand_written_fields_win() -> None:
    entry = CatalogEntry(
        source="openai/gpt-x",
        slug="kept-slug",
        label="Kept",
        no_sampling=True,
        overrides=PriceOverrides(output_price=3.0),
    )

    [spec] = build_catalog([entry], _models_dev("openai", "gpt-x")).models

    assert (spec.slug, spec.label, spec.no_sampling) == ("kept-slug", "Kept", True)
    assert (spec.input_price, spec.output_price) == (1.0, 3.0)


def test_a_model_missing_from_models_dev_needs_a_label_and_overrides() -> None:
    with pytest.raises(ValueError, match="openai/gone"):
        build_catalog([CatalogEntry(source="openai/gone")], {})

    entry = CatalogEntry(
        source="openai/gone", label="Gone", overrides=PriceOverrides(input_price=1.0)
    )
    [spec] = build_catalog([entry], {}).models
    assert (spec.label, spec.input_price, spec.output_price) == ("Gone", 1.0, None)


def test_check_reports_drift_from_models_dev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(generator, "OUTPUT_PATH", tmp_path / "chat_models.json")
    monkeypatch.setattr(generator, "load_entries", lambda: [CatalogEntry(source="openai/gpt-x")])
    monkeypatch.setattr(generator, "fetch_models_dev", lambda: _models_dev("openai", "gpt-x"))
    assert generator.main([]) == 0
    assert generator.main(["--check"]) == 0

    monkeypatch.setattr(
        generator, "fetch_models_dev", lambda: _models_dev("openai", "gpt-x", input_price=1.5)
    )
    assert generator.main(["--check"]) == 1
    assert '+      "input_price": 1.5,\n' in capsys.readouterr().out
