"""Generate app/ai/chat_models.json from chat_models.yaml next to this script and models.dev.

Run from the backend root:

    PYTHONPATH=. python scripts/python/generate_chat_models.py          # rewrite the JSON
    PYTHONPATH=. python scripts/python/generate_chat_models.py --check  # exit 1 if stale
"""

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.ai.schemas import ChatModelCatalog, ChatModelSpec
from app.enums import Gateway

MODELS_DEV_URL = "https://models.dev/api.json"
INPUT_PATH = Path(__file__).with_name("chat_models.yaml")
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "app" / "ai" / "chat_models.json"


class PriceOverrides(BaseModel):
    """For models models.dev lacks or gets wrong; USD per 1M tokens, limits in tokens."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_price: float | None = None
    cached_input_price: float | None = None
    output_price: float | None = None
    context_limit: int | None = None
    output_limit: int | None = None


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(pattern=r"^[^/]+/.+$")
    slug: str | None = None
    label: str | None = None
    no_sampling: bool = False
    overrides: PriceOverrides | None = None


_entries_adapter = TypeAdapter(list[str | CatalogEntry])


def load_entries(path: Path = INPUT_PATH) -> list[CatalogEntry]:
    raw = _entries_adapter.validate_python(yaml.safe_load(path.read_text(encoding="utf-8")))
    return [CatalogEntry(source=entry) if isinstance(entry, str) else entry for entry in raw]


def fetch_models_dev() -> dict[str, Any]:
    response = httpx.get(MODELS_DEV_URL, headers={"User-Agent": "model-catalog"}, timeout=30)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    return payload


def build_catalog(entries: list[CatalogEntry], api: dict[str, Any]) -> ChatModelCatalog:
    return ChatModelCatalog(models=[_build_spec(entry, api) for entry in entries])


def _build_spec(entry: CatalogEntry, api: dict[str, Any]) -> ChatModelSpec:
    host, model_id = entry.source.split("/", 1)
    found = api.get(host, {}).get("models", {}).get(model_id)
    if found is None and (entry.overrides is None or entry.label is None):
        raise ValueError(f"{entry.source} is not on models.dev; give it a label and overrides")
    found = found or {}
    cost = found.get("cost", {})
    limit = found.get("limit", {})

    facts = {
        "input_price": cost.get("input"),
        "cached_input_price": cost.get("cache_read"),
        "output_price": cost.get("output"),
        "context_limit": limit.get("context"),
        "output_limit": limit.get("output"),
    }
    if entry.overrides is not None:
        facts |= entry.overrides.model_dump(exclude_none=True)

    return ChatModelSpec.model_validate(
        {
            "slug": entry.slug or model_id.rsplit("/", 1)[-1],
            "label": entry.label or found["name"],
            "provider": _provider(host, model_id),
            "gateway": _gateway(host, model_id),
            # The models.dev id is what each SDK expects: Gemini's bare id, Claude's bare
            # alias, and Grok's "xai/" publisher prefix for Vertex's OpenAI-compatible endpoint.
            "provider_model": model_id,
            "no_sampling": entry.no_sampling,
            **facts,
        }
    )


def _provider(host: str, model_id: str) -> str:
    if "/" in model_id:
        return model_id.split("/", 1)[0]
    return "google" if host == "google-vertex" else host


def _gateway(host: str, model_id: str) -> Gateway:
    if host == "google-vertex":
        return Gateway.vertex_maas if "/" in model_id else Gateway.google
    return Gateway(host)


def render(catalog: ChatModelCatalog) -> str:
    return json.dumps(catalog.model_dump(mode="json", exclude_none=True), indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report drift instead of rewriting")
    args = parser.parse_args(argv)

    fresh = render(build_catalog(load_entries(), fetch_models_dev()))
    if not args.check:
        OUTPUT_PATH.write_text(fresh, encoding="utf-8")
        return 0

    committed = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    diff = list(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            fresh.splitlines(keepends=True),
            "committed",
            "generated",
        )
    )
    if not diff:
        print("app/ai/chat_models.json is up to date")
        return 0
    sys.stdout.writelines(diff)
    return 1


if __name__ == "__main__":
    sys.exit(main())
