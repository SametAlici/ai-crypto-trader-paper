"""Daily 30/60/90-day momentum with a closed-candle BTC regime and vol cap."""

from datetime import datetime
from typing import ClassVar

import numpy as np
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame


class R1_TSMomentum(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "1d"
    startup_candle_count = 400  # EMA100 needs ~4x period to converge (recursive-analysis)
    minimal_roi: ClassVar[dict[str, float]] = {}
    stoploss = -0.30
    process_only_new_candles = True

    @property
    def protections(self):
        return [{"method": "CooldownPeriod", "stop_duration_candles": 2}]

    @informative("1d", "BTC/{stake}")
    def populate_indicators_btc(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["regime"] = ta.EMA(dataframe, timeperiod=100)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["momentum"] = sum(dataframe.close.pct_change(n) for n in (30, 60, 90)) / 3
        dataframe["vol"] = dataframe.close.pct_change().rolling(30).std() * np.sqrt(365)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        threshold = self.config.get("r1", {}).get("threshold", 0.03)
        dataframe.loc[
            (dataframe.momentum > threshold)
            & (dataframe["btc_usdt_close_1d"] > dataframe["btc_usdt_regime_1d"])
            & (dataframe.volume > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "positive_tsmom")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe.loc[
            ((dataframe.momentum < 0)
             | (dataframe["btc_usdt_close_1d"] < dataframe["btc_usdt_regime_1d"]))
            & (dataframe.volume > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "momentum_end")
        return dataframe

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float, proposed_stake: float,
        min_stake: float | None, max_stake: float, leverage: float,
        entry_tag: str | None, side: str, **kwargs,
    ) -> float:
        frame, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if frame.empty or not np.isfinite(frame.iloc[-1]["vol"]) or frame.iloc[-1]["vol"] <= 0:
            return 0.0
        target = self.config.get("r1", {}).get("target_vol", 0.40)
        # Cap by a third of equity: free-wallet allocation must not inflate later entries.
        allocation = min(proposed_stake, self.wallets.get_total_stake_amount() / 3)
        stake = min(max_stake, allocation * min(1.0, target / frame.iloc[-1]["vol"]))
        return float(stake) if stake >= (min_stake or 0) else 0.0
