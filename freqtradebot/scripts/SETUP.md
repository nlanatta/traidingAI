# AI Trading System - Setup Guide

Complete setup instructions for Phase 1: AI Strategy Selector

## Prerequisites

✅ Already installed:
- Python 3.x
- Docker (for Freqtrade)
- All dependencies (`pip3 install -r requirements.txt`)

## Setup Steps

### 1. Create API Key Environment File

Copy the example and add your Anthropic API key:

```bash
cd scripts
cp .env.example .env
```

Edit `.env` and add your API key:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

Get your key from: https://console.anthropic.com/

### 2. Test Market Data Collection

```bash
cd scripts
python3 market_data.py
```

Expected output:
```
📊 Fetching market data...
✅ Market data collected: BTC=$XX,XXX, F&G=XX
...
✅ Data saved to logs/market_data_latest.json
```

### 3. Test AI Selector (Manual Run)

```bash
python3 ai_selector.py
```

Expected output:
```
🧠 Asking AI to analyze market conditions...
✅ AI Decision: ImprovedAdaptiveV3 (confidence: 8/10)
...
✅ Decision saved to logs/ai_decision_latest.json
```

### 4. Test Deployment (Dry Run)

```bash
python3 deploy.py
```

This will update `config-live.json` but NOT restart Docker yet (first test).

### 5. Test Full Pipeline

```bash
python3 run_ai_selector.py
```

This runs the complete workflow:
1. Fetch market data
2. Get AI recommendation
3. Update config
4. Restart Docker container
5. Log everything

### 6. Set Up Cron Job

Run AI selector every 4 hours:

```bash
# Open crontab
crontab -e

# Add this line (adjust path):
0 */4 * * * cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/scripts && python3 run_ai_selector.py >> logs/cron.log 2>&1
```

This runs at: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC

**Alternative: Every 6 hours (less aggressive)**
```
0 */6 * * * cd /path/to/scripts && python3 run_ai_selector.py >> logs/cron.log 2>&1
```

Verify cron is working:
```bash
# Check cron is running
crontab -l

# Monitor logs
tail -f logs/cron.log
tail -f logs/decisions.txt
```

## File Structure

```
freqtradebot/
├── config-live.json          # Updated by deploy.py
├── strategies/
│   ├── ImprovedAdaptiveV3.py
│   ├── ContrarianbuyDips.py  # TODO: Create in Week 2
│   ├── TrendFollowingFixed.py # TODO: Fix in Week 2
│   └── RangeScalper.py       # TODO: Create in Week 2
├── scripts/
│   ├── .env                  # YOUR API KEYS (never commit!)
│   ├── .env.example
│   ├── requirements.txt
│   ├── market_data.py        # ✅ Working
│   ├── ai_selector.py        # ✅ Ready to test
│   ├── deploy.py             # ✅ Ready to test
│   ├── run_ai_selector.py    # ✅ Ready to test
│   └── logs/
│       ├── market_data_latest.json
│       ├── ai_decision_latest.json
│       ├── decisions.jsonl   # Full history
│       ├── decisions.txt     # Human readable
│       └── cron.log
└── AI-TRADING-PLAN.md
```

## Monitoring

### Check Latest Decision
```bash
cat logs/ai_decision_latest.json | jq .
```

### View Decision History
```bash
tail -20 logs/decisions.txt
```

### Watch Live
```bash
watch -n 60 'cat logs/ai_decision_latest.json | jq ".decision"'
```

## Safety Features

✅ **Validation**: AI decisions are validated before deployment
✅ **Fallback**: If Claude API fails, defaults to safe strategy (ImprovedAdaptiveV3)
✅ **Logging**: All decisions logged with full market context
✅ **No-op optimization**: If strategy already deployed, skips restart
✅ **Error handling**: Deployment failures logged, doesn't break the system

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Make sure `.env` file exists in `scripts/` directory
- Check the file has correct format: `ANTHROPIC_API_KEY=sk-ant-...`

### "ModuleNotFoundError"
```bash
pip3 install -r requirements.txt
```

### "Container not found"
- First time: Deploy will just update config, won't restart container
- Manually start: `docker-compose up -d`

### AI selector returns same strategy every time
- This is correct behavior if market conditions haven't changed
- Check `logs/decisions.txt` to see reasoning
- AI will switch when conditions warrant it

## Next Steps (Week 2)

1. Create 3 new strategies:
   - `ContrarianbuyDips.py` - Aggressive mean reversion for F&G <25
   - `TrendFollowingFixed.py` - Fix existing trend following strategy
   - `RangeScalper.py` - High-frequency for low volatility

2. Backtest all strategies on 105-day period

3. Monitor first 24 hours of automated AI selection

## Target Performance

**Phase 1 Goal**: 20-30% annual return
- Current baseline: 8.4% annual (ImprovedAdaptiveV3 only)
- With dynamic switching: Expected 20-30% annual
- Success metric: 2-3x improvement over static strategy

## Support

Check `AI-TRADING-PLAN.md` for full implementation details.
