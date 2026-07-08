#!/usr/bin/env python3
"""
AI Strategy Selector
Uses Claude API to analyze market conditions and recommend optimal strategy
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()


class AIStrategySelector:
    """Selects optimal trading strategy based on market conditions"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in .env file")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def select_strategy(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and select optimal strategy

        Returns:
            {
                "strategy": "strategy_name",
                "confidence": 1-10,
                "reasoning": "explanation",
                "duration": "4h/8h/12h/24h",
                "max_drawdown_acceptable": "5%/10%/15%",
                "alternative": "backup_strategy"
            }
        """
        print("🧠 Asking AI to analyze market conditions...")

        prompt = self._build_prompt(market_data)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            content = response.content[0].text
            decision = json.loads(content)

            print(f"✅ AI Decision: {decision['strategy']} (confidence: {decision['confidence']}/10)")

            return decision

        except Exception as e:
            print(f"⚠️  Error calling Claude API: {e}")
            # Fallback to safe default
            return {
                "strategy": "ImprovedAdaptiveV3",
                "confidence": 5,
                "reasoning": f"API error, defaulting to safe strategy: {str(e)}",
                "duration": "4h",
                "max_drawdown_acceptable": "10%",
                "alternative": "ImprovedAdaptiveV3"
            }

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """Build detailed prompt for Claude"""

        tech = data.get("technical_indicators", {})
        price_24h = data.get("price_24h", {})

        return f"""You are an expert crypto trading AI. Analyze current market conditions and select the BEST strategy.

CURRENT MARKET DATA:
- Timestamp: {data.get('timestamp', 'unknown')}
- BTC Price: ${data.get('btc_price', 0):,.2f}
- 24h Change: {price_24h.get('change_percent', 0):.2f}%
- 24h High: ${price_24h.get('high', 0):,.2f}
- 24h Low: ${price_24h.get('low', 0):,.2f}
- Fear & Greed Index: {data.get('fear_greed_index', 50)} (0=Extreme Fear, 100=Extreme Greed)
- Funding Rate: {data.get('funding_rate', 0)*100:.4f}% every 8h
- RSI (14): {tech.get('rsi_14', 50):.2f}
- ADX (14): {tech.get('adx_14', 20):.2f}
- EMA 50: ${tech.get('ema_50', 0):,.0f}
- EMA 200: ${tech.get('ema_200', 0):,.0f}
- Volume Spike: {tech.get('volume_spike', False)}
- Market Regime: {data.get('regime', 'unknown')}

AVAILABLE STRATEGIES:

1. **ImprovedAdaptiveV3** (Mean Reversion - Conservative)
   - Best for: Ranging markets (ADX <25), neutral sentiment (F&G 30-70)
   - Performance: 100% win rate (backtest), 1-3% per trade, 0.12 trades/day
   - Risk: Very low
   - When to use: Neutral conditions, no clear edge elsewhere

2. **ContrarianbuyDips** (Aggressive Mean Reversion - NEW)
   - Best for: Extreme Fear (F&G <25), RSI <40, volume spike, capitulation
   - Performance: 70-80% win rate expected, 3-5% per trade, 0.3-0.5 trades/day
   - Risk: Medium
   - When to use: Extreme fear + technical confirmation
   - WARNING: NOT created yet - only recommend if VERY confident in setup

3. **TrendFollowingFixed** (Momentum - NEEDS FIXING)
   - Best for: Strong trends (ADX >30), momentum building, clear direction
   - Performance: 45-55% win rate expected, 5-15% per trade, 0.1-0.2 trades/day
   - Risk: High
   - When to use: Clear trend + volume confirmation
   - WARNING: Previously lost money in backtest, needs fixing before use

4. **RangeScalper** (High Frequency - NEW)
   - Best for: Low volatility (ADX <20), clear support/resistance
   - Performance: 60-70% win rate expected, 1-2% per trade, 1-2 trades/day
   - Risk: Low-Medium
   - When to use: Boring sideways markets
   - WARNING: NOT created yet - only recommend if conditions perfect

DECISION RULES:

1. **Extreme Fear Analysis:**
   - F&G <25 AND RSI <40 AND volume spike → STRONGLY favor ContrarianbuyDips
   - F&G <25 BUT RSI >40 OR no volume spike → ImprovedAdaptiveV3 (wait for better setup)
   - F&G <25 BUT ADX >50 → CAUTION: Strong trend, could fall further despite fear

2. **Trend Analysis:**
   - ADX >30 AND clear direction → Consider TrendFollowingFixed (if fixed)
   - ADX >50 → Very strong trend, mean reversion dangerous
   - NEVER deploy TrendFollowing during F&G <25 (catastrophic in bear markets)

3. **Range Analysis:**
   - ADX <20 AND low volatility → Consider RangeScalper
   - ADX <25 AND neutral conditions → Default to ImprovedAdaptiveV3

4. **Safety First:**
   - If uncertain or mixed signals → ImprovedAdaptiveV3 (proven, safe)
   - If new strategy not created yet → ImprovedAdaptiveV3
   - If extreme conditions but no confirmation → ImprovedAdaptiveV3

CURRENT SITUATION ASSESSMENT:
Based on the data above:
- Fear & Greed = {data.get('fear_greed_index', 50)} ({'Extreme Fear' if data.get('fear_greed_index', 50) < 25 else 'Fear' if data.get('fear_greed_index', 50) < 50 else 'Neutral' if data.get('fear_greed_index', 50) < 75 else 'Greed'})
- RSI = {tech.get('rsi_14', 50):.1f} ({'Oversold' if tech.get('rsi_14', 50) < 30 else 'Neutral' if tech.get('rsi_14', 50) < 70 else 'Overbought'})
- ADX = {tech.get('adx_14', 20):.1f} ({'Ranging' if tech.get('adx_14', 20) < 25 else 'Weak Trend' if tech.get('adx_14', 20) < 40 else 'Strong Trend'})

Respond ONLY with valid JSON (no markdown, no code blocks, no explanation):
{{
  "strategy": "strategy_name",
  "confidence": 1-10,
  "reasoning": "2-3 sentence explanation of why this strategy fits current conditions",
  "duration": "4h or 8h or 12h or 24h",
  "max_drawdown_acceptable": "5% or 10% or 15%",
  "alternative": "backup_strategy_if_primary_fails"
}}"""

    def validate_decision(self, decision: Dict[str, Any]) -> bool:
        """Validate AI decision has required fields and reasonable values"""
        required_fields = ["strategy", "confidence", "reasoning", "duration", "alternative"]

        # Check all required fields present
        for field in required_fields:
            if field not in decision:
                print(f"⚠️  Invalid decision: missing '{field}'")
                return False

        # Validate confidence range
        if not (1 <= decision["confidence"] <= 10):
            print(f"⚠️  Invalid confidence: {decision['confidence']} (must be 1-10)")
            return False

        # Validate strategy names
        valid_strategies = ["ImprovedAdaptiveV3", "ContrarianbuyDips", "TrendFollowingFixed", "RangeScalper"]
        if decision["strategy"] not in valid_strategies:
            print(f"⚠️  Invalid strategy: {decision['strategy']}")
            return False

        return True


def main():
    """Test the AI selector"""
    from market_data import MarketDataCollector

    print("="*60)
    print("AI STRATEGY SELECTOR TEST")
    print("="*60)

    # Fetch current market data
    collector = MarketDataCollector()
    market_data = collector.fetch_all()

    # Get AI recommendation
    selector = AIStrategySelector()
    decision = selector.select_strategy(market_data)

    # Display decision
    print("\n" + "="*60)
    print("AI RECOMMENDATION")
    print("="*60)
    print(f"Strategy: {decision['strategy']}")
    print(f"Confidence: {decision['confidence']}/10")
    print(f"Reasoning: {decision['reasoning']}")
    print(f"Duration: {decision['duration']}")
    print(f"Max Drawdown: {decision['max_drawdown_acceptable']}")
    print(f"Backup: {decision['alternative']}")
    print("="*60)

    # Save decision
    with open("logs/ai_decision_latest.json", "w") as f:
        json.dump({
            "timestamp": market_data["timestamp"],
            "market_data": market_data,
            "decision": decision
        }, f, indent=2)
    print("\n✅ Decision saved to logs/ai_decision_latest.json")


if __name__ == "__main__":
    main()
