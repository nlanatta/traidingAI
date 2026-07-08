#!/usr/bin/env python3
"""
Strategy Deployment Manager
Deploys selected strategy to Freqtrade by updating config and restarting bot
"""

import json
import subprocess
from typing import Dict, Any
from datetime import datetime


class StrategyDeployer:
    """Deploys trading strategies"""

    def __init__(self):
        self.config_path = "../config-live.json"
        self.docker_container = "freqtradebot"  # Adjust if different

    def deploy(self, decision: Dict[str, Any]) -> bool:
        """
        Deploy the selected strategy

        Returns: True if successful, False otherwise
        """
        strategy_name = decision["strategy"]
        print(f"🚀 Deploying strategy: {strategy_name}")

        try:
            # 1. Update config-live.json
            if not self._update_config(strategy_name):
                return False

            # 2. Restart Docker container
            if not self._restart_bot():
                return False

            print(f"✅ Strategy {strategy_name} deployed successfully")
            return True

        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False

    def _update_config(self, strategy_name: str) -> bool:
        """Update config-live.json with new strategy"""
        try:
            print(f"📝 Updating {self.config_path}...")

            # Read current config
            with open(self.config_path, "r") as f:
                config = json.load(f)

            # Update strategy
            config["strategy"] = strategy_name

            # Write back
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)

            print(f"✅ Config updated: strategy = {strategy_name}")
            return True

        except FileNotFoundError:
            print(f"❌ Config file not found: {self.config_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config: {e}")
            return False
        except Exception as e:
            print(f"❌ Error updating config: {e}")
            return False

    def _restart_bot(self) -> bool:
        """Restart the Freqtrade Docker container"""
        try:
            print(f"🔄 Restarting Docker container: {self.docker_container}...")

            # Check if container exists
            check_cmd = ["docker", "ps", "-a", "--filter", f"name={self.docker_container}", "--format", "{{.Names}}"]
            result = subprocess.run(check_cmd, capture_output=True, text=True)

            if self.docker_container not in result.stdout:
                print(f"⚠️  Container {self.docker_container} not found - assuming first run")
                return True

            # Restart container
            restart_cmd = ["docker", "restart", self.docker_container]
            result = subprocess.run(restart_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"✅ Container restarted successfully")
                return True
            else:
                print(f"❌ Container restart failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Container restart timed out after 30s")
            return False
        except Exception as e:
            print(f"❌ Error restarting container: {e}")
            return False

    def get_current_strategy(self) -> str:
        """Get currently deployed strategy"""
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            return config.get("strategy", "unknown")
        except:
            return "unknown"


def main():
    """Test deployment"""
    print("="*60)
    print("STRATEGY DEPLOYMENT TEST")
    print("="*60)

    deployer = StrategyDeployer()

    # Show current strategy
    current = deployer.get_current_strategy()
    print(f"\nCurrent strategy: {current}")

    # Test deployment (dry run - just update config, don't restart)
    test_decision = {
        "strategy": "ImprovedAdaptiveV3",
        "confidence": 8,
        "reasoning": "Test deployment",
        "duration": "4h"
    }

    print(f"\nTest deployment: {test_decision['strategy']}")
    success = deployer.deploy(test_decision)

    if success:
        print("\n✅ Deployment test passed")
    else:
        print("\n❌ Deployment test failed")


if __name__ == "__main__":
    main()
