"""Your rules live here. Coil publishes scores and states; sizing and risk are yours."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_num(name: str, default: str, cast):
    """A typo in an env var should cost a warning and a default, not a traceback at import."""
    raw = os.environ.get(name, default)
    try:
        return cast(raw)
    except (TypeError, ValueError):
        print(f"  warning: {name}={raw!r} is not a number — using {default}")
        return cast(default)


@dataclass
class Config:
    book: str = os.environ.get("COIL_BOOK", "spx")          # spx | qqq | macro | crypto
    max_positions: int = _env_num("COIL_MAX_POSITIONS", "5", int)
    max_position_pct: float = _env_num("COIL_MAX_POSITION_PCT", "0.20", float)
    min_notional: float = _env_num("COIL_MIN_NOTIONAL", "10", float)
    cash_floor_pct: float = _env_num("COIL_CASH_FLOOR_PCT", "0.20", float)

    def deployable_cash(self, equity: float, cash: float) -> float:
        """Cash we are willing to deploy today, honouring the cash floor."""
        return max(0.0, min(cash, equity * (1.0 - self.cash_floor_pct)))
