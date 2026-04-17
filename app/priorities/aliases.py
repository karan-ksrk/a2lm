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
        ("openrouter",  "meta-llama/llama-3.3-70b-instruct:free"),
    ],
    "fast": [
        ("groq",        "llama-3.1-8b-instant"),
        ("cerebras",    "llama3.1-8b"),
        ("google",      "gemma-3-4b-it"),
        ("mistral",     "mistral-small-latest"),
    ],
    "smart": [
        ("groq",        "moonshotai/kimi-k2-instruct"),
        ("google",      "gemini-2.5-flash"),
        ("mistral",     "mistral-large-latest"),
        ("openrouter",  "meta-llama/llama-3.1-405b-instruct:free"),
    ],
    "coding": [
        ("mistral",     "codestral-latest"),
        ("groq",        "moonshotai/kimi-k2-instruct"),
        ("google",      "gemini-2.5-flash"),
        ("openrouter",  "deepseek/deepseek-coder-v2-lite-instruct:free"),
    ],
}
