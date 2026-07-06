# Freqtrade POC Guide - Quick Start

> **⚠️ NOTE:** This was the initial POC guide. See [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) for current deployment including A/B testing setup.

## What We're Doing

1. ✅ Downloaded Freqtrade Docker image
2. ✅ Created paper trading config (`config-poc.json`)
3. 🔄 Downloading 30 days of BTC/USDT + ETH/USDT data
4. ⏳ Next: Run backtest with example strategy
5. ⏳ Next: Start paper trading

---

## Step 3: Run Your First Backtest

Once data download completes (watch for notification), run:

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# Backtest with example strategy
docker-compose run --rm freqtrade backtesting \
    --strategy SampleStrategy \
    --config user_data/config-poc.json \
    --timerange 20240603-20240703
```

**What to look for:**
- Total profit % (positive is good, but don't get excited yet)
- Win rate (40-60% is typical)
- Sharpe ratio (>1.0 is good)
- Max drawdown (<20% is manageable)

---

## Step 4: Start Paper Trading

If backtest looks reasonable:

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# Start paper trading (NO REAL MONEY)
docker-compose run --rm freqtrade trade \
    --strategy SampleStrategy \
    --config user_data/config-poc.json
```

**What happens:**
- Bot connects to Binance for live price data
- Simulates trades with $10,000 virtual USDT
- Logs every trade to database
- NO real money involved

**To stop:** Press `Ctrl+C`

---

## Step 5: View Results

While paper trading is running (in another terminal):

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# View current trades
docker-compose run --rm freqtrade show-trades --days 1

# View performance
docker-compose run --rm freqtrade profit --days 7
```

---

## Config Explained

```json
{
  "dry_run": true,              // PAPER TRADING (no real money)
  "dry_run_wallet": 10000,      // Virtual $10K USDT
  "max_open_trades": 3,         // Max 3 concurrent positions
  "stake_amount": 100,          // Invest 100 USDT per trade
  
  "exchange": {
    "name": "binance",
    "key": "",                  // Empty = read-only (paper trading)
    "secret": "",
    "pair_whitelist": [
      "BTC/USDT",
      "ETH/USDT"
    ]
  }
}
```

---

## Next Steps After POC

1. **Study the strategy code:**
   ```bash
   cat freqtrade/templates/sample_strategy.py
   ```

2. **Modify one parameter** (e.g., RSI threshold)

3. **Re-run backtest** to see impact

4. **Let paper trading run for 24-48 hours**

5. **Analyze results** - compare paper trading to backtest

---

## Key Files

- **Config:** `user_data/config-poc.json`
- **Data:** `user_data/data/binance/`
- **Database:** `user_data/tradesv3.sqlite` (stores all trades)
- **Logs:** `user_data/logs/freqtrade.log`
- **Strategies:** `freqtrade/templates/sample_strategy.py`

---

## Common Commands

```bash
# Download more data
docker-compose run --rm freqtrade download-data \
    --exchange binance \
    --pairs SOL/USDT \
    --timeframe 5m \
    --days 30

# List available strategies
docker-compose run --rm freqtrade list-strategies

# Backtest different timerange
docker-compose run --rm freqtrade backtesting \
    --strategy SampleStrategy \
    --timerange 20240601-20240615

# Plot backtest results (creates HTML chart)
docker-compose run --rm freqtrade plot-dataframe \
    --strategy SampleStrategy \
    --pairs BTC/USDT \
    --indicators1 rsi,macd \
    --timerange 20240601-20240703
```

---

## Safety Reminders

- ✅ **dry_run: true** = NO REAL MONEY
- ✅ Empty API keys = Read-only access
- ✅ Virtual $10K balance for simulation
- ❌ **DO NOT** change `dry_run` to `false` yet
- ❌ **DO NOT** add real API keys until strategy is proven profitable

---

## What Success Looks Like (After 3-6 Months Paper Trading)

- ✅ Positive cumulative P&L over 100+ trades
- ✅ Sharpe ratio ≥ 1.0
- ✅ Max drawdown ≤ 20%
- ✅ Can explain WHY strategy has edge
- ✅ Backtest and paper trading results align

**If all above true:** Consider live trading with small capital ($50-100 per trade)

**If any false:** Strategy is not profitable, try different approach or stop

---

## Getting Help

- **Discord:** https://discord.gg/freqtrade (10K+ members)
- **Docs:** https://www.freqtrade.io/
- **Strategies:** https://github.com/freqtrade/freqtrade-strategies

---

## Quick Troubleshooting

**"No data available"**
→ Run download-data command again

**"Exchange returned an error"**
→ Check internet connection
→ Binance may rate-limit, wait 1 minute and retry

**Bot exits immediately**
→ Check logs: `cat user_data/logs/freqtrade.log`

**"Invalid config"**
→ Validate JSON syntax: https://jsonlint.com/

---

**Current Status:**
- ✅ Data downloaded (30 days BTC/USDT + ETH/USDT)
- ✅ Backtest complete: -0.02% profit over 30 days (87% win rate, but stop-losses killed gains)
- ⏳ Next: Start paper trading to see live performance

**Backtest command (for reference):**
```bash
docker-compose run --rm freqtrade backtesting \
    --strategy SampleStrategy \
    --config user_data/config-poc.json \
    --timerange 20260603-20260703
```
