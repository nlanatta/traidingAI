# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
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


class ImprovedStrategy(IStrategy):
    """
    Improved strategy with better risk management:
    - Tighter stoploss (-5% instead of -10%)
    - Trailing stop to lock in profits
    - Volume confirmation for entries
    - Better exit timing
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Aggressive ROI to take profits quickly
    minimal_roi = {
        "0": 0.05,   # Take 5% profit immediately if available
        "15": 0.03,  # After 15min, take 3%
        "30": 0.02,  # After 30min, take 2%
        "60": 0.01,  # After 1 hour, take 1%
    }

    # CRITICAL FIX: Tighter stoploss to prevent big losses
    stoploss = -0.05  # -5% instead of -10%

    # Enable trailing stop to lock in profits
    trailing_stop = True
    trailing_stop_positive = 0.01  # Start trailing at 1% profit
    trailing_stop_positive_offset = 0.015  # Trigger trailing at 1.5% profit
    trailing_only_offset_is_reached = True  # Only trail after offset reached

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Hyperoptable parameters
    buy_rsi = IntParameter(low=20, high=40, default=30, space="buy", optimize=True, load=True)
    sell_rsi = IntParameter(low=60, high=80, default=70, space="sell", optimize=True, load=True)
    volume_factor = DecimalParameter(1.2, 2.0, default=1.5, space="buy", optimize=True, load=True)

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
            "tema": {},
            "ema_fast": {"color": "green"},
            "ema_slow": {"color": "red"},
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "red"},
            },
            "Volume": {
                "volume": {"color": "blue"},
                "volume_ma": {"color": "orange"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators with focus on trend confirmation and volume
        """

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        # TEMA
        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)

        # EMA for trend confirmation
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)

        # Volume indicators
        dataframe["volume_ma"] = dataframe["volume"].rolling(20).mean()

        # MACD for additional confirmation
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry with balanced confirmation:
        - RSI oversold bounce
        - Volume confirmation (above average)
        - TEMA rising and below BB middle
        """
        dataframe.loc[
            (
                # RSI crosses above buy threshold (oversold bounce)
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value))
                # Volume above average (not requiring spike)
                & (dataframe["volume"] > dataframe["volume_ma"])
                # TEMA rising
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                # TEMA below BB middle (room to grow)
                & (dataframe["tema"] <= dataframe["bb_middleband"])
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit when momentum fades:
        - RSI overbought
        - TEMA above BB middle and falling
        - Or MACD crosses down
        """
        dataframe.loc[
            (
                # RSI overbought
                (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value))
                # TEMA above BB middle
                & (dataframe["tema"] > dataframe["bb_middleband"])
                # TEMA falling
                & (dataframe["tema"] < dataframe["tema"].shift(1))
            )
            |
            (
                # Alternative exit: MACD crosses down
                (qtpylib.crossed_below(dataframe["macd"], dataframe["macdsignal"]))
                # Only if we have some profit or small loss
                & (dataframe["close"] >= dataframe["close"].shift(1) * 0.98)
            ),
            "exit_long",
        ] = 1

        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Custom exit logic for better profit taking and loss cutting
        """

        # Take profit at 4% regardless of other conditions
        if current_profit >= 0.04:
            return 'take_profit_4pct'

        # Cut losses faster if trade is old and still losing
        if current_profit <= -0.03:
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
            # If losing -3% after 2 hours, exit
            if trade_duration > 2:
                return 'stop_loss_2hr'

        # Exit if trade has been open too long without profit
        if current_profit <= 0.005:  # Less than 0.5% profit
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
            # If barely profitable after 6 hours, exit
            if trade_duration > 6:
                return 'exit_stale_6hr'

        return None
