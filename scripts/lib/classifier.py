from __future__ import annotations
import re

# Checked in order — first match wins. "auto" is the fallback.
# Keywords matched against individual tokens (split on [-/._:]) to avoid
# substring false-positives (e.g. "gemini" containing "mini").
_RULES: list[tuple[str, list[str]]] = [
    ("coding", ["code", "coder", "codestral", "starcoder", "devstral"]),
    ("fast",   ["instant", "mini", "tiny", "flash", "turbo", "small", "3b", "1b", "2b", "4b", "7b", "8b"]),
    ("smart",  ["large", "70b", "72b", "90b", "405b", "r1", "think", "reasoning", "kimi", "qwq", "opus", "ultra", "pro"]),
]


def _tokens(model_id: str) -> set[str]:
    return set(re.split(r"[-/._: ]+", model_id.lower()))


def classify_model(model_id: str) -> str:
    tokens = _tokens(model_id)
    for alias, keywords in _RULES:
        if tokens & set(keywords):
            return alias
    return "auto"
