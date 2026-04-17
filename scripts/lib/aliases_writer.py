from __future__ import annotations
import difflib
import re
import sys
import os

# Ensure project root on path so app.priorities is importable
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ALIASES_PATH = os.path.join(_ROOT, "app", "priorities", "aliases.py")


def load_existing() -> dict[str, set[tuple[str, str]]]:
    from app.priorities.aliases import PRIORITIES
    return {alias: set(entries) for alias, entries in PRIORITIES.items()}


def _pad_provider(provider: str) -> str:
    pad = max(0, 14 - len(provider))
    return provider + (" " * pad)


def write_additions(
    additions: dict[str, list[tuple[str, str]]],
    path: str = ALIASES_PATH,
    dry_run: bool = False,
) -> bool:
    if not additions:
        print("Nothing new to add.")
        return False

    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    lines = original.splitlines(keepends=True)
    # Work from bottom to top so line indices stay valid after insertions.
    # For each alias, find the closing `],` line of that alias block.
    alias_close: dict[str, int] = {}
    current_alias: str | None = None
    depth = 0
    for i, line in enumerate(lines):
        m = re.match(r'\s+"(\w+)":\s*\[', line)
        if m:
            current_alias = m.group(1)
            depth = 1
            continue
        if current_alias:
            depth += line.count("[") - line.count("]")
            if depth <= 0:
                alias_close[current_alias] = i
                current_alias = None
                depth = 0

    # Build insertion map: line_index -> list of lines to insert before it
    insert_before: dict[int, list[str]] = {}
    for alias, entries in additions.items():
        close_idx = alias_close.get(alias)
        if close_idx is None:
            print(f"  WARNING: could not find closing bracket for alias '{alias}', skipping")
            continue
        insert_lines = []
        for provider, model_id in entries:
            insert_lines.append(f'        ("{provider}",{" " * max(1, 14-len(provider))}"{model_id}"),\n')
        insert_before[close_idx] = insert_before.get(close_idx, []) + insert_lines

    if not insert_before:
        print("Nothing could be located for insertion.")
        return False

    # Apply insertions in reverse order
    new_lines = list(lines)
    for idx in sorted(insert_before.keys(), reverse=True):
        for ins_line in reversed(insert_before[idx]):
            new_lines.insert(idx, ins_line)

    new_content = "".join(new_lines)

    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile="aliases.py (before)",
        tofile="aliases.py (after)",
    ))
    if diff:
        print("".join(diff))
    else:
        print("No diff generated — entries may already exist.")
        return False

    if dry_run:
        print("\n[DRY RUN] No changes written.")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"\nWritten to {path}")
    return True
