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


class ScalpingStrategy(IStrategy):
    """
    Scalping Strategy - Quick in/out for small profits

    Characteristics:
    - 1m timeframe (very fast)
    - Small profit targets (0.5-1%)
    - Tight stop loss (0.3%)
    - Many trades per day
    - High win rate required (60%+)

    Entry: Quick momentum bursts with volume
    Exit: Fast profit taking or cut losses quickly
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Aggressive ROI - true scalping on 1m
    minimal_roi = {
        "0": 0.008,   # Take 0.8% profit immediately
        "2": 0.006,   # After 2min, take 0.6%
        "5": 0.005,   # After 5min, take 0.5%
        "10": 0.004,  # After 10min, take 0.4%
        "15": 0.003,  # After 15min, take 0.3%
    }

    # Very tight stop loss for 1m scalping
    stoploss = -0.004  # -0.4% (just above fees)

    # Trailing stop to lock in quick profits
    trailing_stop = True
    trailing_stop_positive = 0.003  # Start trailing at 0.3%
    trailing_stop_positive_offset = 0.005  # Trigger at 0.5%
    trailing_only_offset_is_reached = True

    # 1m timeframe for true scalping
    timeframe = "1m"
    process_only_new_candles = True

    # Don't use exit signals - ROI and trailing stop handle it
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Hyperoptable parameters
    rsi_entry = IntParameter(40, 60, default=50, space="buy", optimize=True, load=True)
    rsi_exit = IntParameter(60, 80, default=70, space="sell", optimize=True, load=True)
    volume_surge = DecimalParameter(1.5, 3.0, default=2.0, space="buy", optimize=True, load=True)

    startup_candle_count: int = 100

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
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "red"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Scalping indicators - fast-moving, responsive
        """

        # RSI - short period for faster signals
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=7)  # Faster than default 14

        # Fast EMAs for quick trend detection
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=5)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=13)

        # Volume - critical for scalping
        dataframe["volume_ma"] = dataframe["volume"].rolling(10).mean()
        dataframe["volume_surge"] = dataframe["volume"] / dataframe["volume_ma"]

        # Price momentum - need quick bursts
        dataframe["price_change"] = dataframe["close"].pct_change()
        dataframe["momentum"] = dataframe["close"].pct_change(periods=3)

        # Bollinger Bands - narrower for 1m
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=10, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["bb_width"] = (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe["bb_middleband"]

        # MACD - faster settings for scalping
        macd = ta.MACD(dataframe, fastperiod=6, slowperiod=13, signalperiod=5)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Scalping entry: Quick momentum burst with volume

        Need ALL of:
        1. Price breaking up through fast EMA
        2. Fast EMA above slow EMA (uptrend)
        3. Volume surge (buying pressure)
        4. RSI showing momentum but not overbought
        5. MACD confirming
        6. Positive price momentum
        """
        dataframe.loc[
            (
                # Trend: Fast EMA above slow EMA
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                # Price just crossed above fast EMA (momentum starting)
                & (qtpylib.crossed_above(dataframe["close"], dataframe["ema_fast"]))

                # RSI: Showing momentum (not oversold, not overbought)
                & (dataframe["rsi"] > self.rsi_entry.value)
                & (dataframe["rsi"] < 75)  # Not too high
                # RSI rising (momentum building)
                & (dataframe["rsi"] > dataframe["rsi"].shift(1))

                # Volume: Strong surge confirms the move
                & (dataframe["volume_surge"] > self.volume_surge.value)

                # MACD: Confirms momentum
                & (dataframe["macd"] > dataframe["macdsignal"])
                & (dataframe["macd"] > 0)  # Above zero line

                # Price momentum: Positive and accelerating
                & (dataframe["momentum"] > 0)
                & (dataframe["price_change"] > 0)

                # Bollinger Bands: Volatility present (BB width not too tight)
                & (dataframe["bb_width"] > 0.01)
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals disabled - ROI and trailing stop handle exits
        """
        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Scalping custom exit: Take profits very quickly
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        trade_duration_minutes = (current_time - trade.open_date_utc).total_seconds() / 60

        # Quick profit target: 0.8% (above fees + some profit)
        if current_profit >= 0.008:
            return 'scalp_profit_0_8pct'

        # If momentum reverses while in profit, exit
        if current_profit >= 0.003:  # At least 0.3% profit
            if last_candle['macd'] < last_candle['macdsignal']:
                return 'exit_momentum_reverse'
            if last_candle['rsi'] > 75:  # Overbought
                return 'exit_overbought'

        # Cut losses very fast if momentum fails
        if current_profit <= -0.002:  # -0.2% (below fees)
            if last_candle['ema_fast'] < last_candle['ema_slow']:
                return 'stop_loss_trend_fail'

        # Scalps should be quick - if not profitable after 15min, exit
        if trade_duration_minutes > 15:
            if current_profit < 0.002:  # Less than 0.2%
                return 'exit_stale_scalp'

        return None
