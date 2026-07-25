# Coil Market Board — scored US stocks for AI agents

Returns a **scored, ranked US stock market board** as dataset rows: a regime verdict per book,
then every scored name with opportunity, entry-quality and hold-strength scores — so an agent has
a disciplined read instead of screening 500 tickers and buying whatever it saw most recently.

Free tier needs **no key, no wallet and no account**.

## What you get

Each run writes three kinds of row:

| `row_type` | What it is |
|---|---|
| `regime` | One per book — the verdict and the permission ladder. **Read these first.** |
| `name` | One per scored security: `opp`, `entry_q`, `hold_q`, `state`, sector, leadership flag. |
| `record` | Optional. The publisher's own return vs SPY and QQQ, with its sample-size note. |

**Read top-down.** If a book's `ladder_rung` is `CASH`, the ranked names under it are context, not
a green light. An agent that skips the regime row and buys the top-ranked name every day is not
running this strategy.

## Input

| Field | Default | Meaning |
|---|---|---|
| `book` | `all` | `all`, `spx` (S&P 500), `qqq` (Nasdaq-100), `macro`, `crypto` |
| `includeRegime` | `true` | Emit the regime row per book |
| `includeRecord` | `false` | Emit the publisher's benchmark-relative record |
| `licenseKey` | — | Optional [Coil Scanner](https://coil.trade/scanner) key for the live intraday board |

The live board recomputes **about every 5 minutes while the US market is open**; the free tier is the same board **one market day delayed**. `/api/board/asof` is the exception everywhere: an immutable archive, never revised. Without a licence key you get the full board **one market day delayed** — genuinely usable for a
swing-timeframe agent, which is what this is for.

## Reading the scores

- **`opp`** — opportunity, 0–100. A percentile **rank** across the scored universe on the publish
  date. Not a return forecast.
- **`entry_q`** — entry quality, 0–100: buyable now versus extended. Timing only.
- **`hold_q`** — hold strength, 0–100: trend durability if a position already exists.
- **`state`** — `firing` / `ready` / `setup` / `wait` / `chase` / `falling`. Never an instruction.

## Check the publisher before trusting it

Both free and unauthenticated:

- **[coil.trade/api/perf](https://coil.trade/api/perf)** — the engine's own return versus SPY and
  QQQ, funding-adjusted, published with its sample size. Omitted rather than estimated when the
  underlying data is unavailable.
- **[coil.trade/api/board/proof](https://coil.trade/api/board/proof)** — an append-only SHA-256
  commitment over every archived day, written at publish time **before the outcome was known**,
  with a verification recipe that reproduces byte-identically in Python and JavaScript.

## Other ways to read the same board

- Free MCP server: `claude mcp add --transport http coil https://coil.trade/mcp`
- Pay per read over [x402](https://x402.org) — $0.001–$0.25, no account
- Open source harness: [github.com/joeyfife/coil-agent](https://github.com/joeyfife/coil-agent)

## Disclaimer

Impersonal research publication — identical for every reader. **Scores and states only: never stop
prices, never target prices, never individualized investment advice.** Not a managed account, not a
signal service, not a guarantee of any outcome. Markets can lose money and an automated agent can
lose it faster. See [coil.trade/terms](https://coil.trade/terms).
