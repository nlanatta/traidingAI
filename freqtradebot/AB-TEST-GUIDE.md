# A/B Testing: SampleStrategy vs CustomSampleStrategy

> **⚠️ NOTE:** This content has been merged into [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) for easier maintenance. Use that guide instead.

## What We're Testing

**Hypothesis:** Adding an ADX < 25 filter will prevent catastrophic stop-losses during trending markets, improving overall profitability.

### Strategy A: SampleStrategy (Baseline)
- Mean-reversion using RSI + TEMA + Bollinger Bands
- **No trend filter** - trades in all market conditions
- Backtest: 87% win rate, but -$2.27 total (3 stop-losses wiped gains)

### Strategy B: CustomSampleStrategy (Test)
- Same as Strategy A, but adds `ADX < 25` filter
- **Only trades in ranging markets** (ADX < 25)
- **Avoids trending markets** where mean-reversion fails

---

## Setup

### 1. Files Created

```
user_data/
├── strategies/
│   ├── SampleStrategy.py           # Original (baseline)
│   └── CustomSampleStrategy.py     # With ADX filter (test)
├── config.json                     # Config for SampleStrategy
├── config-custom.json              # Config for CustomSampleStrategy
├── tradesv3.sqlite                 # Database for SampleStrategy
├── tradesv3-custom.sqlite          # Database for CustomSampleStrategy (will be created)
└── logs/
    ├── freqtrade.log               # Logs for SampleStrategy
    └── freqtrade-custom.log        # Logs for CustomSampleStrategy
```

### 2. Docker Containers

- **freqtrade** (port 8080) - runs SampleStrategy
- **freqtrade-custom** (port 8081) - runs CustomSampleStrategy

Both containers share the same `user_data/` folder but use separate databases and logs.

---

## Deployment Steps

### Local Testing First

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# Start both strategies locally
docker compose up -d

# Check logs for both
docker compose logs -f freqtrade          # SampleStrategy
docker compose logs -f freqtrade-custom   # CustomSampleStrategy

# Compare results after a few hours
./compare-strategies.sh
```

### Deploy to DigitalOcean

```bash
# From LOCAL machine - sync everything to droplet
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@YOUR_DROPLET_IP:~/freqtradebot/

# SSH into droplet
ssh -i ~/.ssh/id_do root@YOUR_DROPLET_IP

# Go to freqtrade directory
cd ~/freqtradebot/freqtrade

# Start BOTH containers
docker compose up -d

# Verify both are running
docker compose ps

# Check logs
docker compose logs -f freqtrade          # SampleStrategy
docker compose logs -f freqtrade-custom   # CustomSampleStrategy
```

---

## Monitoring

### Check Status

```bash
# On droplet
cd ~/freqtradebot/freqtrade

# View both containers
docker compose ps

# Check memory usage (1GB should handle both)
free -h

# Compare strategies
./compare-strategies.sh
```

### Daily Comparison

Run `./compare-strategies.sh` daily to see:
- Total trades (CustomSampleStrategy may have fewer)
- Win rate (should be similar or better)
- **Worst trade** (key metric - should avoid -10% stop-losses)
- Total profit (after 20-30 trades, should be positive)

---

## Expected Results

### After 3-5 Days (20-30 trades each):

#### Scenario 1: ADX Filter Works ✅
- **SampleStrategy**: 87% win rate, but 2-3 stop-losses wipe gains → net negative
- **CustomSampleStrategy**: 70-80% win rate, but NO catastrophic stop-losses → net positive
- **Winner**: CustomSampleStrategy (fewer trades, but profitable)

#### Scenario 2: ADX Filter Too Restrictive ❌
- **SampleStrategy**: Many trades, some stop-losses, net slightly positive
- **CustomSampleStrategy**: Very few trades (ADX < 25 too strict), can't reach statistical validity
- **Winner**: SampleStrategy (more opportunities)

#### Scenario 3: Both Fail ⚠️
- Both strategies hit multiple stop-losses
- Market conditions not suitable for mean-reversion
- **Action**: Try different strategy type (trend-following instead)

---

## Decision Criteria (After 20-30 Trades Each)

### Keep CustomSampleStrategy If:
- ✅ Total profit > SampleStrategy
- ✅ Worst trade > -5% (avoiding catastrophic stop-losses)
- ✅ Win rate ≥ 70%
- ✅ Profit factor ≥ 1.5

### Keep SampleStrategy If:
- ✅ CustomSampleStrategy has < 10 trades (too restrictive)
- ✅ Both have similar performance (ADX filter not helping)

### Try Different Strategy If:
- ❌ Both strategies net negative after 30 trades
- ❌ Both hitting multiple -10% stop-losses
- ❌ Mean-reversion not working in current market

---

## Adding More Pairs (Speed Up Testing)

To get 20-30 trades faster, add more pairs to BOTH configs:

```json
// In config.json and config-custom.json
"pair_whitelist": [
  "BTC/USDT",
  "ETH/USDT",
  "SOL/USDT",
  "ADA/USDT",
  "DOT/USDT",
  "LINK/USDT"
]
```

Then restart:
```bash
docker compose restart
```

**Expected:** 2-3× more trades per day (statistical validity in 2-3 days instead of 5-7 days)

---

## Stopping the Test

```bash
# Stop both containers
docker compose down

# Download databases for analysis
scp root@YOUR_DROPLET_IP:~/freqtradebot/freqtrade/user_data/tradesv3*.sqlite ~/Downloads/

# Run final comparison
./compare-strategies.sh
```

---

## Cost Impact

Running 2 containers instead of 1:
- **512 MB droplet**: Will crash (not enough memory)
- **1 GB droplet**: Should work but monitor with `free -h`
- **2 GB droplet**: Safe ($12/mo)

**Current setup**: 1GB droplet - should handle both strategies.

If memory issues: upgrade to 2GB or test one strategy at a time.

---

## Quick Reference Commands

```bash
# Compare strategies
./compare-strategies.sh

# View logs
docker compose logs -f freqtrade          # Original
docker compose logs -f freqtrade-custom   # ADX filter

# Restart after config changes
docker compose restart

# Check memory
free -h

# Stop both
docker compose down

# Start both
docker compose up -d

# Check which strategies are running
docker compose ps
```

---

## Next Steps

1. **Deploy both to droplet** (rsync + docker compose up -d)
2. **Let run for 3-5 days**
3. **Compare daily** with `./compare-strategies.sh`
4. **After 20-30 trades each**: Make decision based on criteria above
5. **Keep winner, stop loser** or try different strategy type

---

**Remember:** This is still paper trading (dry_run: true). NO REAL MONEY.
