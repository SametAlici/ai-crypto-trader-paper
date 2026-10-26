"""Broad-universe TSMomentum subclass with configurable slot/sizing cap."""

from datetime import datetime

import numpy as np

from user_data.strategies.R1_TSMomentum import R1_TSMomentum


class R5_TSMomentum(R1_TSMomentum):
    """Subclass of R1_TSMomentum with per-position allocation cap matching slot count.

    Entry and exit rules remain strictly identical to R1_TSMomentum.
    Only custom_stake_amount is adapted so that the per-position cap equals
    equity / slots (defaulting to max_open_trades).
    """

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        frame, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if frame.empty or not np.isfinite(frame.iloc[-1]["vol"]) or frame.iloc[-1]["vol"] <= 0:
            return 0.0
        target = self.config.get("r1", {}).get("target_vol", 0.40)
        slots = int(
            self.config.get("r5", {}).get(
                "position_cap_slots", self.config.get("max_open_trades", 5)
            )
        )
        allocation = min(proposed_stake, self.wallets.get_total_stake_amount() / slots)
        stake = min(max_stake, allocation * min(1.0, target / frame.iloc[-1]["vol"]))
        return float(stake) if stake >= (min_stake or 0) else 0.0
