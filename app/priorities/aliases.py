# Priority lists for each model alias.
# Each entry: (provider_name, native_model_id)
# Router tries them in order — first success wins.
# To change routing behavior, edit only this file.

PRIORITIES: dict[str, list[tuple[str, str]]] = {
    "auto": [
        ("groq",        "llama-3.3-70b-versatile"),
        ("cerebras",    "llama3.1-8b"),
        ("google",      "gemini-2.5-flash"),
        ("mistral",     "mistral-small-latest"),
        ("cloudflare",  "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
        ("cohere",      "command-a-03-2025"),
        ("openrouter",  "meta-llama/llama-3.3-70b-instruct:free"),
        ("nvidia",      "meta/llama-3.3-70b-instruct"),
    ],
    "fast": [
        ("groq",        "llama-3.1-8b-instant"),
        ("cerebras",    "llama3.1-8b"),
        ("google",      "gemma-3-4b-it"),
        ("mistral",     "mistral-small-latest"),
        ("cloudflare",  "@cf/meta/llama-3.2-3b-instruct"),
        ("cohere",      "command-r7b-12-2024"),
    ],
    "smart": [
        ("groq",        "moonshotai/kimi-k2-instruct"),
        ("google",      "gemini-2.5-flash"),
        ("mistral",     "mistral-large-latest"),
        ("nvidia",      "deepseek-ai/deepseek-r1"),
        ("cloudflare",  "@cf/qwen/qwq-32b"),
        ("cohere",      "command-a-03-2025"),
        ("openrouter",  "meta-llama/llama-3.1-405b-instruct:free"),
    ],
    "coding": [
        ("nvidia",      "qwen/qwen3-coder-480b-a35b-instruct"),
        ("nvidia",      "mistralai/devstral-2-123b-instruct-2512"),
        ("mistral",     "codestral-latest"),
        ("groq",        "moonshotai/kimi-k2-instruct"),
        ("nvidia",      "qwen/qwen2.5-coder-32b-instruct"),
        ("google",      "gemini-2.5-flash"),
        ("cloudflare",  "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"),
        ("openrouter",  "deepseek/deepseek-coder-v2-lite-instruct:free"),
    ],
}
