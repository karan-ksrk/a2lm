from app.models.schemas import ModelInfo
from app.config import get_settings
from app.adapters.base import BaseProviderAdapter


# ── Static model registry (MVP — will move to Postgres in Phase 2) ────────────
# Format: alias → (provider_id, native_model, context_len, weight)

MODELS: list[ModelInfo] = [
    # ── Groq ──────────────────────────────────────────────────────────────────
    ModelInfo(id="llama-8b",        provider_id="groq", native_id="llama-3.1-8b-instant",     context_len=131072, weight=100),
    ModelInfo(id="llama-70b",       provider_id="groq", native_id="llama-3.3-70b-versatile",  context_len=131072, weight=90),
    ModelInfo(id="kimi-k2",         provider_id="groq", native_id="moonshotai/kimi-k2-instruct", context_len=131072, weight=80),
    ModelInfo(id="qwen-32b",        provider_id="groq", native_id="qwen/qwen3-32b",            context_len=32768,  weight=80),

    # ── OpenRouter ────────────────────────────────────────────────────────────
    ModelInfo(id="llama-405b",      provider_id="openrouter", native_id="meta-llama/llama-3.1-405b-instruct:free", context_len=131072, weight=70),
    ModelInfo(id="deepseek-r1",     provider_id="openrouter", native_id="deepseek/deepseek-r1-0528:free",          context_len=65536,  weight=75),
    ModelInfo(id="gemma-27b-or",    provider_id="openrouter", native_id="google/gemma-3-27b-it:free",              context_len=8192,   weight=65),

    # ── Google AI Studio ──────────────────────────────────────────────────────
    ModelInfo(id="gemini-flash",    provider_id="google_ai_studio", native_id="gemini-2.5-flash", context_len=1048576, weight=85),
    ModelInfo(id="gemma-27b",       provider_id="google_ai_studio", native_id="gemma-3-27b-it",   context_len=8192,    weight=80),
    ModelInfo(id="gemma-12b",       provider_id="google_ai_studio", native_id="gemma-3-12b-it",   context_len=8192,    weight=75),
    ModelInfo(id="gemma-4b",        provider_id="google_ai_studio", native_id="gemma-3-4b-it",    context_len=8192,    weight=70),

    # ── Aliases that span providers ───────────────────────────────────────────
    # "auto" and "fast" and "smart" are resolved by the routing engine
    # based on availability — they don't map to a single model entry
]

# Priority-ordered provider list for generic aliases
ALIAS_PRIORITY = {
    "auto":  [("groq", "llama-3.3-70b-versatile"),  ("google_ai_studio", "gemma-3-27b-it"),   ("openrouter", "meta-llama/llama-3.3-70b-instruct:free")],
    "fast":  [("groq", "llama-3.1-8b-instant"),     ("google_ai_studio", "gemma-3-4b-it"),    ("openrouter", "meta-llama/llama-3.2-3b-instruct:free")],
    "smart": [("groq", "moonshotai/kimi-k2-instruct"),("openrouter", "meta-llama/llama-3.1-405b-instruct:free"), ("google_ai_studio", "gemini-2.5-flash")],
}


class ModelRegistry:
    def __init__(self):
        self._models = {m.id: m for m in MODELS}

    def list_models(self) -> list[dict]:
        """Return model list in OpenAI /v1/models format."""
        return [
            {
                "id": m.id,
                "object": "model",
                "owned_by": m.provider_id,
                "context_length": m.context_len,
            }
            for m in self._models.values()
            if m.is_active
        ] + [
            {"id": alias, "object": "model", "owned_by": "omni-llm", "context_length": 131072}
            for alias in ["auto", "fast", "smart"]
        ]

    def get(self, alias: str) -> ModelInfo | None:
        return self._models.get(alias)

    def get_candidates(self, alias: str) -> list[tuple[str, str]]:
        """
        Returns list of (provider_id, native_model) candidates to try in order.
        For known aliases: returns that model's provider pair.
        For generic aliases (auto/fast/smart): returns priority-ordered list.
        """
        if alias in ALIAS_PRIORITY:
            return ALIAS_PRIORITY[alias]
        model = self._models.get(alias)
        if model:
            return [(model.provider_id, model.native_id)]
        # Unknown alias — try as native model on groq first
        return [("groq", alias), ("openrouter", alias)]


def build_adapter(provider_id: str, api_key: str) -> BaseProviderAdapter:
    from app.adapters.groq import GroqAdapter
    from app.adapters.openrouter import OpenRouterAdapter
    from app.adapters.google_ai_studio import GoogleAIStudioAdapter
    return {
        "groq": GroqAdapter,
        "openrouter": OpenRouterAdapter,
        "google_ai_studio": GoogleAIStudioAdapter,
    }[provider_id](api_key)
