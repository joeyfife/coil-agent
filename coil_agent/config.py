"""Your rules live here. Coil publishes scores and states; sizing and risk are yours."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    book: str = os.environ.get("COIL_BOOK", "spx")          # spx | qqq | macro | crypto
    max_positions: int = int(os.environ.get("COIL_MAX_POSITIONS", "5"))
    max_position_pct: float = float(os.environ.get("COIL_MAX_POSITION_PCT", "0.20"))
    min_notional: float = float(os.environ.get("COIL_MIN_NOTIONAL", "10"))
    cash_floor_pct: float = float(os.environ.get("COIL_CASH_FLOOR_PCT", "0.20"))

    def deployable_cash(self, equity: float, cash: float) -> float:
        """Cash we are willing to deploy today, honouring the cash floor."""
        return max(0.0, min(cash, equity * (1.0 - self.cash_floor_pct)))
