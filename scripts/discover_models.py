#!/usr/bin/env python3
"""
Model discovery automation for A2LM Gateway.

Discovers new free models from each provider's API, smoke-tests them
with existing API keys, and appends working models to aliases.py.

Usage (from project root):
    python scripts/discover_models.py [--dry-run] [--providers groq,mistral] [--skip-test] [--alias auto]
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys

# Project root on path so `app.*` imports work without PYTHONPATH
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import httpx

from app.config import get_settings
from app.providers.groq import GroqProvider
from app.providers.cerebras import CerebrasProvider
from app.providers.google import GoogleProvider
from app.providers.mistral import MistralProvider
from app.providers.openrouter import OpenRouterProvider
from app.providers.cohere import CohereProvider
from app.providers.nvidia import NvidiaProvider
from app.providers.cloudflare import CloudflareProvider

from scripts.lib.fetchers import (
    fetch_groq, fetch_cerebras, fetch_google, fetch_mistral,
    fetch_openrouter, fetch_cohere, fetch_nvidia, fetch_cloudflare,
    DiscoveredModel,
)
from scripts.lib.tester import test_model
from scripts.lib.classifier import classify_model
from scripts.lib.aliases_writer import load_existing, write_additions, ALIASES_PATH


def build_providers(settings) -> dict:
    p = {}
    if settings.groq_api_key:
        p["groq"] = GroqProvider(settings.groq_api_key)
    if settings.cerebras_api_key:
        p["cerebras"] = CerebrasProvider(settings.cerebras_api_key)
    if settings.google_ai_studio_api_key:
        p["google"] = GoogleProvider(settings.google_ai_studio_api_key)
    if settings.mistral_api_key:
        p["mistral"] = MistralProvider(settings.mistral_api_key)
    if settings.openrouter_api_key:
        p["openrouter"] = OpenRouterProvider(settings.openrouter_api_key)
    if settings.cohere_api_key:
        p["cohere"] = CohereProvider(settings.cohere_api_key)
    if settings.nvidia_api_key:
        p["nvidia"] = NvidiaProvider(settings.nvidia_api_key)
    if settings.cloudflare_api_key and settings.cloudflare_account_id:
        p["cloudflare"] = CloudflareProvider(settings.cloudflare_api_key, settings.cloudflare_account_id)
    return p


async def run(args: argparse.Namespace) -> None:
    settings = get_settings()
    providers = build_providers(settings)

    if not providers:
        print("ERROR: No providers configured. Set at least one API key in .env")
        return

    wanted = set(args.providers.split(",")) if args.providers else set(providers.keys())
    providers = {k: v for k, v in providers.items() if k in wanted}

    print(f"\n=== Phase 1: Config ===")
    print(f"Active providers: {list(providers)}")

    existing = load_existing()
    existing_flat: set[tuple[str, str]] = set()
    for entries in existing.values():
        existing_flat.update(entries)

    # --- Phase 2: Discover ---
    print(f"\n=== Phase 2: Discover ===")
    fetch_client = httpx.AsyncClient(timeout=20.0)
    tasks = []
    if "groq" in providers:
        tasks.append(fetch_groq(settings.groq_api_key, fetch_client))
    if "cerebras" in providers:
        tasks.append(fetch_cerebras(settings.cerebras_api_key, fetch_client))
    if "google" in providers:
        tasks.append(fetch_google(settings.google_ai_studio_api_key, fetch_client))
    if "mistral" in providers:
        tasks.append(fetch_mistral(settings.mistral_api_key, fetch_client))
    if "openrouter" in providers:
        tasks.append(fetch_openrouter(settings.openrouter_api_key, fetch_client))
    if "cohere" in providers:
        tasks.append(fetch_cohere(settings.cohere_api_key, fetch_client))
    if "nvidia" in providers:
        tasks.append(fetch_nvidia(settings.nvidia_api_key, fetch_client))
    if "cloudflare" in providers:
        tasks.append(fetch_cloudflare(settings.cloudflare_api_key, settings.cloudflare_account_id, fetch_client))

    results: list[list[DiscoveredModel]] = await asyncio.gather(*tasks)
    await fetch_client.aclose()

    all_discovered: list[DiscoveredModel] = []
    for batch in results:
        all_discovered.extend(batch)

    for pname in providers:
        count = sum(1 for m in all_discovered if m.provider == pname)
        print(f"  {pname}: {count} models discovered")

    # --- Phase 3: Filter ---
    print(f"\n=== Phase 3: Filter ===")
    new_models = [
        m for m in all_discovered
        if (m.provider, m.model_id) not in existing_flat
    ]
    known_count = len(all_discovered) - len(new_models)
    print(f"  {len(all_discovered)} total | {known_count} already in aliases.py | {len(new_models)} new to test")

    if not new_models:
        print("Nothing new found. All discovered models already in aliases.py.")
        _close_providers(providers)
        return

    # --- Phase 4: Test ---
    passing: list[DiscoveredModel] = []
    if args.skip_test:
        print(f"\n=== Phase 4: Test (SKIPPED) ===")
        passing = new_models
        for m in new_models:
            print(f"  [{m.provider}] {m.model_id}  (not tested)")
    else:
        print(f"\n=== Phase 4: Test ({len(new_models)} models) ===")
        counts = {"pass": 0, "fail": 0, "skip": 0}
        for m in new_models:
            provider = providers.get(m.provider)
            if not provider:
                continue
            result = await test_model(provider, m.model_id)
            if result.passed:
                counts["pass"] += 1
                passing.append(m)
                snippet = (result.snippet or "").encode("ascii", errors="replace").decode("ascii")
                print(f"  [{m.provider}] {m.model_id}  PASS  \"{snippet}\"")
            elif result.skipped:
                counts["skip"] += 1
                print(f"  [{m.provider}] {m.model_id}  SKIPPED ({result.error})")
            else:
                counts["fail"] += 1
                print(f"  [{m.provider}] {m.model_id}  FAIL  {result.error}")
        print(f"\n  Results: {counts['pass']} pass / {counts['fail']} fail / {counts['skip']} skipped")

    # --- Phase 5: Classify ---
    print(f"\n=== Phase 5: Classify ===")
    additions: dict[str, list[tuple[str, str]]] = {}
    for m in passing:
        alias = args.alias if args.alias else classify_model(m.model_id)
        print(f"  {m.provider}/{m.model_id}  ->  {alias}")
        additions.setdefault(alias, []).append((m.provider, m.model_id))

    # --- Phase 6: Write ---
    print(f"\n=== Phase 6: Write ===")
    if args.output:
        _write_candidates_file(additions, args.output)
    else:
        write_additions(additions, path=ALIASES_PATH, dry_run=args.dry_run)

    for p in providers.values():
        await p.close()


def _write_candidates_file(additions: dict[str, list[tuple[str, str]]], path: str) -> None:
    lines = ["# Discovered model candidates — copy entries into app/priorities/aliases.py\n\n"]
    lines.append("NEW_MODELS: dict[str, list[tuple[str, str]]] = {\n")
    for alias, entries in sorted(additions.items()):
        lines.append(f'    "{alias}": [\n')
        for provider, model_id in entries:
            pad = " " * max(1, 14 - len(provider))
            lines.append(f'        ("{provider}",{pad}"{model_id}"),\n')
        lines.append("    ],\n")
    lines.append("}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Candidates written to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover and integrate new LLM models into aliases.py")
    parser.add_argument("--dry-run", action="store_true", help="Show diff but do not write to aliases.py")
    parser.add_argument("--providers", default="", help="Comma-separated list of providers to run (default: all)")
    parser.add_argument("--skip-test", action="store_true", help="Skip live completion test — just report discoveries")
    parser.add_argument("--alias", default="", help="Force all new models into this alias instead of auto-classifying")
    parser.add_argument("--output", default="", metavar="FILE", help="Write passing models to FILE instead of patching aliases.py")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
