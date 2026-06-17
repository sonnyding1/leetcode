#!/usr/bin/env python3
"""
Log LeetCode problem events to events.yaml when an .md file is saved.

Triggered by nvim BufWritePost autocommand.
No external dependencies — stdlib only.

Usage:
    python3 scripts/log_event.py <path/to/problem.md>
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LEETCODE_DIR = SCRIPT_DIR.parent
STATE_FILE = LEETCODE_DIR / ".state.yaml"
EVENTS_FILE = LEETCODE_DIR / "events.yaml"


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(filepath: str) -> dict | None:
    """Extract YAML frontmatter from a markdown file.

    Returns a dict with keys 'name', 'id', 'difficulty', 'tags' (id and
    difficulty are coerced to int; tags is a list of strings).  Returns
    None if the file is unreadable, has no frontmatter, or is missing
    required fields.
    """
    try:
        text = Path(filepath).read_text()
    except OSError:
        return None

    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None

    fm: dict = {}
    in_list = False
    list_key: str | None = None

    for line in m.group(1).strip().split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Collect items for a multi-line list (e.g. tags:\n  - foo\n  - bar)
        if in_list:
            if line_stripped.startswith("- "):
                item = line_stripped[2:].strip().strip("\"'")
                fm[list_key].append(item)
                continue
            else:
                in_list = False
                list_key = None
                # Fall through to process this line as a regular key:value

        if ":" not in line_stripped:
            continue

        key, _, val = line_stripped.partition(":")
        key = key.strip()
        val = val.strip()

        # Empty value → might be start of a multi-line list
        if not val:
            in_list = True
            list_key = key
            fm[key] = []
            continue

        # Inline YAML list: [item1, item2]
        if val.startswith("[") and val.endswith("]"):
            items = [
                x.strip().strip("\"'")
                for x in val[1:-1].split(",")
                if x.strip()
            ]
            fm[key] = items
            continue

        # Coerce numbers
        try:
            val = int(val)
        except ValueError:
            val = val.strip("\"'")

        fm[key] = val

    if "id" not in fm or "difficulty" not in fm:
        return None

    # Ensure types
    fm["id"] = int(fm["id"])
    fm["difficulty"] = int(fm["difficulty"])
    fm.setdefault("name", "")
    fm.setdefault("tags", [])
    return fm


# ---------------------------------------------------------------------------
# State file (simple key:value format — no YAML parser needed)
# ---------------------------------------------------------------------------

def load_state() -> dict[int, dict]:
    """Load .state.yaml → {id: {difficulty, tags}, ...}.  Empty dict if missing.

    Handles both legacy format ("1: 0") and nested format with tags.
    """
    if not STATE_FILE.exists():
        return {}
    state: dict[int, dict] = {}
    current_id: int | None = None
    for line in STATE_FILE.read_text().splitlines():
        # Detect indentation from raw line (before strip removes whitespace)
        is_indented = line.startswith(" ")
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if not is_indented:
            # Top-level key
            if ":" in line_stripped:
                key_part, _, val_part = line_stripped.partition(":")
                pid = int(key_part.strip())
                val_part = val_part.strip()
                state[pid] = {"difficulty": 0, "tags": []}
                current_id = pid
                if val_part:
                    # Legacy format: "1: 0" — difficulty value on same line
                    try:
                        state[pid]["difficulty"] = int(val_part)
                    except ValueError:
                        pass
        elif current_id is not None and ":" in line_stripped:
            key, _, val = line_stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "difficulty":
                try:
                    state[current_id]["difficulty"] = int(val)
                except ValueError:
                    pass
            elif key == "tags":
                if val.startswith("[") and val.endswith("]"):
                    state[current_id]["tags"] = [
                        t.strip().strip("\"'")
                        for t in val[1:-1].split(",")
                        if t.strip()
                    ]
    return state


def save_state(state: dict[int, dict]) -> None:
    """Write .state.yaml with difficulty and tags per problem, sorted by id."""
    lines = []
    for pid in sorted(state):
        entry = state[pid]
        lines.append("%d:" % pid)
        lines.append("  difficulty: %d" % entry.get("difficulty", 0))
        tags = entry.get("tags", [])
        if tags:
            lines.append("  tags: [%s]" % ", ".join(tags))
    STATE_FILE.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Event logging
# ---------------------------------------------------------------------------

def append_event(event: dict) -> None:
    """Append a single event dict to events.yaml."""
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event["timestamp"] = timestamp

    # Serialise one YAML list item: id, name, difficulty, timestamp
    lines = ["- id: %d" % event["id"]]
    if event.get("name"):
        lines.append('  name: "%s"' % event["name"])
    lines.append("  difficulty: %d" % event["difficulty"])
    lines.append("  timestamp: %s" % timestamp)

    entry = "\n".join(lines) + "\n"

    with open(EVENTS_FILE, "a") as fh:
        fh.write(entry)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: log_event.py <path/to/problem.md>", file=sys.stderr)
        return 1

    filepath = sys.argv[1]

    fm = parse_frontmatter(filepath)
    if fm is None:
        # Not a problem file (e.g. README, template) — silent skip
        return 0

    pid = fm["id"]
    name = fm["name"]
    new_diff = fm["difficulty"]
    tags = fm.get("tags", [])
    state = load_state()

    prev = state.get(pid)

    if prev is None:
        state[pid] = {"difficulty": new_diff, "tags": tags}
        save_state(state)
        append_event({
            "id": pid,
            "name": name,
            "difficulty": new_diff,
        })
        print(f"create: {name} (difficulty {new_diff})")
        return 0

    prev_diff = prev.get("difficulty", -1)

    if prev_diff == new_diff and prev.get("tags") == tags:
        # No change — silent success
        return 0

    # Always sync current state (handles tag-only changes silently)
    state[pid]["difficulty"] = new_diff
    state[pid]["tags"] = tags
    save_state(state)

    if prev_diff != new_diff:
        append_event({
            "id": pid,
            "name": name,
            "difficulty": new_diff,
        })
        print(f"update: {name} ({prev_diff} → {new_diff})")
    return 0


if __name__ == "__main__":
    sys.exit(main())