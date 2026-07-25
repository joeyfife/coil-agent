"""The loop. Read the board top-down, propose orders, and only then touch the broker.

    python -m coil_agent.run              # dry run — prints the plan, sends nothing
    python -m coil_agent.run --submit     # sends the plan to Alpaca PAPER
    python -m coil_agent.run --verify     # check the archive against published commitments

The read order is the whole point. Regime first: if the permission ladder says CASH, the
run ends there and the journal records a deliberate stand-down. An agent that skips this
step and buys the top-ranked name every day is not running this strategy.
"""
from __future__ import annotations

import sys

from . import __version__, board, journal
from .broker import Alpaca, plan_orders
from .config import Config


def _fmt_pct(x) -> str:
    return "n/a" if x is None else f"{x:+.2f}%"


def show_record() -> None:
    """Print Coil's published record before doing anything with its scores."""
    try:
        p = board.perf()
    except board.BoardError as e:
        print(f"  record unavailable: {e}")
        return
    h = (p.get("perf") or {}).get("headline")
    if not h:
        print("  record: not published right now (omitted rather than estimated)")
        return
    print(f"  record since inception: engine {_fmt_pct(h.get('engine_return_pct'))} · "
          f"SPY {_fmt_pct(h.get('spy_return_pct'))} · QQQ {_fmt_pct(h.get('qqq_return_pct'))}")
    note = (p.get("perf") or {}).get("note")
    if note:
        print(f"  {note}")


def verify_archive(date: str | None = None) -> int:
    """Recompute a published commitment from the archive payload you received."""
    from .verify import check
    log = board.proof()
    dates = [c["date"] for c in log.get("commitments", [])]
    if not dates:
        print("no commitments published yet")
        return 1
    target = date or dates[-1]
    print(f"verifying {target} ({len(dates)} commitments published)")
    entry = next((c for c in log["commitments"] if c["date"] == target), None)
    if not entry:
        print(f"  no commitment for {target}; available: {dates}")
        return 1
    try:
        payload = board._get("/api/board/asof", {"date": target})
    except board.BoardError as e:
        print(f"  the archive itself is a paid read ({e})")
        print(f"  published sha256 for {target}: {entry['sha256']}")
        print("  buy that day and re-run to check it against this digest.")
        return 0
    ok = check(payload, entry["sha256"])
    print(f"  published : {entry['sha256']}")
    print(f"  recomputed: {'MATCH' if ok else 'MISMATCH'}")
    return 0 if ok else 2


def main(argv: list | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--verify" in argv:
        i = argv.index("--verify")
        return verify_archive(argv[i + 1] if len(argv) > i + 1 and not argv[i + 1].startswith("-") else None)

    submit = "--submit" in argv
    cfg = Config()
    print(f"coil-agent {__version__} · book={cfg.book} · "
          f"{'SUBMIT' if submit else 'DRY RUN (nothing is sent)'}")
    show_record()

    b = board.board()
    print(f"\n  board asof {b.get('asof') or b.get('asof_daily')} "
          f"({'delayed' if b.get('delayed') else 'live'})")
    print(f"  regime: {board.regime_line(b, cfg.book)}")

    # 1. Regime gate. An empty candidate list here is an answer, not a failure.
    candidates = board.buy_candidates(b, cfg.book, limit=cfg.max_positions)
    if not candidates:
        print("\n  the board does not permit new names today — standing down.")
        journal.record({"action": "stand_down", "book": cfg.book,
                        "regime": board.regime_line(b, cfg.book)})
        return 0

    print(f"\n  {len(candidates)} candidate(s):")
    for c in candidates:
        print(f"    {c.get('sym'):6s} opp={c.get('opp_pct') or c.get('opp')} state={c.get('state')}")

    # 2. Broker. Only now, and only on paper unless explicitly told otherwise.
    api = Alpaca()
    if not api.configured:
        print("\n  no Alpaca keys configured — plan only.")
        print("  set ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY for paper trading (free, no funding).")
        journal.record({"action": "plan_only", "candidates": [c.get("sym") for c in candidates]})
        return 0

    acct = api.account()
    equity, cash = float(acct.get("equity", 0)), float(acct.get("cash", 0))
    deployable = cfg.deployable_cash(equity, cash)
    print(f"\n  alpaca {'PAPER' if api.paper else 'LIVE'} · equity ${equity:,.2f} · "
          f"deployable ${deployable:,.2f}")

    held = {p["symbol"] for p in api.positions()}
    orders = [o for o in plan_orders(candidates, deployable, cfg) if o.symbol not in held]
    if not orders:
        print("  nothing to do (already held, or below the minimum notional).")
        journal.record({"action": "no_orders", "held": sorted(held)})
        return 0

    print("\n  plan:")
    for o in orders:
        print("   ", o.describe())

    if not submit:
        print("\n  dry run — nothing sent. Re-run with --submit to place these on paper.")
        journal.record({"action": "dry_run", "orders": [o.__dict__ for o in orders]})
        return 0

    for o in orders:
        try:
            r = api.submit(o)
            print(f"    submitted {o.symbol}: {r.get('id', '?')}")
            journal.record({"action": "submitted", "symbol": o.symbol,
                            "notional": o.notional, "paper": api.paper, "order_id": r.get("id")})
        except Exception as e:  # one bad symbol must not kill the run
            print(f"    FAILED {o.symbol}: {e}")
            journal.record({"action": "submit_failed", "symbol": o.symbol, "error": str(e)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
