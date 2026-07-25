"""Independently verify Coil's point-in-time archive against its published commitments.

You do not have to take "we did not edit it afterwards" on faith. Coil publishes a sha256
over each day's scores at publish time; this recomputes it from the payload you received.

The canonicalisation is stated so it reproduces in any language: keys sorted recursively,
no whitespace, and a number equal to its integer value written without a decimal point
(40, not 40.0 — the rule that makes Python and JavaScript agree).
"""
from __future__ import annotations

import hashlib
import json


def canonical(obj) -> bytes:
    def norm(x):
        if isinstance(x, bool):
            return x
        if isinstance(x, float) and x == int(x):
            return int(x)
        if isinstance(x, dict):
            return {k: norm(v) for k, v in x.items()}
        if isinstance(x, list):
            return [norm(v) for v in x]
        return x
    return json.dumps(norm(obj), separators=(",", ":"), sort_keys=True).encode()


def digest(payload: dict) -> str:
    """sha256 of an /api/board/asof payload, per the published recipe."""
    return hashlib.sha256(canonical({"date": payload["date"], "names": payload["names"]})).hexdigest()


def check(payload: dict, published_sha256: str) -> bool:
    return digest(payload) == published_sha256
