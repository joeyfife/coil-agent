"""Apify Actor entry point — publish Coil's scored board as a dataset.

Deliberately dependency-free: it talks to the Apify REST API with urllib, using the
environment Apify injects into every run. That keeps the image small, keeps the repo's
stdlib-only promise, and means this exact file also runs on a laptop with no Apify at all
(it just prints the rows instead of pushing them).

    python3 -m actor_main            # local: prints rows as JSON lines
    (on Apify)                       # pushes rows to the run's default dataset

Reads only. This Actor fetches and publishes scores; it places no orders and holds no keys
beyond an optional Coil Scanner license the operator supplies as a secret input.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from coil_agent import board

API = "https://api.apify.com/v2"
TOKEN = os.environ.get("APIFY_TOKEN")
DATASET = os.environ.get("APIFY_DEFAULT_DATASET_ID")
KV_STORE = os.environ.get("APIFY_DEFAULT_KEY_VALUE_STORE_ID")
ON_APIFY = bool(TOKEN and DATASET)

BOOKS = ["spx", "qqq", "macro", "crypto"]


def _api(path: str, method: str = "GET", payload=None):
    req = urllib.request.Request(
        f"{API}{path}?token={TOKEN}", method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def get_input() -> dict:
    """The run's INPUT record. Absent locally, and absent on a run with no input — both fine."""
    if not (ON_APIFY and KV_STORE):
        return {}
    try:
        return _api(f"/key-value-stores/{KV_STORE}/records/INPUT") or {}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise


def push(rows: list) -> None:
    if not rows:
        return
    if ON_APIFY:
        _api(f"/datasets/{DATASET}/items", "POST", rows)
    else:
        for r in rows:
            print(json.dumps(r, separators=(",", ":")))


def rows_for(b: dict, books: list, include_regime: bool) -> list:
    """Flatten the board into dataset rows: optionally one regime row per book, then names."""
    asof = b.get("asof") or b.get("asof_daily")
    delayed = bool(b.get("delayed"))
    out = []
    for key in books:
        bk = (b.get("books") or {}).get(key)
        if not bk:
            continue
        if include_regime:
            r = bk.get("regime") or {}
            ladder = (r.get("ladder") or {})
            out.append({
                "row_type": "regime",
                "book": key,
                "asof": asof,
                "delayed": delayed,
                "regime_mode": r.get("mode") or bk.get("regime_mode"),
                "verdict": r.get("verdict") or bk.get("regime_verdict"),
                "ladder_rung": ladder.get("rung") or bk.get("ladder_rung"),
                "green_sectors": r.get("green_sectors"),
            })
        # Full board (licensed/paid shapes) carries names[]; the free tier carries top3 per book.
        names = [n for n in (b.get("names") or [])
                 if (key in n.get("bk", []) if isinstance(n.get("bk"), list) else n.get("bk") == key)
                 and n.get("kind") != "index"] or (bk.get("top3") or [])
        for n in names:
            out.append({
                "row_type": "name",
                "book": key,
                "asof": asof,
                "delayed": delayed,
                "sym": n.get("sym"),
                "name": n.get("name"),
                "sector": n.get("sector"),
                "opp": n.get("opp_pct", n.get("opp")),
                "entry_q": n.get("entry_q"),
                "hold_q": n.get("hold_q"),
                "state": n.get("state"),
                "is_leader": n.get("is_leader"),
            })
    return out


def main() -> int:
    inp = get_input()
    book = (inp.get("book") or "all").lower()
    books = BOOKS if book == "all" else [book]
    include_regime = inp.get("includeRegime", True)
    include_record = inp.get("includeRecord", False)

    lic = (inp.get("licenseKey") or "").strip()
    if lic:
        os.environ["COIL_LICENSE_KEY"] = lic     # board._get attaches it as X-License-Key

    try:
        b = board.board()
    except board.BoardError as e:
        print(f"could not read the board: {e}", file=sys.stderr)
        return 1

    rows = rows_for(b, books, include_regime)

    if include_record:
        try:
            p = board.perf()
            h = (p.get("perf") or {}).get("headline") or {}
            rows.append({
                "row_type": "record",
                "asof": asof_of(p) or b.get("asof"),
                "engine_return_pct": h.get("engine_return_pct"),
                "spy_return_pct": h.get("spy_return_pct"),
                "qqq_return_pct": h.get("qqq_return_pct"),
                "note": (p.get("perf") or {}).get("note"),
                "proof": p.get("proof"),
            })
        except board.BoardError:
            pass   # the record is a bonus; never fail the run over it

    push(rows)
    print(f"pushed {len(rows)} rows"
          f" ({'live' if not b.get('delayed') else 'delayed'} board, book={book})")
    return 0


def asof_of(p: dict):
    return (p or {}).get("board_computed_at")


if __name__ == "__main__":
    raise SystemExit(main())
