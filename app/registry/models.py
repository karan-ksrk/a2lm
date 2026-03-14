from app.models.schemas import ModelInfo
from app.config import get_settings
from app.adapters.base import BaseProviderAdapter


# ── Static model registry (MVP — will move to Postgres in Phase 2) ────────────
# Format: alias → (provider_id, native_model, context_len, weight)

MODELS: list[ModelInfo] = [
    # ── Groq ──────────────────────────────────────────────────────────────────
    ModelInfo(id="llama-8b",        provider_id="groq",
              native_id="llama-3.1-8b-instant",     context_len=131072, weight=100),
    ModelInfo(id="llama-70b",       provider_id="groq",
              native_id="llama-3.3-70b-versatile",  context_len=131072, weight=90),
    ModelInfo(id="kimi-k2",         provider_id="groq",
              native_id="moonshotai/kimi-k2-instruct", context_len=131072, weight=80),
    ModelInfo(id="qwen-32b",        provider_id="groq",
              native_id="qwen/qwen3-32b",            context_len=32768,  weight=80),

    # ── OpenRouter ────────────────────────────────────────────────────────────
    ModelInfo(id="llama-405b",      provider_id="openrouter",
              native_id="meta-llama/llama-3.1-405b-instruct:free", context_len=131072, weight=70),
    ModelInfo(id="deepseek-r1",     provider_id="openrouter",
              native_id="deepseek/deepseek-r1-0528:free",          context_len=65536,  weight=75),
    ModelInfo(id="gemma-27b-or",    provider_id="openrouter",
              native_id="google/gemma-3-27b-it:free",              context_len=8192,   weight=65),

    # ── Google AI Studio ──────────────────────────────────────────────────────
    ModelInfo(id="gemini-flash",    provider_id="google_ai_studio",
              native_id="gemini-2.5-flash", context_len=1048576, weight=85),
    ModelInfo(id="gemma-27b",       provider_id="google_ai_studio",
              native_id="gemma-3-27b-it",   context_len=8192,    weight=80),
    ModelInfo(id="gemma-12b",       provider_id="google_ai_studio",
              native_id="gemma-3-12b-it",   context_len=8192,    weight=75),
    ModelInfo(id="gemma-4b",        provider_id="google_ai_studio",
              native_id="gemma-3-4b-it",    context_len=8192,    weight=70),

    # ── Cerebras ───────────────────────────────────────────────────────────────
    # ModelInfo(id="cerebras-llama-70b", provider_id="cerebras",
    #           native_id="llama-3.3-70b", context_len=131072, weight=95),

    ModelInfo(id="cerebras-llama-8b", provider_id="cerebras",
              native_id="llama3.1-8b", context_len=131072, weight=90),

    ModelInfo(id="cerebras-gpt-oss-120b", provider_id="cerebras",
              native_id="gpt-oss-120b", context_len=131072, weight=100),

    # ModelInfo(id="cerebras-glm-4.7", provider_id="cerebras",
    #           native_id="zai-glm-4.7", context_len=131072, weight=98),

    # ModelInfo(id="cerebras-qwen-235b", provider_id="cerebras",
    #           native_id="qwen-3-235b-a22b-instruct-2507", context_len=131072, weight=96),

    ModelInfo(id="cerebras-qwen-32b", provider_id="cerebras",
              native_id="qwen-3-32b", context_len=131072, weight=92),

    # ── Aliases that span providers ───────────────────────────────────────────
    # "auto" and "fast" and "smart" are resolved by the routing engine
    # based on availability — they don't map to a single model entry

    # ── Cloudflare Workers AI ─────────────────────────────────────────────────────
    ModelInfo(id="cf-llama-70b",   provider_id="cloudflare",
              native_id="@cf/meta/llama-3.3-70b-instruct-fp8-fast", context_len=131072, weight=85),
    ModelInfo(id="cf-llama-8b",    provider_id="cloudflare",
              native_id="@cf/meta/llama-3.2-3b-instruct",           context_len=131072, weight=85),
    ModelInfo(id="cf-qwq-32b",     provider_id="cloudflare",
              native_id="@cf/qwen/qwq-32b",                         context_len=32768,  weight=80),
    ModelInfo(id="cf-deepseek-r1", provider_id="cloudflare",
              native_id="@cf/deepseek-ai/deepseek-r1-distill-qwen-32b", context_len=32768, weight=80),
    ModelInfo(id="cf-gemma-12b",   provider_id="cloudflare",
              native_id="@cf/google/gemma-3-12b-it",                context_len=8192,   weight=75),
    # ModelInfo(id="cf-mistral-7b",  provider_id="cloudflare",
    #           native_id="@cf/mistral/mistral-7b-instruct-v0.2",     context_len=32768,  weight=70),

    # ── Cohere ────────────────────────────────────────────────────────────────────
    ModelInfo(id="command-a",      provider_id="cohere",
              native_id="command-a-03-2025",       context_len=256000, weight=70),
    ModelInfo(id="command-r-plus", provider_id="cohere",
              native_id="command-r-plus-08-2024",  context_len=128000, weight=65),
    ModelInfo(id="command-r",      provider_id="cohere",
              native_id="command-r-08-2024",       context_len=128000, weight=60),
    ModelInfo(id="command-r7b",    provider_id="cohere",
              native_id="command-r7b-12-2024",     context_len=128000, weight=55),
    ModelInfo(id="aya-32b",        provider_id="cohere",
              native_id="c4ai-aya-expanse-32b",    context_len=8192,   weight=55),

    # ── Mistral ───────────────────────────────────────────────────────────────────
    ModelInfo(id="mistral-small",  provider_id="mistral",
              native_id="mistral-small-latest",  context_len=131072, weight=90),
    ModelInfo(id="mistral-large",  provider_id="mistral",
              native_id="mistral-large-latest",  context_len=131072, weight=85),
    ModelInfo(id="mistral-nemo",   provider_id="mistral",
              native_id="open-mistral-nemo",      context_len=131072, weight=80),
    ModelInfo(id="mixtral-8x7b",   provider_id="mistral",
              native_id="open-mixtral-8x7b",      context_len=32768,  weight=80),
    ModelInfo(id="codestral",      provider_id="mistral",
              native_id="codestral-latest",       context_len=262144, weight=85),

    # ── NVIDIA NIM ────────────────────────────────────────────────────────────────
    ModelInfo(id="nvidia-llama-70b",    provider_id="nvidia",
              native_id="meta/llama-3.3-70b-instruct",            context_len=131072, weight=88),
    ModelInfo(id="nvidia-llama-405b",   provider_id="nvidia",
              native_id="meta/llama-3.1-405b-instruct",           context_len=131072, weight=85),
    # ModelInfo(id="nvidia-deepseek-r1",  provider_id="nvidia",
    #           native_id="deepseek-ai/deepseek-r1",                context_len=65536,  weight=88),
    # ModelInfo(id="nvidia-qwen-72b",     provider_id="nvidia",
    #           native_id="qwen/qwen2.5-72b-instruct",              context_len=131072, weight=85),
    ModelInfo(id="nvidia-qwen-coder",   provider_id="nvidia",
              native_id="qwen/qwen2.5-coder-32b-instruct",        context_len=131072, weight=85),
    # ModelInfo(id="nvidia-nemotron-70b", provider_id="nvidia",
    #           native_id="nvidia/llama-3.1-nemotron-70b-instruct", context_len=131072, weight=85),
    ModelInfo(id="nvidia-phi-4-mini",   provider_id="nvidia",
              native_id="microsoft/phi-4-mini-instruct",          context_len=131072, weight=80),
]

# Priority-ordered provider list for generic aliases
ALIAS_PRIORITY = {
    "auto": [
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "llama3.1-8b"),
        ("mistral", "mistral-small-latest"),
        ("nvidia",           "meta/llama-3.3-70b-instruct"),
        ("cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
        ("google_ai_studio", "gemma-3-27b-it"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
        ("cohere", "command-a-03-2025"),
    ],

    "fast": [
        ("groq", "llama-3.1-8b-instant"),
        ("cerebras", "llama3.1-8b"),
        ("mistral",          "mistral-small-latest"),
        ("nvidia",           "meta/llama-3.3-70b-instruct"),
        ("cloudflare", "@cf/meta/llama-3.2-3b-instruct"),
        ("google_ai_studio", "gemma-3-4b-it"),
        ("openrouter", "meta-llama/llama-3.2-3b-instruct:free"),
        ("cohere", "command-r7b-12-2024"),
    ],

    "smart": [
        ("cerebras", "gpt-oss-120b"),
        ("cloudflare", "@cf/qwen/qwq-32b"),
        ("nvidia",           "deepseek-ai/deepseek-r1"),
        ("mistral",          "mistral-large-latest"),
        ("groq", "moonshotai/kimi-k2-instruct"),
        ("openrouter", "meta-llama/llama-3.1-405b-instruct:free"),
        ("google_ai_studio", "gemini-2.5-flash"),
        ("cohere", "command-a-03-2025"),
    ],
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
            {"id": alias, "object": "model", "owned_by": "a2lm", "context_length": 131072}
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
    from app.adapters.cerebras import CerebrasAdapter
    from app.adapters.cloudflare import CloudflareAdapter
    from app.adapters.cohere import CohereAdapter
    from app.adapters.mistral import MistralAdapter
    from app.adapters.nvidia import NvidiaAdapter

    if provider_id == "cloudflare":
        from app.config import get_settings
        account_id = get_settings().cloudflare_account_id
        return CloudflareAdapter(api_key=api_key, account_id=account_id)

    return {
        "groq": GroqAdapter,
        "openrouter": OpenRouterAdapter,
        "google_ai_studio": GoogleAIStudioAdapter,
        "cerebras": CerebrasAdapter,
        "cohere": CohereAdapter,
        "mistral": MistralAdapter,
        "nvidia": NvidiaAdapter,

    }[provider_id](api_key)
