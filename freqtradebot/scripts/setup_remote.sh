#!/bin/bash
# Quick setup for remote deployment

set -e

echo "==========================================="
echo "AI Trading System - Remote Setup"
echo "==========================================="
echo ""

# Check if .env exists
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    source .env

    if [ -z "$DROPLET_IP" ]; then
        echo "⚠️  DROPLET_IP not set in .env"
        echo ""
        echo "Please edit .env and add:"
        echo "  DROPLET_IP=your.droplet.ip"
        echo "  SSH_KEY_PATH=~/.ssh/id_do"
        echo "  SSH_USER=root"
        echo "  REMOTE_PATH=~/freqtradebot"
        exit 1
    fi

    echo "  Droplet IP: $DROPLET_IP"
    echo "  SSH Key: ${SSH_KEY_PATH:-~/.ssh/id_do}"
    echo "  SSH User: ${SSH_USER:-root}"
    echo "  Remote Path: ${REMOTE_PATH:-~/freqtradebot}"
    echo ""
else
    echo "❌ .env file not found"
    echo ""
    echo "Creating .env from example..."
    cp .env.example .env
    echo ""
    echo "Please edit .env and add your droplet details:"
    echo "  nano .env"
    echo ""
    echo "Required fields:"
    echo "  DROPLET_IP=your.droplet.ip"
    echo "  SSH_KEY_PATH=~/.ssh/id_do"
    exit 1
fi

# Test SSH connection
echo "Testing SSH connection..."
SSH_KEY="${SSH_KEY_PATH:-~/.ssh/id_do}"
SSH_KEY="${SSH_KEY/#\~/$HOME}"  # Expand ~
SSH_USER="${SSH_USER:-root}"

if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
    "$SSH_USER@$DROPLET_IP" "echo 'SSH connection successful'" 2>/dev/null; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check droplet IP: ping $DROPLET_IP"
    echo "2. Check SSH key exists: ls -la $SSH_KEY"
    echo "3. Test manually: ssh -i $SSH_KEY $SSH_USER@$DROPLET_IP"
    exit 1
fi

# Test remote path exists
echo ""
echo "Checking remote path..."
REMOTE_PATH="${REMOTE_PATH:-~/freqtradebot}"

if ssh -i "$SSH_KEY" "$SSH_USER@$DROPLET_IP" \
    "test -d $REMOTE_PATH && echo 'exists'" | grep -q 'exists'; then
    echo "✅ Remote path exists: $REMOTE_PATH"
else
    echo "⚠️  Remote path not found: $REMOTE_PATH"
    echo ""
    echo "Do you need to create it?"
    echo "  ssh -i $SSH_KEY $SSH_USER@$DROPLET_IP"
    echo "  mkdir -p $REMOTE_PATH"
    exit 1
fi

# Test Docker on remote
echo ""
echo "Checking Docker on remote..."
DOCKER_SERVICE="${DOCKER_SERVICE:-freqtrade-live}"
if ssh -i "$SSH_KEY" "$SSH_USER@$DROPLET_IP" \
    "cd $REMOTE_PATH && docker compose ps" 2>/dev/null | grep -q "$DOCKER_SERVICE"; then
    echo "✅ Docker container found: $DOCKER_SERVICE"
else
    echo "⚠️  Docker container not running: $DOCKER_SERVICE"
    echo ""
    echo "You may need to start it:"
    echo "  ssh -i $SSH_KEY $SSH_USER@$DROPLET_IP"
    echo "  cd $REMOTE_PATH"
    echo "  docker compose up -d $DOCKER_SERVICE"
fi

# Test deployment
echo ""
echo "Testing deployment..."
if python3 deploy_remote.py 2>&1 | grep -q 'Deployment test passed'; then
    echo "✅ Deployment test passed"
else
    echo "⚠️  Deployment test had issues (check output above)"
fi

echo ""
echo "==========================================="
echo "Setup Complete!"
echo "==========================================="
echo ""
echo "Next steps:"
echo "1. Test market analysis: python3 analyze_and_deploy.py"
echo "2. Test manual deployment: python3 deploy_remote.py"
echo "3. Scheduler is already running (every 4h at :07)"
echo ""
echo "Monitor:"
echo "  • Decision log: cat logs/decisions.txt"
echo "  • Market data: cat logs/market_analysis_latest.txt"
echo "  • Remote bot: ssh -i $SSH_KEY $SSH_USER@$DROPLET_IP 'docker compose logs -f freqtrade'"
echo ""
