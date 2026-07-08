#!/bin/bash
# Setup cron job for AI Strategy Selector
# Run this after testing the AI selector manually

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_CMD="0 */4 * * * cd $SCRIPT_DIR && python3 run_ai_selector.py >> logs/cron.log 2>&1"

echo "==========================================="
echo "AI Strategy Selector - Cron Setup"
echo "==========================================="
echo ""
echo "This will add a cron job to run the AI selector every 4 hours."
echo "Schedule: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC"
echo ""
echo "Cron command to be added:"
echo "$CRON_CMD"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_ai_selector.py"; then
    echo "⚠️  Cron job already exists!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "run_ai_selector.py"
    echo ""
    read -p "Replace existing cron job? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    # Remove existing cron job
    crontab -l | grep -v "run_ai_selector.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "Verify installation:"
echo "  crontab -l"
echo ""
echo "Monitor logs:"
echo "  tail -f $SCRIPT_DIR/logs/cron.log"
echo "  tail -f $SCRIPT_DIR/logs/decisions.txt"
echo ""
echo "Remove cron job:"
echo "  crontab -l | grep -v 'run_ai_selector.py' | crontab -"
echo ""
echo "==========================================="
echo "Next steps:"
echo "1. Wait for next scheduled run (check: date)"
echo "2. Or manually test: python3 run_ai_selector.py"
echo "3. Monitor: tail -f logs/cron.log"
echo "==========================================="
