# A prompt that encodes the read order

Paste into your agent's instructions. It matters that the regime check comes first and
that the agent is told, explicitly, that sizing and exits are not the publisher's job.

```
Every morning, before considering any trade:

1. Call coil get_market_regime. If the permission ladder does not allow names,
   stop and report that the board says stand down. Do not place orders.
2. Call coil get_buy_list and consider ONLY names that appear on it.
3. Call coil get_stock_read on each candidate you are serious about.
4. Size positions from MY rules below - never from Coil, which publishes scores
   and states, not position sizes, stops or targets.
5. Place orders through my broker only within the budget I set, and show me the
   plan before you act.

My rules: [max position size, max concurrent positions, cash floor, what to do
with an existing position that leaves the buy list]
```

`get_morning_brief` collapses steps 1–2 into a single call if you would rather start there.
