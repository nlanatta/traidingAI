# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
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


class MomentumStrategy(IStrategy):
    """
    Momentum/Trend Following Strategy - BUY STRENGTH, not weakness

    Instead of buying dips (oversold RSI), this strategy:
    - Buys when price shows upward momentum
    - Rides trends with trailing stops
    - Exits when momentum fades

    Should work in bull markets where dip-buying strategies fail.
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Let trends run - minimal ROI targets
    minimal_roi = {
        "0": 0.15,   # Only exit at 15% profit via ROI (very rare)
        "60": 0.08,  # After 1 hour, 8%
        "120": 0.05, # After 2 hours, 5%
        "240": 0.03, # After 4 hours, 3%
    }

    # Wider stoploss since we're riding trends
    stoploss = -0.06  # -6%

    # Aggressive trailing stop to lock in momentum gains
    trailing_stop = True
    trailing_stop_positive = 0.02  # Start trailing at 2% profit
    trailing_stop_positive_offset = 0.03  # Trigger at 3% profit
    trailing_only_offset_is_reached = True

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Hyperoptable parameters
    # Momentum entry thresholds
    rsi_entry = IntParameter(50, 70, default=60, space="buy", optimize=True, load=True)
    volume_surge = DecimalParameter(1.5, 3.0, default=2.0, space="buy", optimize=True, load=True)

    # Exit thresholds
    rsi_exit = IntParameter(30, 50, default=40, space="sell", optimize=True, load=True)
    profit_target = DecimalParameter(0.03, 0.08, default=0.05, space="sell", optimize=True, load=True)

    startup_candle_count: int = 200

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    plot_config = {
        "main_plot": {
            "ema_fast": {"color": "green"},
            "ema_slow": {"color": "red"},
            "ema_trend": {"color": "blue"},
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "red"},
            },
            "MACD": {
                "macd": {"color": "blue"},
                "macdsignal": {"color": "orange"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add momentum indicators
        """

        # RSI - but we'll use it opposite: high RSI = momentum
        dataframe["rsi"] = ta.RSI(dataframe)

        # EMAs for trend detection
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=50)

        # Volume indicators - momentum needs volume
        dataframe["volume_ma"] = dataframe["volume"].rolling(20).mean()
        dataframe["volume_surge"] = dataframe["volume"] / dataframe["volume_ma"]

        # MACD for momentum confirmation
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # ADX for trend strength (high ADX = strong trend)
        dataframe["adx"] = ta.ADX(dataframe)

        # Price momentum
        dataframe["price_change"] = dataframe["close"].pct_change()
        dataframe["price_momentum"] = dataframe["close"].pct_change(periods=10)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry: BUY STRENGTH, not weakness
        - Price above rising EMAs (bullish alignment)
        - RSI showing momentum (above 60, not below 30)
        - Volume surge confirms buying pressure
        - MACD positive and rising
        """
        dataframe.loc[
            (
                # TREND: Price above all EMAs (bullish structure)
                (dataframe["close"] > dataframe["ema_fast"])
                & (dataframe["close"] > dataframe["ema_slow"])
                & (dataframe["close"] > dataframe["ema_trend"])
                # EMAs bullishly aligned (fast > slow > trend)
                & (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["ema_slow"] > dataframe["ema_trend"])

                # MOMENTUM: RSI showing strength (not oversold!)
                & (dataframe["rsi"] > self.rsi_entry.value)
                & (dataframe["rsi"] < 80)  # Not overbought extreme
                # RSI rising (momentum building)
                & (dataframe["rsi"] > dataframe["rsi"].shift(1))

                # VOLUME: Strong buying pressure
                & (dataframe["volume_surge"] > self.volume_surge.value)

                # MACD: Positive momentum
                & (dataframe["macd"] > dataframe["macdsignal"])
                & (dataframe["macd"] > 0)  # Above zero line
                & (dataframe["macdhist"] > dataframe["macdhist"].shift(1))  # Histogram growing

                # ADX: Strong trend present
                & (dataframe["adx"] > 25)

                # Price momentum positive
                & (dataframe["price_momentum"] > 0)
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit: When momentum fades or trend reverses
        - RSI drops (losing momentum)
        - MACD crosses down
        - EMAs start reversing
        """
        dataframe.loc[
            (
                # Momentum fading: RSI dropping
                (dataframe["rsi"] < self.rsi_exit.value)
                & (dataframe["rsi"] < dataframe["rsi"].shift(1))
            )
            |
            (
                # Trend reversing: MACD crosses down
                (qtpylib.crossed_below(dataframe["macd"], dataframe["macdsignal"]))
                & (dataframe["close"] < dataframe["ema_fast"])
            )
            |
            (
                # Strong reversal signal: price below all EMAs
                (dataframe["close"] < dataframe["ema_fast"])
                & (dataframe["close"] < dataframe["ema_slow"])
                & (dataframe["ema_fast"] < dataframe["ema_slow"])
            ),
            "exit_long",
        ] = 1

        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Custom exit: Lock in momentum gains quickly
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600

        # Take profit at target (momentum trades should move fast)
        if current_profit >= self.profit_target.value:
            return 'take_profit_momentum'

        # If momentum is fading (RSI dropping while in profit), take it
        if current_profit >= 0.02:
            if last_candle['rsi'] < last_candle['rsi'] - 5:  # RSI dropped 5 points
                return 'exit_momentum_fade'

        # Exit if losing and momentum clearly reversed
        if current_profit <= -0.03:
            if last_candle['macd'] < last_candle['macdsignal']:
                return 'stop_loss_momentum_reversal'

        # Momentum trades should move quickly - if stale, exit
        if trade_duration > 4:
            if current_profit < 0.01:
                return 'exit_stale_no_momentum'

        return None
