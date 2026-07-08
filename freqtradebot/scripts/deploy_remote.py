#!/usr/bin/env python3
"""
Remote Deployment Manager
Deploys strategy to DigitalOcean droplet via SSH
"""

import json
import subprocess
import os
from typing import Dict, Any
from datetime import datetime


class RemoteDeployer:
    """Deploys trading strategies to remote server"""

    def __init__(self):
        # Load SSH config
        self.ssh_host = os.getenv("DROPLET_IP", "")
        self.ssh_key = os.getenv("SSH_KEY_PATH", "~/.ssh/id_do")
        self.ssh_user = os.getenv("SSH_USER", "root")
        self.remote_path = os.getenv("REMOTE_PATH", "~/freqtradebot")
        self.service_name = os.getenv("DOCKER_SERVICE", "freqtrade-live")

        if not self.ssh_host:
            print("⚠️  DROPLET_IP not set in .env - will use dry-run mode")
            self.dry_run = True
        else:
            self.dry_run = False
            self.ssh_key = os.path.expanduser(self.ssh_key)

    def deploy(self, strategy_name: str, decision: Dict[str, Any]) -> bool:
        """
        Deploy the selected strategy to remote server

        Returns: True if successful, False otherwise
        """
        print(f"🚀 Deploying strategy: {strategy_name}")

        if self.dry_run:
            print("📝 DRY RUN MODE - No remote deployment (set DROPLET_IP in .env to enable)")
            return self._dry_run_deploy(strategy_name, decision)

        try:
            # 1. Check current strategy
            current = self.get_current_strategy()
            if current == strategy_name:
                print(f"✅ Strategy {strategy_name} already deployed - no change needed")
                return True

            # 2. SAFETY CHECK: Check for open trades
            open_trades = self._check_open_trades()
            if open_trades is None:
                print("⚠️  Could not check open trades - proceeding with caution")
            elif open_trades > 0:
                print(f"🛑 SAFETY: {open_trades} trade(s) currently open")
                print(f"   Skipping strategy switch: {current} → {strategy_name}")
                print(f"   Reason: Letting {current} complete its trades naturally")
                print(f"   Will retry in 4 hours when trades close")
                return False

            print(f"✅ No open trades - safe to switch strategies")

            # 3. Update local config first
            if not self._update_local_config(strategy_name):
                return False

            # 4. Sync config to remote server
            if not self._sync_to_remote():
                return False

            # 5. Restart remote Docker container
            if not self._restart_remote_bot():
                return False

            print(f"✅ Strategy {strategy_name} deployed successfully to remote server")
            return True

        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False

    def _update_local_config(self, strategy_name: str) -> bool:
        """Update local config-live.json"""
        try:
            config_path = "../config-live.json"
            print(f"📝 Updating local config: {config_path}")

            # Read current config
            with open(config_path, "r") as f:
                config = json.load(f)

            # Update strategy
            config["strategy"] = strategy_name

            # Write back
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            print(f"✅ Local config updated: strategy = {strategy_name}")
            return True

        except Exception as e:
            print(f"❌ Error updating local config: {e}")
            return False

    def _sync_to_remote(self) -> bool:
        """Sync local config to remote server via rsync"""
        try:
            print(f"📤 Syncing config to {self.ssh_user}@{self.ssh_host}...")

            cmd = [
                "rsync",
                "-avz",
                "-e", f"ssh -i {self.ssh_key}",
                "--include", "config-live.json",
                "--include", "strategies/",
                "--include", "strategies/*.py",
                "--exclude", "*",
                "../",
                f"{self.ssh_user}@{self.ssh_host}:{self.remote_path}/"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print("✅ Config synced to remote server")
                return True
            else:
                print(f"❌ Rsync failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Rsync timeout after 30s")
            return False
        except Exception as e:
            print(f"❌ Error syncing to remote: {e}")
            return False

    def _restart_remote_bot(self) -> bool:
        """Restart Freqtrade Docker container on remote server"""
        try:
            print(f"🔄 Restarting {self.service_name} on {self.ssh_host}...")

            cmd = [
                "ssh",
                "-i", self.ssh_key,
                f"{self.ssh_user}@{self.ssh_host}",
                f"cd {self.remote_path} && docker compose restart {self.service_name}"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print("✅ Remote bot restarted successfully")
                return True
            else:
                print(f"❌ Remote restart failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Remote restart timeout after 60s")
            return False
        except Exception as e:
            print(f"❌ Error restarting remote bot: {e}")
            return False

    def _dry_run_deploy(self, strategy_name: str, decision: Dict[str, Any]) -> bool:
        """Simulate deployment in dry-run mode"""
        print(f"\n{'='*60}")
        print("DRY RUN - Would deploy:")
        print(f"{'='*60}")
        print(f"Strategy: {strategy_name}")
        print(f"Confidence: {decision.get('confidence', 'N/A')}/10")
        print(f"Reasoning: {decision.get('reasoning', 'N/A')}")
        print(f"\nTo enable real deployment:")
        print("1. Add to scripts/.env:")
        print("   DROPLET_IP=your.droplet.ip")
        print("   SSH_KEY_PATH=~/.ssh/id_do")
        print("   SSH_USER=root")
        print("   REMOTE_PATH=~/freqtradebot")
        print(f"{'='*60}\n")
        return True

    def get_current_strategy(self) -> str:
        """Get currently deployed strategy"""
        try:
            with open("../config-live.json", "r") as f:
                config = json.load(f)
            return config.get("strategy", "unknown")
        except:
            return "unknown"

    def _check_open_trades(self) -> int:
        """
        Check for open trades on remote server

        Returns: Number of open trades, or None if check failed
        """
        try:
            cmd = [
                "ssh",
                "-i", self.ssh_key,
                "-o", "ConnectTimeout=10",
                f"{self.ssh_user}@{self.ssh_host}",
                f"cd {self.remote_path} && docker compose exec -T {self.service_name} "
                f"freqtrade show_trades --open | grep -c 'open' || echo '0'"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                try:
                    count = int(result.stdout.strip())
                    return count
                except ValueError:
                    return None
            else:
                return None

        except Exception as e:
            print(f"⚠️  Error checking open trades: {e}")
            return None

    def test_connection(self) -> bool:
        """Test SSH connection to remote server"""
        if self.dry_run:
            print("⚠️  Dry-run mode - no remote connection to test")
            return False

        try:
            print(f"Testing SSH connection to {self.ssh_user}@{self.ssh_host}...")

            cmd = [
                "ssh",
                "-i", self.ssh_key,
                "-o", "ConnectTimeout=10",
                f"{self.ssh_user}@{self.ssh_host}",
                "echo 'Connection successful'"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                print("✅ SSH connection successful")
                return True
            else:
                print(f"❌ SSH connection failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


def main():
    """Test remote deployment"""
    print("="*60)
    print("REMOTE DEPLOYMENT TEST")
    print("="*60)

    deployer = RemoteDeployer()

    # Test connection first
    if not deployer.dry_run:
        deployer.test_connection()

    # Show current strategy
    current = deployer.get_current_strategy()
    print(f"\nCurrent strategy: {current}")

    # Test deployment
    test_decision = {
        "strategy": "ImprovedAdaptiveV3",
        "confidence": 8,
        "reasoning": "Test deployment",
        "duration": "4h"
    }

    print(f"\nTest deployment: {test_decision['strategy']}")
    success = deployer.deploy(test_decision['strategy'], test_decision)

    if success:
        print("\n✅ Deployment test passed")
    else:
        print("\n❌ Deployment test failed")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
