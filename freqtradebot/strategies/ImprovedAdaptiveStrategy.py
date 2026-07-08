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


class ImprovedAdaptiveStrategy(IStrategy):
    """
    Best of both worlds:
    - ImprovedStrategy's optimized parameters and risk management
    - AdaptiveStrategy's dynamic market regime detection
    - Regime-specific entry/exit behavior
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Aggressive ROI - let custom_exit handle regime-specific exits
    minimal_roi = {
        "0": 0.08,   # Only exit at 8% profit via ROI (rare)
        "30": 0.04,  # After 30min, 4%
        "60": 0.02,  # After 1 hour, 2%
        "120": 0.01, # After 2 hours, 1%
    }

    # Tighter stoploss from ImprovedStrategy
    stoploss = -0.05  # -5%

    # Trailing stop to lock in profits
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Hyperoptable parameters - optimized values from hyperopt
    buy_rsi = IntParameter(low=20, high=40, default=25, space="buy", optimize=True, load=True)
    sell_rsi = IntParameter(low=60, high=80, default=77, space="sell", optimize=True, load=True)
    volume_factor = DecimalParameter(1.2, 2.0, default=1.941, space="buy", optimize=True, load=True)

    # Additional regime-specific parameters - optimized values
    bull_rsi_offset = IntParameter(5, 15, default=13, space="buy", optimize=True, load=True)
    bear_profit_target = DecimalParameter(0.02, 0.04, default=0.026, space="sell", optimize=True, load=True)

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
            "tema": {},
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
        Add indicators with market regime detection
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

        # EMAs for trend and regime detection
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
        dataframe["is_bull"] = (dataframe["close"] > dataframe["ema_200"]) & (dataframe["ema_50"] > dataframe["ema_200"])
        dataframe["is_bear"] = (dataframe["close"] < dataframe["ema_200"]) | (dataframe["ema_50"] < dataframe["ema_200"])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry with regime-aware RSI thresholds:
        - Bull market: higher RSI entry (ride trends)
        - Bear market: lower RSI entry (catch bounces)
        """

        # BULL MARKET ENTRIES - Higher RSI threshold
        dataframe.loc[
            (
                # Market is bullish
                (dataframe["is_bull"])
                # RSI crosses above buy threshold + bull offset
                & (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value + self.bull_rsi_offset.value))
                # Volume confirmation
                & (dataframe["volume"] > dataframe["volume_ma"])
                # TEMA rising
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                # TEMA below BB middle (room to grow)
                & (dataframe["tema"] <= dataframe["bb_middleband"])
                # MACD positive momentum
                & (dataframe["macd"] > dataframe["macdsignal"])
            ),
            "enter_long",
        ] = 1

        # BEAR MARKET ENTRIES - Lower RSI threshold (oversold bounces)
        dataframe.loc[
            (
                # Market is bearish
                (dataframe["is_bear"])
                # RSI crosses above buy threshold (oversold bounce)
                & (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value))
                # Volume spike (capitulation)
                & (dataframe["volume"] > dataframe["volume_ma"] * self.volume_factor.value)
                # TEMA starting to rise
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
        - Bull market: let winners run (higher RSI exit)
        - Bear market: take profits quickly (lower RSI exit)
        """

        # BULL MARKET EXITS - Higher threshold
        dataframe.loc[
            (
                (dataframe["is_bull"])
                # RSI very overbought
                & (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value))
                # TEMA above BB middle and falling
                & (dataframe["tema"] > dataframe["bb_middleband"])
                & (dataframe["tema"] < dataframe["tema"].shift(1))
            )
            |
            (
                # Or MACD crosses down in bull market
                (dataframe["is_bull"])
                & (qtpylib.crossed_below(dataframe["macd"], dataframe["macdsignal"]))
                & (dataframe["rsi"] > 60)
            ),
            "exit_long",
        ] = 1

        # BEAR MARKET EXITS - Lower threshold
        dataframe.loc[
            (
                (dataframe["is_bear"])
                # RSI moderately overbought (lower than bull)
                & (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value - 5))
                # TEMA falling
                & (dataframe["tema"] < dataframe["tema"].shift(1))
            )
            |
            (
                # Or any sign of reversal in bear market
                (dataframe["is_bear"])
                & (dataframe["close"] < dataframe["ema_50"])
                & (dataframe["rsi"] > 55)
            ),
            "exit_long",
        ] = 1

        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Custom exit with regime-aware profit taking and stop losses
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        is_bull = last_candle['is_bull']
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600

        # Bull market: let winners run, take bigger profits
        if is_bull:
            # Take profit at 5% in bull
            if current_profit >= 0.05:
                return 'take_profit_bull_5pct'

            # Cut losses if trend reverses (EMA 50 crosses below EMA 200)
            if current_profit <= -0.03:
                if last_candle['ema_50'] < last_candle['ema_200']:
                    return 'stop_loss_trend_reversal'

            # Exit stale trades in bull after 6 hours
            if current_profit <= 0.01 and trade_duration > 6:
                return 'exit_stale_bull_6hr'

        # Bear market: take profits quickly, strict stops
        else:
            # Take profit at target (default 3%) in bear
            if current_profit >= self.bear_profit_target.value:
                return 'take_profit_bear'

            # Cut losses faster in bear market
            if current_profit <= -0.03 and trade_duration > 1:
                return 'stop_loss_bear_1hr'

            # Exit stale trades in bear after 3 hours (faster than bull)
            if current_profit <= 0.005 and trade_duration > 3:
                return 'exit_stale_bear_3hr'

        return None
