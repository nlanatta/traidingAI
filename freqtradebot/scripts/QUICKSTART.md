# AI Trading System - Quick Start

Get AI-powered dynamic strategy selection running in 5 minutes.

## Phase 1 Status: READY TO TEST ✅

All core components built:
- ✅ Market data collector (Binance + Fear & Greed Index + technical indicators)
- ✅ AI selector (Claude API decision engine)
- ✅ Deployment manager (config update + Docker restart)
- ✅ Orchestrator (full pipeline)
- ✅ Logger (decisions + deployments)

## 5-Minute Setup

### 1. Get Anthropic API Key (1 min)
Go to https://console.anthropic.com/ and copy your API key.

### 2. Configure Environment (30 sec)
```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/scripts
cp .env.example .env
nano .env  # Paste your API key
```

### 3. Test AI Selector (1 min)
```bash
python3 ai_selector.py
```

Expected output:
```
🧠 Asking AI to analyze market conditions...
✅ AI Decision: ImprovedAdaptiveV3 (confidence: 8/10)
```

### 4. Run Full Pipeline (1 min)
```bash
python3 run_ai_selector.py
```

This will:
1. Fetch real-time market data
2. Get AI recommendation
3. Update config
4. Deploy strategy
5. Log everything

### 5. Set Up Automation (1 min)
```bash
./setup_cron.sh
```

Done! AI will now select optimal strategy every 4 hours.

## Monitor Your AI Trader

### Latest Decision
```bash
cat logs/ai_decision_latest.json | jq .
```

### Decision History
```bash
tail -20 logs/decisions.txt
```

### Live Monitoring
```bash
tail -f logs/cron.log
```

## What It Does

Every 4 hours, the AI:

1. **Analyzes Market**: BTC price, Fear & Greed Index, RSI, ADX, EMA 50/200, volume, funding rate
2. **Selects Strategy**: ImprovedAdaptiveV3 (conservative) or others when conditions warrant
3. **Deploys Automatically**: Updates config-live.json and restarts bot
4. **Logs Everything**: Full decision reasoning + market context

## Example Decision Log

```
MARKET CONDITIONS:
  BTC Price: $61,919.72 (-3.27% 24h)
  Fear & Greed Index: 20 (Extreme Fear)
  RSI (14): 30.12 (oversold)
  ADX (14): 65.43 (strong trend)
  Regime: bull_trending

AI DECISION:
  Strategy: ImprovedAdaptiveV3
  Confidence: 8/10
  Reasoning: Extreme Fear (20) + oversold RSI (30.12) suggest contrarian 
    opportunity, but ADX (65.43) indicates very strong trend. Mean reversion 
    dangerous in strong trends. Staying with proven conservative strategy 
    until trend weakens (ADX <40). Will reassess in 4h.
  Duration: 4h
  
DEPLOYMENT: SUCCESS
```

## Safety Features

✅ **Validated Decisions**: AI output validated before deployment
✅ **Fallback**: If API fails → defaults to safe strategy
✅ **No Repeated Restarts**: If strategy unchanged → skips deployment
✅ **Full Logging**: Every decision logged with reasoning
✅ **Error Handling**: Graceful failures, no system crashes

## Current Strategy Library

1. **ImprovedAdaptiveV3** ✅ - Conservative mean reversion (100% win rate backtest)
2. **ContrarianbuyDips** 🚧 - Aggressive buying in Extreme Fear (Week 2)
3. **TrendFollowingFixed** 🚧 - Momentum riding (needs fixing, Week 2)
4. **RangeScalper** 🚧 - High-frequency scalping (Week 2)

AI will ONLY deploy ImprovedAdaptiveV3 until other strategies are ready.

## Target Performance

| Metric | Current (Static) | Target (AI Dynamic) |
|--------|------------------|---------------------|
| Annual Return | 8.4% | 20-30% |
| Strategy Selection | Manual, static | AI, every 4h |
| Market Adaptation | None | Automatic |
| Extreme Events | Missed opportunities | Captured via ContrarianbuyDips |
| Strong Trends | Underperforming | Better via TrendFollowing |

## Week 2 Roadmap

1. Create ContrarianbuyDips.py
2. Fix TrendFollowingFixed.py
3. Create RangeScalper.py
4. Backtest all 3 strategies
5. Monitor AI switching for 24 hours

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
- Check `.env` file exists in scripts/ directory
- Format: `ANTHROPIC_API_KEY=sk-ant-api03-...`

**AI always picks same strategy**
- This is correct if market conditions similar
- AI will switch when conditions warrant it
- Check `logs/decisions.txt` for reasoning

**Container restart fails**
- First run: Normal (container may not exist yet)
- Start manually: `docker-compose up -d`

## Next Test

Wait 4 hours for next automatic run, or manually trigger:
```bash
python3 run_ai_selector.py
```

Watch logs:
```bash
tail -f logs/decisions.txt
```

---

**Phase 1 Complete**: Autonomous AI strategy selector operational! 🚀
