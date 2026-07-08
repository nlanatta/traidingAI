#!/usr/bin/env python3
"""
AI Trading System - Analysis Output for Claude Code
Outputs market analysis that Claude Code can read and make decisions on
"""

import json
from datetime import datetime
from market_data import MarketDataCollector


def generate_analysis():
    """Generate market analysis for Claude to review"""

    print("="*80)
    print("AI TRADING SYSTEM - Market Analysis")
    print(f"Time: {datetime.utcnow().isoformat()} UTC")
    print("="*80)

    # Collect market data
    collector = MarketDataCollector()
    data = collector.fetch_all()

    tech = data.get("technical_indicators", {})
    price_24h = data.get("price_24h", {})

    # Generate human-readable analysis
    analysis = f"""
CURRENT MARKET CONDITIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 PRICE DATA:
  • BTC Price: ${data.get('btc_price', 0):,.2f}
  • 24h Change: {price_24h.get('change_percent', 0):.2f}%
  • 24h High: ${price_24h.get('high', 0):,.2f}
  • 24h Low: ${price_24h.get('low', 0):,.2f}

😨 SENTIMENT:
  • Fear & Greed Index: {data.get('fear_greed_index', 50)}/100
    → {get_sentiment_label(data.get('fear_greed_index', 50))}

📈 TECHNICAL INDICATORS:
  • RSI (14): {tech.get('rsi_14', 50):.2f}
    → {get_rsi_label(tech.get('rsi_14', 50))}
  • ADX (14): {tech.get('adx_14', 20):.2f}
    → {get_adx_label(tech.get('adx_14', 20))}
  • EMA 50: ${tech.get('ema_50', 0):,.0f}
  • EMA 200: ${tech.get('ema_200', 0):,.0f}
    → Regime: {get_regime_label(data.get('regime', 'unknown'))}
  • Volume Spike: {'YES ⚠️' if tech.get('volume_spike', False) else 'No'}

💰 FUTURES DATA:
  • Funding Rate: {data.get('funding_rate', 0)*100:.4f}% (every 8h)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AVAILABLE STRATEGIES:

1. ImprovedAdaptiveV3 ✅ (Conservative Mean Reversion)
   • Use when: ADX <25, neutral sentiment (F&G 30-70)
   • Win rate: 100% (backtest)
   • Risk: Very Low

2. ContrarianbuyDips 🚧 (Aggressive - Not Ready Yet)
   • Use when: F&G <25, RSI <40, volume spike
   • Win rate: 70-80% expected
   • Risk: Medium

3. TrendFollowingFixed 🚧 (Momentum - Not Ready Yet)
   • Use when: ADX >30, clear trend
   • Win rate: 50-60% expected
   • Risk: High

4. RangeScalper 🚧 (High Frequency - Not Ready Yet)
   • Use when: ADX <20, low volatility
   • Win rate: 65-75% expected
   • Risk: Low-Medium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DECISION NEEDED:

Based on the current market conditions above, which strategy should we deploy?

Please analyze and respond with:
1. Recommended strategy name
2. Confidence level (1-10)
3. Brief reasoning (2-3 sentences)
4. Duration to run before next check (4h/8h/12h/24h)

Current strategy in config: {get_current_strategy()}
"""

    # Save raw data
    with open("logs/market_data_latest.json", "w") as f:
        json.dump(data, f, indent=2)

    # Save analysis
    with open("logs/market_analysis_latest.txt", "w") as f:
        f.write(analysis)

    print(analysis)
    print("\n✅ Analysis saved to logs/market_analysis_latest.txt")
    print("✅ Raw data saved to logs/market_data_latest.json")

    return data, analysis


def get_sentiment_label(fg_index):
    """Get sentiment label from F&G index"""
    if fg_index < 25:
        return "EXTREME FEAR 😱"
    elif fg_index < 50:
        return "Fear 😟"
    elif fg_index < 75:
        return "Neutral 😐"
    else:
        return "Greed 🤑"


def get_rsi_label(rsi):
    """Get RSI label"""
    if rsi < 30:
        return "OVERSOLD 📉"
    elif rsi < 40:
        return "Oversold"
    elif rsi > 70:
        return "OVERBOUGHT 📈"
    elif rsi > 60:
        return "Overbought"
    else:
        return "Neutral"


def get_adx_label(adx):
    """Get ADX label"""
    if adx < 20:
        return "RANGING (weak/no trend)"
    elif adx < 25:
        return "Weak trend forming"
    elif adx < 40:
        return "TRENDING (moderate)"
    else:
        return "STRONG TREND 🚀"


def get_regime_label(regime):
    """Get regime label"""
    labels = {
        "bull_trending": "🐂 BULL TRENDING",
        "bull_consolidation": "🐂 Bull Consolidating",
        "bear_trending": "🐻 BEAR TRENDING",
        "bear_consolidation": "🐻 Bear Consolidating",
        "unknown": "Unknown"
    }
    return labels.get(regime, regime)


def get_current_strategy():
    """Get currently deployed strategy"""
    try:
        with open("../config-live.json", "r") as f:
            config = json.load(f)
        return config.get("strategy", "unknown")
    except:
        return "unknown"


if __name__ == "__main__":
    generate_analysis()
