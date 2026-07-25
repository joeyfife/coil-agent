# coil-agent

A small, readable long-only swing harness that reads a **published, scored market board**
and turns it into paper orders — so an LLM agent has something disciplined to act on
instead of screening 500 tickers and buying whatever it saw most recently.

Runs end to end with **no API key, no wallet, and no account**.

```bash
git clone https://github.com/joeyfife/coil-agent && cd coil-agent
python -m coil_agent.run          # dry run: prints the record, the regime, and a plan
```

Nothing is sent anywhere until you add broker keys and pass `--submit`.

---

## What it does

Every run reads the board **top-down**, in this order, and stops as soon as the board says
stop:

1. **Regime.** Is the tape risk-on, selective, or stand-down — and does the permission
   ladder (index → sector → name) allow individual names at all? If not, the run ends and
   the journal records a deliberate stand-down. *An empty result here is an answer.*
2. **Candidates.** Today's ranked names for your chosen book, already scored for
   opportunity, entry quality and hold strength.
3. **Your sizing rules** (`coil_agent/config.py`) — equal-weight, capped, with a cash
   floor. Boring on purpose. Replace `plan_orders()` with your own.
4. **The broker**, last. Alpaca **paper** by default; going live takes an explicit
   environment variable that spells out what you are doing.

Everything is appended to `coil_agent_journal.jsonl`, including the days it did nothing.

## Where the data comes from

[Coil](https://coil.trade) scores ~560 US names (S&P 500, Nasdaq-100, macro ETFs) plus a
long-only BTC/ETH trend book each market morning: `opp_pct` (opportunity 0–100), `entry_q`
(buyable now vs extended), `hold_q` (trend durability), and a `state`
(`firing` / `ready` / `setup` / `wait` / `chase` / `falling`).

| Tier | How | What you get |
|---|---|---|
| **Free** (default) | nothing to configure | Full board, one market day delayed |
| Free MCP | `claude mcp add --transport http coil https://coil.trade/mcp` | Same board as agent tools |
| License | `COIL_LICENSE_KEY=…` | Live intraday board (~5 min in market hours) |
| x402 | any x402 client | Pay per read in USDC, no account |

The delayed tier is genuinely usable for a swing-timeframe strategy, which is what this is.

## Check the publisher before you trust it

Two things are free and unauthenticated, because you should not have to pay to evaluate
someone:

```bash
curl https://coil.trade/api/perf           # engine vs SPY and QQQ, funding-adjusted
curl https://coil.trade/api/board/proof    # sha256 committed at publish time, each day
python -m coil_agent.run --verify          # recompute a commitment yourself
```

The commitment log is append-only and each digest is written **before** the outcome is
known, so a day's published scores cannot be quietly improved after the fact. `verify.py`
implements the published canonicalisation in ~15 lines; the same recipe reproduces
byte-identically in JavaScript.

The record is thin and honest — a few weeks, roughly market-matching, published with its
sample size attached. Read it yourself rather than taking a number from a README.

## What is deliberately missing

- **No stop or target prices.** Coil publishes scores and states; it does not publish exit
  levels, and this harness will not invent them and attribute them to the publisher.
- **No position sizing from the scores.** Sizing is in your config, where you can see it.
- **No exit logic.** Deciding when to sell is the hardest part of this and it is yours. The
  journal gives you the data to build it.
- **No backtest.** A backtest of a board you can only read forward would prove nothing.

If you want those decisions made for you, that is a different product and this is not it.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `COIL_BOOK` | `spx` | `spx`, `qqq`, `macro`, `crypto` |
| `COIL_MAX_POSITIONS` | `5` | Max concurrent names |
| `COIL_MAX_POSITION_PCT` | `0.20` | Max fraction of deployable cash per name |
| `COIL_CASH_FLOOR_PCT` | `0.20` | Fraction of equity never deployed |
| `COIL_MIN_NOTIONAL` | `10` | Skip orders smaller than this ($) |
| `COIL_JOURNAL` | `coil_agent_journal.jsonl` | Where the run journal is written |
| `COIL_LICENSE_KEY` | – | Live board instead of delayed |
| `ALPACA_API_KEY_ID` / `ALPACA_API_SECRET_KEY` | – | Paper trading (free, unfunded) |

## Use it from an AI agent

Point your agent at the board directly via MCP and let it run this loop:

```bash
claude mcp add --transport http coil https://coil.trade/mcp
```

(Claude Desktop and Cursor shapes: [`examples/mcp_setup.md`](examples/mcp_setup.md).)

If your agent can also *execute* — Robinhood's agentic accounts, or Alpaca — the
[pairing recipe](https://coil.trade/agents/robinhood) documents the read order and a prompt
that encodes it.

## Run it on Apify (no install)

This repo doubles as an [Apify](https://apify.com) Actor — `.actor/` carries the input schema,
a dataset view and a dependency-free Dockerfile. It publishes the board as dataset rows: one
`regime` row per book (read it first) and one `name` row per scored name, with an optional
`record` row carrying the publisher's own return versus SPY and QQQ.

Inputs: `book` (all / spx / qqq / macro / crypto), `includeRegime`, `includeRecord`, and an
optional Coil Scanner `licenseKey` for the live intraday board instead of the free delayed one.

The same entry point runs locally with no Apify at all — it prints the rows instead of pushing
them:

```bash
python3 -m actor_main
```

## Disclaimer

Research software, published for study. **Not investment advice**, not a recommendation to
buy or sell any security, not a managed account, and not a promise of any outcome. Markets
can lose money and an automated agent can lose it faster and more consistently than you
would by hand. Paper-trade it for a long time. You are responsible for every order your
machine sends.

MIT licensed. Not affiliated with Alpaca, Robinhood, or Anthropic.
