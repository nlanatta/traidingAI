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


class ImprovedAdaptiveV3(IStrategy):
    """
    ImprovedAdaptiveV3 - Combining all proven improvements:

    1. ADX filter (ADX <25) - Only trade in ranging markets (from CustomSampleStrategy)
    2. Bull/bear regime detection (EMA 50/200) - Adaptive entries (from ImprovedAdaptive)
    3. No exit signals - ROI + trailing stops only (from V2 analysis)
    4. Optimized hyperopt parameters
    5. Less aggressive bear market stops

    Based on trading wiki recommendations:
    - Mean reversion needs ADX filter to avoid trends
    - Works 60-70% of time when ADX <25
    - Catastrophic losses in trends (ADX >25)
    """

    INTERFACE_VERSION = 3
    can_short: bool = False

    # Aggressive ROI - let trailing stops work
    minimal_roi = {
        "0": 0.06,   # Take 6% profit immediately
        "30": 0.04,  # After 30min, 4%
        "60": 0.03,  # After 1 hour, 3%
        "120": 0.02, # After 2 hours, 2%
        "240": 0.01, # After 4 hours, 1%
    }

    stoploss = -0.05  # -5%

    # Aggressive trailing
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    timeframe = "5m"
    process_only_new_candles = True

    # DISABLE exit signals - they lose money
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Optimized parameters from hyperopt
    buy_rsi = IntParameter(low=20, high=40, default=25, space="buy", optimize=True, load=True)
    sell_rsi = IntParameter(low=60, high=80, default=77, space="sell", optimize=True, load=True)
    volume_factor = DecimalParameter(1.2, 2.0, default=1.941, space="buy", optimize=True, load=True)

    bull_rsi_offset = IntParameter(5, 15, default=13, space="buy", optimize=True, load=True)
    bear_profit_target = DecimalParameter(0.02, 0.04, default=0.026, space="sell", optimize=True, load=True)

    # ADX filter threshold
    adx_threshold = IntParameter(20, 30, default=25, space="buy", optimize=True, load=True)

    startup_candle_count: int = 250

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
            "ADX": {
                "adx": {"color": "green"},
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe["rsi"] = ta.RSI(dataframe)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        # TEMA
        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)

        # EMAs for regime detection
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)

        # Volume
        dataframe["volume_ma"] = dataframe["volume"].rolling(20).mean()

        # MACD
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # ADX - CRITICAL FILTER for mean reversion
        dataframe["adx"] = ta.ADX(dataframe)

        # Market regime detection
        dataframe["is_bull"] = (dataframe["close"] > dataframe["ema_200"]) & (dataframe["ema_50"] > dataframe["ema_200"])
        dataframe["is_bear"] = (dataframe["close"] < dataframe["ema_200"]) | (dataframe["ema_50"] < dataframe["ema_200"])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry with ADX filter + regime-specific rules

        CRITICAL: ADX <25 filter prevents catastrophic losses in trends
        """

        # BULL MARKET ENTRIES (with ADX filter)
        dataframe.loc[
            (
                # CRITICAL: Only trade in ranging markets (no strong trend)
                (dataframe["adx"] < self.adx_threshold.value)

                # Bull regime
                & (dataframe["is_bull"])
                & (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value + self.bull_rsi_offset.value))
                & (dataframe["volume"] > dataframe["volume_ma"])
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                & (dataframe["tema"] <= dataframe["bb_middleband"])
                & (dataframe["macd"] > dataframe["macdsignal"])
            ),
            "enter_long",
        ] = 1

        # BEAR MARKET ENTRIES (with ADX filter)
        dataframe.loc[
            (
                # CRITICAL: Only trade in ranging markets
                (dataframe["adx"] < self.adx_threshold.value)

                # Bear regime
                & (dataframe["is_bear"])
                & (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value))
                & (dataframe["volume"] > dataframe["volume_ma"] * self.volume_factor.value)
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                & (dataframe["close"] <= dataframe["bb_middleband"])
            ),
            "enter_long",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals disabled - ROI and trailing stops handle exits
        """
        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
        current_profit: float, **kwargs
    ):
        """
        Custom exit - less aggressive than V1, especially in bear markets
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()

        is_bull = last_candle['is_bull']
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600

        # Bull market
        if is_bull:
            # Quick wins in bull
            if current_profit >= 0.04:
                return 'take_profit_bull_4pct'

            # Cut losses if trend reverses
            if current_profit <= -0.03:
                if last_candle['ema_50'] < last_candle['ema_200']:
                    return 'stop_loss_trend_reversal'

        # Bear market - LESS AGGRESSIVE than V1
        else:
            # Take profit quickly in bear
            if current_profit >= self.bear_profit_target.value:
                return 'take_profit_bear'

            # More lenient stop: -3.5% after 2 hours (V1 was -2.5% after 1 hour)
            if current_profit <= -0.035 and trade_duration > 2:
                return 'stop_loss_bear_2hr'

        return None
