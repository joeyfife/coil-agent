"""Offline tests — no network, no keys, no broker. These pin the behaviour that matters:
the regime gate actually gates, and the verifier actually verifies."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coil_agent.board import buy_candidates, regime_line
from coil_agent.broker import plan_orders
from coil_agent.config import Config
from coil_agent.verify import digest, check

STAND_DOWN = {"books": {"spx": {"regime": {"verdict": "CASH - nothing qualifies",
                                           "ladder": {"rung": "CASH"}}}},
              "names": [{"sym": "AAPL", "bk": ["spx"], "opp_pct": 99}]}
RISK_ON = {"books": {"spx": {"regime": {"verdict": "Names are open",
                                        "ladder": {"rung": "NAMES"}}}},
           "names": [{"sym": "AAPL", "bk": ["spx"], "opp_pct": 70, "state": "ready"},
                     {"sym": "MSFT", "bk": ["spx"], "opp_pct": 90, "state": "firing"},
                     {"sym": "BTC-USD", "bk": ["crypto"], "opp_pct": 99},
                     {"sym": "SPY", "bk": ["spx"], "opp_pct": 95, "kind": "index"}]}


def test_stand_down_blocks_everything():
    assert buy_candidates(STAND_DOWN, "spx") == [], "CASH ladder must yield no candidates"


# The FREE tier — the default path — flattens the ladder onto the book instead of nesting it
# under regime. Shipping without this test let the gate pass silently on the tier every new
# user hits first: it printed "nothing qualifies" and then proposed three buys.
FREE_STAND_DOWN = {"books": {"spx": {"label": "SPX", "regime_mode": "NAMES_ON",
                                     "regime_verdict": "CASH - nothing qualifies",
                                     "ladder_rung": "CASH",
                                     "top3": [{"sym": "FDX", "opp": 76, "state": "firing"}]}}}


def test_free_tier_shape_also_gates():
    assert buy_candidates(FREE_STAND_DOWN, "spx") == [], \
        "the free board flattens ladder_rung onto the book - the gate must read that shape too"


def test_free_tier_serves_top3_when_permitted():
    b = {"books": {"spx": {"ladder_rung": "NAMES",
                           "top3": [{"sym": "FDX", "opp": 76}, {"sym": "FRT", "opp": 75}]}}}
    assert [c["sym"] for c in buy_candidates(b, "spx")] == ["FDX", "FRT"]


def test_ranked_and_filtered():
    c = buy_candidates(RISK_ON, "spx")
    assert [x["sym"] for x in c] == ["MSFT", "AAPL"], c   # ranked; index and other books excluded


def test_sizing_respects_caps_and_floor():
    cfg = Config()
    cfg.max_positions, cfg.max_position_pct, cfg.min_notional = 5, 0.20, 10
    orders = plan_orders(buy_candidates(RISK_ON, "spx"), cash=1000.0, cfg=cfg)
    assert len(orders) == 2
    assert all(o.notional <= 200.01 for o in orders), [o.notional for o in orders]
    assert cfg.deployable_cash(1000.0, 1000.0) == 800.0   # 20% cash floor honoured


def test_no_orders_below_min_notional():
    cfg = Config(); cfg.min_notional = 500
    assert plan_orders(buy_candidates(RISK_ON, "spx"), cash=100.0, cfg=cfg) == []


def test_verifier_matches_published_recipe():
    # The integral-float rule is what makes Python and JavaScript agree; pin it.
    payload = {"date": "2026-07-21", "names": {"A": [42, 58.1, 53], "AAPL": [90, 40.0, 59]}}
    d = digest(payload)
    assert check(payload, d)
    same_but_int = {"date": "2026-07-21", "names": {"A": [42, 58.1, 53], "AAPL": [90, 40, 59]}}
    assert digest(same_but_int) == d, "40.0 and 40 must canonicalise identically"
    assert not check({"date": "2026-07-21", "names": {"A": [1, 2, 3]}}, d)


def test_unknown_ladder_shape_fails_closed():
    """Peer review: an unrecognized shape must yield NO candidates, not fall through the gate."""
    weird = {"books": {"spx": {"regime": {"verdict": "??"}}},
             "names": [{"sym": "AAPL", "bk": ["spx"], "opp_pct": 99}]}
    assert buy_candidates(weird, "spx") == []


def test_live_trading_needs_both_signals():
    """paper=False without the env sentinel is a hard error; the sentinel alone cannot
    override paper=True. Neither signal alone may reach a real account."""
    import os
    from coil_agent.broker import Alpaca, LIVE_BASE, PAPER_BASE
    os.environ.pop("ALPACA_LIVE_TRADING", None)
    try:
        Alpaca(paper=False)
        assert False, "paper=False without the sentinel must raise"
    except RuntimeError:
        pass
    os.environ["ALPACA_LIVE_TRADING"] = "I_UNDERSTAND_THE_RISK"
    try:
        assert Alpaca(paper=True).base == PAPER_BASE, "sentinel alone must not flip paper=True"
        assert Alpaca(paper=False).base == LIVE_BASE, "both signals together select live"
    finally:
        os.environ.pop("ALPACA_LIVE_TRADING", None)


def test_bad_env_numbers_do_not_crash():
    import os
    os.environ["COIL_MAX_POSITIONS"] = "banana"
    try:
        import importlib
        from coil_agent import config as cfgmod
        importlib.reload(cfgmod)
        assert cfgmod.Config().max_positions == 5
    finally:
        os.environ.pop("COIL_MAX_POSITIONS", None)
        import importlib
        from coil_agent import config as cfgmod
        importlib.reload(cfgmod)


def test_regime_line_never_crashes():
    assert regime_line({}, "spx")


if __name__ == "__main__":
    fails = 0
    for n, f in sorted(globals().items()):
        if n.startswith("test_") and callable(f):
            try:
                f(); print(f"  PASS  {n}")
            except AssertionError as e:
                fails += 1; print(f"  FAIL  {n}: {e}")
    print("all green" if not fails else f"{fails} FAILED")
    raise SystemExit(1 if fails else 0)
