#!/usr/bin/env python3
"""
Market Data Collector
Fetches all relevant market indicators for AI strategy selection
"""

import requests
import json
from datetime import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any


class MarketDataCollector:
    """Collects market data from various APIs"""

    def __init__(self):
        self.binance_base = "https://api.binance.com/api/v3"
        self.binance_futures = "https://fapi.binance.com/fapi/v1"
        self.fear_greed_url = "https://api.alternative.me/fng/"

    def fetch_all(self) -> Dict[str, Any]:
        """Fetch all market data and return structured dict"""
        print("📊 Fetching market data...")

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "btc_price": self.get_btc_price(),
            "price_24h": self.get_24h_stats(),
            "fear_greed_index": self.get_fear_greed_index(),
            "funding_rate": self.get_funding_rate(),
            "technical_indicators": self.get_technical_indicators(),
        }

        # Add derived fields
        data["regime"] = self.determine_regime(data)

        print(f"✅ Market data collected: BTC=${data['btc_price']:,.0f}, F&G={data['fear_greed_index']}")
        return data

    def get_btc_price(self) -> float:
        """Get current BTC/USDT price"""
        try:
            url = f"{self.binance_base}/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return float(response.json()["price"])
        except Exception as e:
            print(f"⚠️  Error fetching BTC price: {e}")
            return 0.0

    def get_24h_stats(self) -> Dict[str, float]:
        """Get 24h price statistics"""
        try:
            url = f"{self.binance_base}/ticker/24hr?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "change_percent": float(data["priceChangePercent"]),
                "volume": float(data["volume"]),
                "volume_quote": float(data["quoteVolume"]),
            }
        except Exception as e:
            print(f"⚠️  Error fetching 24h stats: {e}")
            return {"high": 0, "low": 0, "change_percent": 0, "volume": 0, "volume_quote": 0}

    def get_fear_greed_index(self) -> int:
        """Get current Fear & Greed Index"""
        try:
            response = requests.get(self.fear_greed_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return int(data["data"][0]["value"])
        except Exception as e:
            print(f"⚠️  Error fetching Fear & Greed Index: {e}")
            return 50  # Default to neutral

    def get_funding_rate(self) -> float:
        """Get current BTC perpetual funding rate"""
        try:
            url = f"{self.binance_futures}/fundingRate?symbol=BTCUSDT&limit=1"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data[0]["fundingRate"])
        except Exception as e:
            print(f"⚠️  Error fetching funding rate: {e}")
            return 0.0

    def get_technical_indicators(self) -> Dict[str, float]:
        """Calculate technical indicators from recent candles"""
        try:
            # Fetch 1h candles (need 200 for EMA 200)
            url = f"{self.binance_base}/klines?symbol=BTCUSDT&interval=1h&limit=200"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            candles = response.json()

            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['volume'] = df['volume'].astype(float)

            # Calculate indicators
            indicators = {
                "rsi_14": self.calculate_rsi(df['close'], 14),
                "adx_14": self.calculate_adx(df, 14),
                "ema_50": self.calculate_ema(df['close'], 50),
                "ema_200": self.calculate_ema(df['close'], 200),
                "bb_upper": 0,  # Will calculate below
                "bb_lower": 0,
                "volume_ma_20": df['volume'].rolling(20).mean().iloc[-1],
            }

            # Bollinger Bands
            sma_20 = df['close'].rolling(20).mean().iloc[-1]
            std_20 = df['close'].rolling(20).std().iloc[-1]
            indicators["bb_upper"] = sma_20 + (2 * std_20)
            indicators["bb_lower"] = sma_20 - (2 * std_20)

            # Volume spike detection
            current_volume = df['volume'].iloc[-1]
            indicators["volume_spike"] = bool(current_volume > (indicators["volume_ma_20"] * 2.0))

            return indicators

        except Exception as e:
            print(f"⚠️  Error calculating technical indicators: {e}")
            return {
                "rsi_14": 50, "adx_14": 20, "ema_50": 0, "ema_200": 0,
                "bb_upper": 0, "bb_lower": 0, "volume_ma_20": 0, "volume_spike": False
            }

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def calculate_ema(self, prices: pd.Series, period: int) -> float:
        """Calculate EMA"""
        ema = prices.ewm(span=period, adjust=False).mean()
        return float(ema.iloc[-1])

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX (Average Directional Index)"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']

            # Calculate +DM and -DM
            high_diff = high.diff()
            low_diff = -low.diff()

            plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
            minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

            # Calculate TR (True Range)
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Smooth TR, +DM, -DM
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

            # Calculate DX and ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()

            return float(adx.iloc[-1])
        except Exception as e:
            print(f"⚠️  Error calculating ADX: {e}")
            return 20.0  # Default to neutral

    def determine_regime(self, data: Dict[str, Any]) -> str:
        """Determine current market regime"""
        try:
            tech = data["technical_indicators"]
            ema_50 = tech["ema_50"]
            ema_200 = tech["ema_200"]
            adx = tech["adx_14"]

            if ema_50 > ema_200:
                if adx > 25:
                    return "bull_trending"
                else:
                    return "bull_consolidation"
            else:
                if adx > 25:
                    return "bear_trending"
                else:
                    return "bear_consolidation"
        except:
            return "unknown"


def main():
    """Test the market data collector"""
    collector = MarketDataCollector()
    data = collector.fetch_all()

    print("\n" + "="*60)
    print("MARKET DATA SUMMARY")
    print("="*60)
    print(f"Timestamp: {data['timestamp']}")
    print(f"BTC Price: ${data['btc_price']:,.2f}")
    print(f"24h Change: {data['price_24h']['change_percent']:.2f}%")
    print(f"Fear & Greed Index: {data['fear_greed_index']} ({'Extreme Fear' if data['fear_greed_index'] < 25 else 'Fear' if data['fear_greed_index'] < 50 else 'Greed'})")
    print(f"Funding Rate: {data['funding_rate']*100:.4f}% (every 8h)")
    print(f"\nTechnical Indicators:")
    print(f"  RSI (14): {data['technical_indicators']['rsi_14']:.2f}")
    print(f"  ADX (14): {data['technical_indicators']['adx_14']:.2f}")
    print(f"  EMA 50: ${data['technical_indicators']['ema_50']:,.0f}")
    print(f"  EMA 200: ${data['technical_indicators']['ema_200']:,.0f}")
    print(f"  Volume Spike: {data['technical_indicators']['volume_spike']}")
    print(f"\nRegime: {data['regime']}")
    print("="*60)

    # Save to file
    with open("logs/market_data_latest.json", "w") as f:
        json.dump(data, f, indent=2)
    print("\n✅ Data saved to logs/market_data_latest.json")


if __name__ == "__main__":
    main()
