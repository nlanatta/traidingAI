#!/usr/bin/env python3
"""
AI Strategy Selector - Main Orchestrator
Runs every 4-6 hours via cron to dynamically select and deploy optimal trading strategy
"""

import os
import json
import sys
from datetime import datetime
from market_data import MarketDataCollector
from deploy import StrategyDeployer

# Try local Claude CLI first, fall back to API
try:
    from ai_selector_local import AIStrategySelector
    AI_METHOD = "local"
except Exception:
    from ai_selector import AIStrategySelector
    AI_METHOD = "api"


class Logger:
    """Simple logger for decisions and deployments"""

    def __init__(self):
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def log_decision(self, market_data, decision, deployment_success):
        """Log AI decision and deployment result"""
        timestamp = datetime.utcnow().isoformat()

        # Save full decision log
        log_entry = {
            "timestamp": timestamp,
            "market_data": market_data,
            "decision": decision,
            "deployment": {
                "success": deployment_success,
                "strategy_deployed": decision["strategy"] if deployment_success else "failed"
            }
        }

        # Append to decisions log (JSONL format)
        with open(f"{self.log_dir}/decisions.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Update latest decision (single JSON file)
        with open(f"{self.log_dir}/ai_decision_latest.json", "w") as f:
            json.dump(log_entry, f, indent=2)

        # Human-readable log
        self._log_human_readable(timestamp, market_data, decision, deployment_success)

    def _log_human_readable(self, timestamp, market_data, decision, success):
        """Append human-readable log entry"""
        tech = market_data.get("technical_indicators", {})
        price_24h = market_data.get("price_24h", {})

        log_line = f"""
{'='*80}
TIMESTAMP: {timestamp}
MARKET CONDITIONS:
  BTC Price: ${market_data.get('btc_price', 0):,.2f} ({price_24h.get('change_percent', 0):.2f}% 24h)
  Fear & Greed Index: {market_data.get('fear_greed_index', 50)}
  RSI (14): {tech.get('rsi_14', 50):.2f}
  ADX (14): {tech.get('adx_14', 20):.2f}
  Regime: {market_data.get('regime', 'unknown')}

AI DECISION:
  Strategy: {decision['strategy']}
  Confidence: {decision['confidence']}/10
  Reasoning: {decision['reasoning']}
  Duration: {decision['duration']}
  Max Drawdown: {decision.get('max_drawdown_acceptable', 'N/A')}
  Backup: {decision.get('alternative', 'N/A')}

DEPLOYMENT: {'SUCCESS' if success else 'FAILED'}
{'='*80}
"""
        with open(f"{self.log_dir}/decisions.txt", "a") as f:
            f.write(log_line)


def main():
    """Main orchestration logic"""
    print("="*80)
    print("AI STRATEGY SELECTOR - Starting Run")
    print(f"Time: {datetime.utcnow().isoformat()} UTC")
    print(f"AI Method: {AI_METHOD.upper()} ({'Local Claude CLI' if AI_METHOD == 'local' else 'Anthropic API'})")
    print("="*80)

    try:
        # Step 1: Collect market data
        print("\n[1/4] Collecting market data...")
        collector = MarketDataCollector()
        market_data = collector.fetch_all()

        # Step 2: Get AI recommendation
        print("\n[2/4] Getting AI recommendation...")
        selector = AIStrategySelector()
        decision = selector.select_strategy(market_data)

        # Validate decision
        if not selector.validate_decision(decision):
            print("❌ Invalid AI decision - aborting")
            sys.exit(1)

        # Step 3: Deploy strategy
        print("\n[3/4] Deploying strategy...")
        deployer = StrategyDeployer()
        current_strategy = deployer.get_current_strategy()

        if current_strategy == decision["strategy"]:
            print(f"✅ Strategy {decision['strategy']} already deployed - no change needed")
            deployment_success = True
        else:
            print(f"🔄 Switching: {current_strategy} → {decision['strategy']}")
            deployment_success = deployer.deploy(decision)

        # Step 4: Log everything
        print("\n[4/4] Logging decision...")
        logger = Logger()
        logger.log_decision(market_data, decision, deployment_success)

        # Summary
        print("\n" + "="*80)
        if deployment_success:
            print(f"✅ SUCCESS: {decision['strategy']} deployed (confidence: {decision['confidence']}/10)")
            print(f"Reasoning: {decision['reasoning']}")
            print(f"Duration: {decision['duration']}")
            print("="*80)
            sys.exit(0)
        else:
            print("❌ FAILED: Deployment unsuccessful")
            print("="*80)
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
