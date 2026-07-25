"""Turn board candidates into Alpaca PAPER orders.

Paper by default, and it takes a deliberate environment variable to change that. The
point of this repo is to let you watch a disciplined loop run for a few weeks before any
real money is involved.

WHAT THIS FILE DOES NOT DO, on purpose:
  · it does not compute position sizes from Coil's scores — sizing comes from YOUR config
  · it does not emit stop or target prices — Coil publishes neither, and inventing them
    here would put words in the publisher's mouth
  · it does not decide when to sell; exits are yours (see README, "What is deliberately
    missing")
"""
from __future__ import annotations

import os
from dataclasses import dataclass

PAPER_BASE = "https://paper-api.alpaca.markets"
LIVE_BASE = "https://api.alpaca.markets"


@dataclass
class Order:
    """A proposed order. Nothing here is sent anywhere until submit() is called."""
    symbol: str
    notional: float
    side: str = "buy"
    reason: str = ""

    def describe(self) -> str:
        return f"{self.side.upper():4s} {self.symbol:6s} ${self.notional:>8,.2f}  {self.reason}"


def plan_orders(candidates: list, cash: float, cfg) -> list:
    """Your sizing rules, applied to the board's ranked candidates.

    Equal-weight across up to max_positions, capped at max_position_pct of cash. Simple and
    boring by design — replace this function with your own rules; that is the point of it
    being a separate function.
    """
    if not candidates:
        return []
    n = min(len(candidates), cfg.max_positions)
    per = min(cash / n, cash * cfg.max_position_pct) if n else 0.0
    if per < cfg.min_notional:
        return []
    out = []
    for c in candidates[:n]:
        sym = c.get("sym") or c.get("symbol")
        if not sym:
            continue
        score = c.get("opp_pct") or c.get("opp")
        state = c.get("state", "?")
        out.append(Order(symbol=sym, notional=round(per, 2),
                         reason=f"opp={score} state={state}"))
    return out


class Alpaca:
    """Minimal Alpaca REST client — orders and account only, no dependencies."""

    def __init__(self, paper: bool = True):
        self.key = os.environ.get("ALPACA_API_KEY_ID")
        self.secret = os.environ.get("ALPACA_API_SECRET_KEY")
        # Live requires BOTH signals (peer review 2026-07-24): the caller must pass
        # paper=False AND the environment must carry the sentinel. Before this, either alone
        # sufficed — Alpaca(paper=False) reached a real account with no env var at all, and a
        # sentinel left in a shell profile silently flipped the default run to live. Passing
        # paper=False WITHOUT the sentinel is a hard error rather than a silent downgrade,
        # so a misconfiguration is loud instead of surprising in either direction.
        env_live = os.environ.get("ALPACA_LIVE_TRADING") == "I_UNDERSTAND_THE_RISK"
        if not paper and not env_live:
            raise RuntimeError(
                "live trading requires ALPACA_LIVE_TRADING=I_UNDERSTAND_THE_RISK in the "
                "environment as well — refusing to guess")
        self.paper = paper or not env_live
        self.base = PAPER_BASE if self.paper else LIVE_BASE

    @property
    def configured(self) -> bool:
        return bool(self.key and self.secret)

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        import json as _json
        import urllib.request
        req = urllib.request.Request(
            self.base + path, method=method,
            data=_json.dumps(body).encode() if body else None,
            headers={"APCA-API-KEY-ID": self.key or "", "APCA-API-SECRET-KEY": self.secret or "",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return _json.loads(r.read().decode() or "{}")

    def account(self) -> dict:
        return self._req("GET", "/v2/account")

    def positions(self) -> list:
        return self._req("GET", "/v2/positions")  # type: ignore[return-value]

    def submit(self, order: Order) -> dict:
        return self._req("POST", "/v2/orders", {
            "symbol": order.symbol, "notional": str(order.notional),
            "side": order.side, "type": "market", "time_in_force": "day"})
