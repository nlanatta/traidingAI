# Freqtrade Trading Bot - Paper Trading POC

**Status:** Running 2 strategies in parallel on DigitalOcean (A/B testing)

**⚠️ PAPER TRADING ONLY - NO REAL MONEY**

---

## Quick Links

- **[DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)** - Complete setup, monitoring, and troubleshooting guide
- **Droplet IP:** `192.81.218.58`
- **SSH:** `ssh -i ~/.ssh/id_do root@192.81.218.58`

---

## Current Setup

### Strategies Running

| Strategy | Description | Status |
|----------|-------------|--------|
| **SampleStrategy** | Mean-reversion (RSI + TEMA + BB) | Running (baseline) |
| **CustomSampleStrategy** | SampleStrategy + ADX < 25 filter | Running (test) |

### Trading Pairs
- BTC/USDT, ETH/USDT, SOL/USDT
- ADA/USDT, DOT/USDT, LINK/USDT

### Risk Settings
- Virtual balance: $10,000 USDT
- Max open trades: 3
- Stake per trade: $100 USDT
- Stop-loss: -10%
- Timeframe: 5 minutes

---

## Quick Commands

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58

# Check strategies
cd ~/freqtradebot/freqtrade
docker compose ps

# Compare performance
./compare-strategies.sh

# View logs
docker compose logs -f

# Restart after changes
docker compose restart
```

---

## What We're Testing

**Hypothesis:** Adding an ADX < 25 filter will prevent catastrophic stop-losses during trending markets.

**Backtest showed:** 87% win rate, but -$2.27 total (3 stop-losses wiped gains)

**Expected outcome after 20-30 trades:**
- CustomSampleStrategy avoids catastrophic losses
- Fewer trades but better overall profitability

---

## Files

```
.
├── DEPLOYMENT-GUIDE.md          ⭐ COMPLETE GUIDE - READ THIS
├── README.md                    ← You are here
├── compare-strategies.sh        Compare strategy performance
├── docker-compose.yml           Runs both strategies
└── freqtrade/
    ├── user_data/
    │   ├── config.json                 SampleStrategy config
    │   ├── config-custom.json          CustomSampleStrategy config
    │   ├── tradesv3.sqlite             SampleStrategy database
    │   ├── tradesv3-custom.sqlite      CustomSampleStrategy database
    │   ├── logs/
    │   │   ├── freqtrade.log
    │   │   └── freqtrade-custom.log
    │   └── strategies/
    │       ├── SampleStrategy.py
    │       └── CustomSampleStrategy.py
```

---

## Next Steps

1. **Monitor daily:** Run `./compare-strategies.sh` on droplet
2. **After 3-5 days (20-30 trades):** Compare performance
3. **Make decision:** Keep winner, stop loser (see DEPLOYMENT-GUIDE.md)
4. **If both fail:** Try different strategy type

---

**Full documentation:** See [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)
