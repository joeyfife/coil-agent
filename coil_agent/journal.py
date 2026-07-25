"""Append-only run journal: what the board said, what we proposed, what happened.

Kept honestly — a skipped day because the regime said stand down is recorded as such, not
omitted. If you ever publish results from this harness, publish this file with them.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

PATH = os.environ.get("COIL_JOURNAL", "coil_agent_journal.jsonl")


def record(entry: dict) -> None:
    entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}
    with open(PATH, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")


def load() -> list:
    if not os.path.exists(PATH):
        return []
    out = []
    with open(PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
