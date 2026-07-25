"""Read Coil's published board.

Two tiers, same schema, chosen automatically by what you have configured:

  free      no key, no wallet, no account — the full board one market day delayed
  license   COIL_LICENSE_KEY — the live intraday board (recomputed ~5 min in market hours)

(x402 pay-per-read exists too, but through any standard x402 client against the same
endpoints — this harness does not carry a wallet.)

The free tier is the default on purpose. A swing-timeframe agent does not need intraday
data, and you should be able to run this repo end to end before paying anyone anything.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

BASE = os.environ.get("COIL_BASE", "https://coil.trade")

# A tagged User-Agent so Coil can measure how many callers came from this harness. That
# measurement is the whole reason the repo exists (see README: the pre-registered metric),
# and it is a per-request header — not an identifier, not a cookie, nothing stored locally.
UA = f"coil-agent/{__version__} (+https://github.com/joeyfife/coil-agent)"


class BoardError(RuntimeError):
    pass


def _get(path: str, params: dict | None = None) -> dict:
    url = BASE.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    key = os.environ.get("COIL_LICENSE_KEY")
    if key:
        req.add_header("X-License-Key", key)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 402:
            # The paid lane answered with a price. The 402 body carries the free alternatives.
            body = json.loads(e.read().decode() or "{}")
            alt = body.get("alternates") or {}
            raise BoardError(
                f"{path} is a paid endpoint. Free alternatives: "
                f"{alt.get('free_delayed_board') or BASE + '/api/board/free'} "
                f"or the MCP server {alt.get('free_mcp_server') or BASE + '/mcp'}"
            ) from None
        if e.code in (401, 403):
            raise BoardError(
                "COIL_LICENSE_KEY was rejected — check the key on your account page "
                "(https://coil.trade/scanner) or unset it to use the free tier"
            ) from None
        raise BoardError(f"{path} failed: HTTP {e.code}") from None
    except urllib.error.URLError as e:
        # No network / DNS failure must be one readable line, not a 30-line traceback.
        raise BoardError(f"cannot reach {BASE}: {getattr(e, 'reason', e)}") from None


def preview() -> dict:
    """The free preview — identical schema to the paid board, previous day, top-3 per book."""
    return _get("/api/board/agent", {"preview": "1"})


def perf() -> dict:
    """The engine's published record vs SPY/QQQ. Free. May be null — it is omitted, not
    estimated, when the underlying data is unavailable."""
    return _get("/api/perf")


def proof(date: str | None = None) -> dict:
    """The append-only sha256 commitment log over the published archive. Free.

    Use verify_archive() to actually check one rather than taking this on faith."""
    return _get("/api/board/proof", {"date": date} if date else None)


def board(live: bool = False) -> dict:
    """The board. Delayed and free by default; live when a license key is configured.

    Returns the same shape either way, so nothing downstream changes when you upgrade."""
    if live and not os.environ.get("COIL_LICENSE_KEY"):
        raise BoardError("live=True needs COIL_LICENSE_KEY (https://coil.trade/scanner)")
    if os.environ.get("COIL_LICENSE_KEY"):
        return _get("/api/board/agent")
    return _get("/api/board/free")


def buy_candidates(b: dict, book: str = "spx", limit: int = 5) -> list:
    """Ranked candidates for one book, read top-down.

    Returns [] when the regime's permission ladder does not allow names — that is a real
    answer, not an error. An empty list means the board says stand down today.
    """
    books = b.get("books") or {}
    bk = books.get(book) or {}
    # The two tiers carry the ladder at different depths — the paid board nests it under
    # regime.ladder.rung, the free board flattens it to ladder_rung on the book. Read BOTH.
    # Getting this wrong is not a cosmetic bug: the gate silently passed on the free tier,
    # which is the default, so the harness printed "nothing qualifies" and then proposed
    # three buys anyway. If you add a tier, add its shape here and to the tests.
    regime = bk.get("regime") or {}
    ladder = regime.get("ladder") or {}
    rung = ladder.get("rung") or regime.get("ladder_rung") or bk.get("ladder_rung")
    if rung is None:
        # Peer review 2026-07-24: an unrecognized shape used to fall THROUGH the gate and
        # propose buys — the exact bug class that already shipped once (the free tier's flat
        # ladder_rung). A gate that cannot read its input is CLOSED, not open: no rung, no
        # candidates. If a new tier adds a new shape, add it above and to the tests.
        return []
    if rung == "CASH":
        return []

    names = b.get("names") or []
    if names:
        pool = [n for n in names
                if (book in n.get("bk", []) if isinstance(n.get("bk"), list) else n.get("bk") == book)
                and n.get("kind") != "index"]
        pool.sort(key=lambda n: n.get("opp_pct") or n.get("opp") or 0, reverse=True)
        return pool[:limit]
    # free tier carries a top-3 teaser per book instead of the full name list
    return (bk.get("top3") or [])[:limit]


def regime_line(b: dict, book: str = "spx") -> str:
    bk = (b.get("books") or {}).get(book) or {}
    r = bk.get("regime") or {}
    return r.get("verdict") or bk.get("regime_verdict") or "(no verdict published)"
