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

    Returns a dict with keys 'name', 'id', 'difficulty' (id and difficulty
    are coerced to int).  Returns None if the file is unreadable, has no
    frontmatter, or is missing required fields.
    """
    try:
        text = Path(filepath).read_text()
    except OSError:
        return None

    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None

    fm: dict = {}
    for line in m.group(1).strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip("\"'")

        # Coerce numbers
        try:
            val = int(val)
        except ValueError:
            pass

        fm[key] = val

    if "id" not in fm or "difficulty" not in fm:
        return None

    # Ensure types
    fm["id"] = int(fm["id"])
    fm["difficulty"] = int(fm["difficulty"])
    fm.setdefault("name", "")
    return fm


# ---------------------------------------------------------------------------
# State file (simple key:value format — no YAML parser needed)
# ---------------------------------------------------------------------------

def load_state() -> dict[int, int]:
    """Load .state.yaml → {id: difficulty, ...}.  Empty dict if missing."""
    if not STATE_FILE.exists():
        return {}
    state: dict[int, int] = {}
    for line in STATE_FILE.read_text().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        try:
            state[int(key.strip())] = int(val.strip())
        except ValueError:
            continue
    return state


def save_state(state: dict[int, int]) -> None:
    """Write .state.yaml as 'id: difficulty' lines, sorted by id."""
    lines = [f"{pid}: {diff}" for pid, diff in sorted(state.items())]
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
    state = load_state()

    prev_diff = state.get(pid)

    if prev_diff is None:
        state[pid] = new_diff
        save_state(state)
        append_event({
            "id": pid,
            "name": name,
            "difficulty": new_diff,
        })
        print(f"create: {name} (difficulty {new_diff})")
        return 0

    if prev_diff == new_diff:
        # No change — silent success
        return 0

    state[pid] = new_diff
    save_state(state)
    append_event({
        "id": pid,
        "name": name,
        "difficulty": new_diff,
    })
    print(f"update: {name} ({prev_diff} → {new_diff})")
    return 0


if __name__ == "__main__":
    sys.exit(main())