use # pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

import talib.abstract as ta
from technical import qtpylib


class TrendFollowingStrategy(IStrategy):
    """
    TrendFollowingStrategy - Based on trading wiki recommendations

    Complements ImprovedAdaptiveV3 (mean reversion):
    - V3 trades when ADX <25 (ranging markets, 70% of time)
    - This trades when ADX >25 (trending markets, 30% of time)

    Core principles from wiki:
    - 50/200 EMA crossover for trend detection
    - ADX >25 filter (only trade trending markets)
    - 2× ATR trailing stops (dynamic, adapts to volatility)
    - Expected: 35-45% win rate, 3-5:1 win/loss ratio
    - Cut losses short, let winners run

    Entry: Price crosses above 50 EMA while 50 > 200 (uptrend confirmed)
    Exit: 2× ATR trailing stop OR price closes below 50 EMA
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Minimal ROI - let winners run (trend following principle)
    minimal_roi = {
        "0": 0.10,    # 10% - only take profit if huge move
        "1440": 0.05, # After 1 day, 5%
        "2880": 0.03, # After 2 days, 3%
    }

    # Wide stoploss - will be overridden by 2× ATR trailing stop
    stoploss = -0.10  # -10% disaster protection

    # ATR-based trailing stop (primary exit method)
    trailing_stop = True
    trailing_stop_positive = 0.02  # Start trailing at 2% profit
    trailing_stop_positive_offset = 0.03  # Trigger at 3% profit
    trailing_only_offset_is_reached = True

    timeframe = "5m"
    process_only_new_candles = True

    # Exit signals disabled - trailing stop handles exits
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Hyperoptable parameters
    adx_threshold = IntParameter(20, 30, default=25, space="buy", optimize=True, load=True)
    volume_factor = DecimalParameter(1.2, 2.0, default=1.5, space="buy", optimize=True, load=True)
    atr_multiplier = DecimalParameter(1.5, 3.0, default=2.0, space="sell", optimize=True, load=True)

    startup_candle_count: int = 250  # Need 200 for EMA 200

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            "ema_50": {"color": "blue"},
            "ema_200": {"color": "red"},
        },
        "subplots": {
            "ADX": {
                "adx": {"color": "green"},
            },
            "ATR": {
                "atr": {"color": "orange"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Trend following indicators from wiki
        """

        # EMAs for trend detection (50/200 crossover)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        # ADX for trend strength (>25 = trending)
        dataframe["adx"] = ta.ADX(dataframe)

        # +DI and -DI for trend direction
        dataframe["plus_di"] = ta.PLUS_DI(dataframe)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe)

        # ATR for trailing stops (2× ATR from wiki)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # Volume
        dataframe["volume_ma"] = dataframe["volume"].rolling(20).mean()

        # Trend identification
        dataframe["is_uptrend"] = (
            (dataframe["ema_50"] > dataframe["ema_200"]) &
            (dataframe["close"] > dataframe["ema_50"])
        )
        dataframe["is_downtrend"] = (
            (dataframe["ema_50"] < dataframe["ema_200"]) &
            (dataframe["close"] < dataframe["ema_50"])
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Trend following entry from wiki:
        - ADX >25 (trending market confirmed)
        - Price crosses above 50 EMA while 50 > 200 (uptrend)
        - Volume confirmation (≥1.5× average)
        - +DI > -DI (directional momentum up)
        """

        dataframe.loc[
            (
                # CRITICAL: Only trade trending markets (ADX >25)
                (dataframe["adx"] > self.adx_threshold.value)

                # Uptrend structure: 50 EMA > 200 EMA
                & (dataframe["ema_50"] > dataframe["ema_200"])

                # Entry trigger: Price crosses above 50 EMA
                & (qtpylib.crossed_above(dataframe["close"], dataframe["ema_50"]))

                # Directional momentum: +DI > -DI
                & (dataframe["plus_di"] > dataframe["minus_di"])

                # Volume confirmation (wiki: ≥1.5× for crypto)
                & (dataframe["volume"] > dataframe["volume_ma"] * self.volume_factor.value)
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals disabled - trailing stop handles exits
        """
        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Custom exit: 2× ATR trailing stop + MA reversal

        From wiki:
        - Primary: ATR trailing stop (adapts to volatility)
        - Secondary: Exit if price closes below 50 EMA (trend broken)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        # Exit if trend broken (price closes below 50 EMA)
        if last_candle['close'] < last_candle['ema_50']:
            return 'exit_trend_broken_below_ema50'

        # Exit if ADX drops below 20 (trend exhausted)
        if last_candle['adx'] < 20:
            return 'exit_trend_exhausted_adx_low'

        # Exit if directional momentum reverses (-DI crosses above +DI)
        if last_candle['minus_di'] > last_candle['plus_di']:
            return 'exit_momentum_reversal'

        # Let ATR trailing stop handle most exits
        return None

    def custom_stoploss(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ) -> float:
        """
        Dynamic 2× ATR trailing stop from wiki

        Adapts to volatility:
        - High volatility = wider stops (avoid noise)
        - Low volatility = tighter stops (protect gains)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        atr = last_candle['atr']

        # Calculate 2× ATR stop distance from current price
        stop_distance = (atr * self.atr_multiplier.value) / current_rate

        # Return as negative percentage (stoploss format)
        return -stop_distance
