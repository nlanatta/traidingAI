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


class AdaptiveStrategy(IStrategy):
    """
    Adaptive strategy that detects market regime (bull/bear) and adjusts behavior:
    - Bull market: ride trends, higher entry RSI, let profits run
    - Bear market: bounce plays, lower entry RSI, quick exits
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Conservative ROI - let regime-specific exits handle it
    minimal_roi = {
        "0": 0.10,   # Only exit at 10% profit via ROI (rare)
        "60": 0.03,  # After 1 hour, 3%
        "120": 0.02, # After 2 hours, 2%
        "180": 0.01, # After 3 hours, 1%
    }

    # Tighter stoploss
    stoploss = -0.04  # -4%

    # Enable trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Hyperoptable parameters
    # Bull market parameters
    buy_rsi_bull = IntParameter(35, 50, default=40, space="buy", optimize=True, load=True)
    sell_rsi_bull = IntParameter(65, 80, default=75, space="sell", optimize=True, load=True)

    # Bear market parameters
    buy_rsi_bear = IntParameter(20, 35, default=28, space="buy", optimize=True, load=True)
    sell_rsi_bear = IntParameter(60, 75, default=68, space="sell", optimize=True, load=True)

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
            "RSI": {
                "rsi": {"color": "red"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators including market regime detection
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

        # EMAs for market regime detection
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        # Volume indicators
        dataframe["volume_ma"] = dataframe["volume"].rolling(20).mean()

        # MACD
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # Market regime detection
        dataframe["is_bull"] = dataframe["close"] > dataframe["ema_200"]
        dataframe["is_bear"] = dataframe["close"] < dataframe["ema_200"]
        dataframe["trend_strength"] = dataframe["ema_50"] - dataframe["ema_200"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry with regime-specific rules:
        - Bull market: higher RSI entry, ride trends
        - Bear market: lower RSI entry, catch bounces
        """

        # BULL MARKET ENTRIES - Ride the trend
        dataframe.loc[
            (
                # Market is bullish
                (dataframe["is_bull"])
                # RSI pullback in uptrend (not oversold, just dip)
                & (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi_bull.value))
                # Confirm uptrend
                & (dataframe["ema_50"] > dataframe["ema_200"])
                # Volume confirmation
                & (dataframe["volume"] > dataframe["volume_ma"])
                # TEMA rising
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                # MACD positive momentum
                & (dataframe["macd"] > dataframe["macdsignal"])
            ),
            "enter_long",
        ] = 1

        # BEAR MARKET ENTRIES - Bounce plays
        dataframe.loc[
            (
                # Market is bearish
                (dataframe["is_bear"])
                # RSI oversold bounce
                & (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi_bear.value))
                # Volume spike (capitulation)
                & (dataframe["volume"] > dataframe["volume_ma"] * 1.5)
                # TEMA starting to rise (momentum shift)
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                # Near lower BB (oversold)
                & (dataframe["close"] <= dataframe["bb_middleband"])
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit with regime-specific rules:
        - Bull market: let winners run longer (higher RSI exit)
        - Bear market: take profits quickly (lower RSI exit)
        """

        # BULL MARKET EXITS - Higher threshold
        dataframe.loc[
            (
                (dataframe["is_bull"])
                # RSI very overbought
                & (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi_bull.value))
                # TEMA above BB middle and falling
                & (dataframe["tema"] > dataframe["bb_middleband"])
                & (dataframe["tema"] < dataframe["tema"].shift(1))
            )
            |
            (
                # Or MACD crosses down in bull market
                (dataframe["is_bull"])
                & (qtpylib.crossed_below(dataframe["macd"], dataframe["macdsignal"]))
                & (dataframe["close"] > dataframe["ema_50"])  # But above trend
            ),
            "exit_long",
        ] = 1

        # BEAR MARKET EXITS - Lower threshold, take profits quick
        dataframe.loc[
            (
                (dataframe["is_bear"])
                # RSI moderately overbought (lower than bull)
                & (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi_bear.value))
                # Momentum fading
                & (dataframe["tema"] < dataframe["tema"].shift(1))
            )
            |
            (
                # Or any sign of reversal in bear market
                (dataframe["is_bear"])
                & (dataframe["close"] < dataframe["ema_50"])
                & (dataframe["rsi"] > 60)
            ),
            "exit_long",
        ] = 1

        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Custom exit with regime-aware profit taking
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        is_bull = last_candle['is_bull']

        # Bull market: let winners run, take bigger profits
        if is_bull:
            # Take profit at 5% in bull
            if current_profit >= 0.05:
                return 'take_profit_bull_5pct'

            # Cut losses faster if trend reverses
            if current_profit <= -0.02:
                if last_candle['ema_50'] < last_candle['ema_200']:
                    return 'stop_loss_trend_reversal'

        # Bear market: take profits quickly, strict stops
        else:
            # Take profit at 3% in bear (don't be greedy)
            if current_profit >= 0.03:
                return 'take_profit_bear_3pct'

            # Cut losses very fast in bear
            if current_profit <= -0.025:
                trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
                if trade_duration > 1:  # After 1 hour
                    return 'stop_loss_bear_1hr'

        # Exit stale trades regardless of regime
        if current_profit <= 0.005:
            trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
            if trade_duration > 4:
                return 'exit_stale_4hr'

        return None
