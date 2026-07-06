# Freqtrade Trading Bot - Complete Deployment Guide

**Status:** Paper trading (NO REAL MONEY) on DigitalOcean VPS

**Current Setup:** Running 2 strategies in parallel (A/B testing)
- **SampleStrategy** (baseline) - Mean-reversion without trend filter
- **CustomSampleStrategy** (test) - Mean-reversion with ADX < 25 filter

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Initial Setup (DigitalOcean)](#initial-setup-digitalocean)
3. [Strategy A/B Testing](#strategy-ab-testing)
4. [Monitoring & Analysis](#monitoring--analysis)
5. [Troubleshooting](#troubleshooting)
6. [Reference](#reference)

---

## Quick Start

### Current Deployment (Droplet Already Running)

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58

# Check both strategies are running
cd ~/freqtradebot/freqtrade
docker compose ps

# View logs
docker compose logs -f

# Compare strategy performance
./compare-strategies.sh
```

### Update Configuration

```bash
# From LOCAL machine - sync changes to droplet
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@192.81.218.58:~/freqtradebot/

# SSH in and restart
ssh -i ~/.ssh/id_do root@192.81.218.58
cd ~/freqtradebot/freqtrade
docker compose restart
```

---

## Initial Setup (DigitalOcean)

### Prerequisites
- DigitalOcean account with $5 credit
- SSH key (`~/.ssh/id_do`)
- Telegram bot token and chat_id

### Step 1: Create Droplet

**Via Web UI (Recommended):**
1. Go to cloud.digitalocean.com
2. Click "Create" → "Droplets"
3. Choose:
   - **Image:** Ubuntu 24.04 LTS
   - **Plan:** Basic
   - **CPU:** 1GB RAM / 1 vCPU ($6/mo) - **Required for dual strategies**
   - **Datacenter:** Closest to you
   - **Authentication:** SSH Key (select your `id_do` key)
   - **Hostname:** `freqtrade-bot`
4. Click "Create Droplet"
5. Note your droplet IP: `192.81.218.58`

**SSH Key Troubleshooting:**
```bash
# List your local SSH keys
ls -la ~/.ssh/id_*.pub

# If you get "Permission denied" when connecting:
ssh -i ~/.ssh/id_do root@192.81.218.58

# Make sure the key you used matches what's in DigitalOcean
```

### Step 2: Initial Server Setup

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose-v2 -y

# Install SQLite (for database queries)
apt install sqlite3 -y

# Verify installation
docker --version
docker compose version
```

### Step 3: Deploy Freqtrade

```bash
# From LOCAL machine - sync all files
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@192.81.218.58:~/freqtradebot/

# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58

# Go to freqtrade directory
cd ~/freqtradebot/freqtrade

# Verify paper trading config
cat user_data/config.json | grep dry_run
# Should show: "dry_run": true
```

### Step 4: Fix Permissions (IMPORTANT)

```bash
# On droplet
cd ~/freqtradebot/freqtrade

# Create log files
touch user_data/logs/freqtrade.log user_data/logs/freqtrade-custom.log
chmod 666 user_data/logs/*.log

# Fix permissions for Docker (runs as user 1000)
chown -R 1000:1000 user_data/
chmod -R 755 user_data/
```

### Step 5: Configure Telegram (Optional)

**Get Bot Token & Chat ID:**

1. **Create bot:** Message @BotFather on Telegram
   ```
   /newbot
   Name: Freqtrade POC Bot
   Username: your_freqtrade_bot
   ```
   Copy the token (looks like: `123456789:ABCdefGHI...`)

2. **Get chat ID:** Message @userinfobot
   It replies with your chat ID (e.g., `7881870362`)

3. **Update config on droplet:**
   ```bash
   nano ~/freqtradebot/freqtrade/user_data/config.json
   ```
   
   Update telegram section:
   ```json
   "telegram": {
     "enabled": true,
     "token": "YOUR_BOT_TOKEN",
     "chat_id": "YOUR_CHAT_ID"
   }
   ```

4. **Start your bot:**
   - Search for your bot on Telegram
   - Click START

**For CustomSampleStrategy:**
- **Option 1 (Recommended):** Disable Telegram in `config-custom.json`:
  ```json
  "telegram": {
    "enabled": false
  }
  ```

- **Option 2:** Create a second bot (same process, different token)

### Step 6: Start Trading Bots

```bash
# On droplet
cd ~/freqtradebot/freqtrade

# Start both strategies
docker compose up -d

# Check status
docker compose ps

# View logs (Ctrl+C to exit)
docker compose logs -f
```

### Step 7: Enable Auto-Restart on Reboot

```bash
# Create systemd service
cat > /etc/systemd/system/freqtrade.service <<EOF
[Unit]
Description=Freqtrade Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/freqtradebot/freqtrade
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

# Enable service
systemctl enable freqtrade
systemctl start freqtrade

# Check status
systemctl status freqtrade
```

---

## Strategy A/B Testing

### What We're Testing

**Hypothesis:** Adding an ADX < 25 filter prevents catastrophic stop-losses during trending markets.

| Strategy | Description | Backtest Result |
|----------|-------------|-----------------|
| **SampleStrategy** (baseline) | Mean-reversion with RSI + TEMA + Bollinger Bands. **No trend filter** - trades in all conditions. | 87% win rate, -$2.27 total (3 stop-losses wiped gains) |
| **CustomSampleStrategy** (test) | Same as above + `ADX < 25` filter. **Only trades in ranging markets**. | Untested - this is what we're validating |

### How It Works

**Two Docker Containers:**
- `freqtrade` (port 8080) - SampleStrategy
- `freqtrade-custom` (port 8081) - CustomSampleStrategy

**Separate Resources:**
- Configs: `config.json` vs `config-custom.json`
- Databases: `tradesv3.sqlite` vs `tradesv3-custom.sqlite`
- Logs: `freqtrade.log` vs `freqtrade-custom.log`

### Files Structure

```
user_data/
├── strategies/
│   ├── SampleStrategy.py           # Baseline (no ADX filter)
│   └── CustomSampleStrategy.py     # Test (ADX < 25 filter)
├── config.json                     # Config for SampleStrategy
├── config-custom.json              # Config for CustomSampleStrategy
├── tradesv3.sqlite                 # Database for SampleStrategy
├── tradesv3-custom.sqlite          # Database for CustomSampleStrategy
└── logs/
    ├── freqtrade.log               # Logs for SampleStrategy
    └── freqtrade-custom.log        # Logs for CustomSampleStrategy
```

### Current Configuration

**Trading Pairs (6 pairs for faster testing):**
- BTC/USDT, ETH/USDT, SOL/USDT
- ADA/USDT, DOT/USDT, LINK/USDT

**Risk Settings:**
- Virtual balance: $10,000 USDT
- Max open trades: 3
- Stake per trade: $100 USDT
- Stop-loss: -10%
- ROI targets: 4% (immediate), 2% (30min), 1% (60min)

**Timeframe:** 5-minute candles

---

## Monitoring & Analysis

### Daily Health Check

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58
cd ~/freqtradebot/freqtrade

# Check containers are running
docker compose ps

# Check memory usage (should be < 90%)
free -h

# Compare strategy performance
./compare-strategies.sh
```

### Compare Strategies Script

The `compare-strategies.sh` script shows:
- Total trades
- Win/loss count
- Average profit %
- Total profit in USDT
- Worst trade % (key metric!)
- Best trade %
- Recent 5 trades for each strategy

**What to Watch:**
- **Total Trades:** CustomSampleStrategy may have fewer (ADX filter rejects entries)
- **Win Rate:** Should be similar or better
- **Worst Trade:** Should avoid -10% catastrophic stop-losses
- **Total Profit:** After 20-30 trades, should be positive

### View Logs

```bash
# View both logs
docker compose logs -f

# View specific strategy
docker compose logs -f freqtrade          # SampleStrategy
docker compose logs -f freqtrade-custom   # CustomSampleStrategy

# View last 100 lines
docker compose logs --tail 100 freqtrade
```

### Manual Database Queries

```bash
# On droplet
cd ~/freqtradebot/freqtrade

# SampleStrategy - last 10 trades
sqlite3 user_data/tradesv3.sqlite "
SELECT 
  pair,
  datetime(open_date, 'localtime') as opened,
  datetime(close_date, 'localtime') as closed,
  ROUND(close_profit_abs, 2) as profit_usdt,
  ROUND(close_profit * 100, 2) as profit_pct
FROM trades 
WHERE is_open=0 
ORDER BY close_date DESC 
LIMIT 10;
"

# CustomSampleStrategy - performance summary
sqlite3 user_data/tradesv3-custom.sqlite "
SELECT 
  COUNT(*) as total_trades,
  SUM(CASE WHEN close_profit > 0 THEN 1 ELSE 0 END) as wins,
  ROUND(AVG(close_profit * 100), 2) as avg_profit_pct,
  ROUND(SUM(close_profit_abs), 2) as total_profit_usdt,
  ROUND(MIN(close_profit * 100), 2) as worst_trade_pct
FROM trades 
WHERE is_open=0;
"
```

### Decision Criteria (After 20-30 Trades Each)

**Keep CustomSampleStrategy If:**
- ✅ Total profit > SampleStrategy
- ✅ Worst trade > -5% (avoiding catastrophic stop-losses)
- ✅ Win rate ≥ 70%
- ✅ Profit factor ≥ 1.5

**Keep SampleStrategy If:**
- ✅ CustomSampleStrategy has < 10 trades (too restrictive)
- ✅ Both have similar performance (ADX filter not helping)

**Try Different Strategy Type If:**
- ❌ Both strategies net negative after 30 trades
- ❌ Both hitting multiple -10% stop-losses
- ❌ Mean-reversion not working in current market conditions

### Expected Timeline

- **Day 1-2:** 10-15 trades per strategy (early signals)
- **Day 3-5:** 20-30 trades per strategy (statistical validity)
- **After Day 5:** Make decision based on criteria above

---

## Troubleshooting

### Container Not Starting

**Check logs:**
```bash
docker compose logs freqtrade
docker compose logs freqtrade-custom
```

**Common issues:**

1. **Config file not found:**
   ```bash
   # Verify file exists and is named correctly
   ls -la user_data/config*.json
   
   # Check it's valid JSON
   cat user_data/config.json | python3 -m json.tool
   ```

2. **Permission denied on logs:**
   ```bash
   # Fix permissions
   chown -R 1000:1000 user_data/
   chmod -R 755 user_data/
   chmod 666 user_data/logs/*.log
   ```

3. **Telegram conflict (both using same bot):**
   ```bash
   # Disable Telegram on custom strategy
   nano user_data/config-custom.json
   # Set "enabled": false
   
   docker compose restart
   ```

### Exchange Connection Issues

**Binance geoblocking (error 451):**
- Solution: Use Kraken instead (already configured)
- Kraken supports 44 USDT pairs

**Test exchange connection:**
```bash
docker compose run --rm freqtrade list-pairs \
  --exchange kraken \
  --quote USDT
```

### Out of Memory

**Check memory usage:**
```bash
free -h
```

**If using > 90%:**
- Upgrade to 2GB droplet ($12/mo)
- OR: Run one strategy at a time

**Monitor in real-time:**
```bash
watch -n 1 free -h
```

### Strategy Not Trading

**Check if strategy is finding signals:**
```bash
# View strategy logs
docker compose logs -f freqtrade | grep -i "enter_long\|exit_long"

# For CustomSampleStrategy, check ADX is being calculated
docker compose logs -f freqtrade-custom | grep -i "adx"
```

**Verify pair data is downloading:**
```bash
# Should see "Downloading data for BTC/USDT..." in logs
docker compose logs freqtrade | grep -i "download"
```

### Telegram Not Working

1. **Check bot token and chat_id are correct:**
   ```bash
   cat user_data/config.json | grep -A 3 telegram
   ```

2. **Verify you clicked START in Telegram bot**

3. **Check logs for Telegram errors:**
   ```bash
   docker compose logs freqtrade | grep -i telegram
   ```

4. **Test connection:**
   ```bash
   # Restart container to trigger "Bot starting" message
   docker compose restart freqtrade
   ```

### Database Locked

**If you see "database is locked" errors:**
```bash
# Stop all containers
docker compose down

# Wait 5 seconds
sleep 5

# Start again
docker compose up -d
```

---

## Reference

### Configuration Files

**Key Settings in config.json / config-custom.json:**

```json
{
  "dry_run": true,              // CRITICAL: NO REAL MONEY
  "dry_run_wallet": 10000,      // Virtual $10K USDT
  "max_open_trades": 3,         // Max 3 concurrent positions
  "stake_amount": 100,          // $100 per trade
  
  "exchange": {
    "name": "kraken",           // Binance is geoblocked, use Kraken
    "key": "",                  // Empty = read-only (paper trading)
    "secret": "",
    "pair_whitelist": [
      "BTC/USDT", "ETH/USDT", "SOL/USDT",
      "ADA/USDT", "DOT/USDT", "LINK/USDT"
    ]
  },
  
  "telegram": {
    "enabled": true,            // false for config-custom.json
    "token": "YOUR_TOKEN",
    "chat_id": "YOUR_CHAT_ID"
  }
}
```

### Docker Compose Commands

```bash
# Start both strategies
docker compose up -d

# Stop both strategies
docker compose down

# Restart after config changes
docker compose restart

# View status
docker compose ps

# View logs (live)
docker compose logs -f

# View logs for specific strategy
docker compose logs -f freqtrade
docker compose logs -f freqtrade-custom

# View last 100 lines
docker compose logs --tail 100 freqtrade

# Stop one strategy
docker compose stop freqtrade-custom

# Start one strategy
docker compose start freqtrade-custom
```

### Useful Commands

```bash
# Compare strategies
./compare-strategies.sh

# Check memory usage
free -h

# Monitor memory in real-time
watch -n 1 free -h

# Download databases for offline analysis
scp root@192.81.218.58:~/freqtradebot/freqtrade/user_data/tradesv3*.sqlite ~/Downloads/

# List available trading pairs
docker compose run --rm freqtrade list-pairs --exchange kraken --quote USDT

# List available strategies
docker compose run --rm freqtrade list-strategies

# View strategy file
cat user_data/strategies/SampleStrategy.py
cat user_data/strategies/CustomSampleStrategy.py
```

### SSH & Rsync

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58

# Sync changes from local to droplet
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@192.81.218.58:~/freqtradebot/

# Download databases from droplet
scp -i ~/.ssh/id_do \
  root@192.81.218.58:~/freqtradebot/freqtrade/user_data/tradesv3*.sqlite \
  ~/Downloads/
```

### Cost Breakdown

**DigitalOcean Droplet:**
- **1GB RAM / 1 vCPU:** $6/mo (current setup)
- **Your credit:** $5 → First month costs $1
- **Billing:** Hourly, can destroy anytime

**To stay within free credit:** Destroy droplet after testing (Settings → Destroy)

**Upgrade options if needed:**
- **2GB RAM:** $12/mo (if memory issues)
- **512MB RAM:** $4/mo (NOT enough for dual strategies)

### Security Notes

**CRITICAL - Paper Trading Only:**
- ✅ `dry_run: true` in all configs
- ✅ Empty API keys (read-only)
- ✅ $10K virtual balance only
- ❌ **DO NOT** change dry_run to false
- ❌ **DO NOT** add real API keys with trading permissions

**Recommended Security (Optional):**

```bash
# Set up firewall
ufw allow OpenSSH
ufw enable

# Automatic security updates
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades
```

### Next Steps After Testing

**After 20-30 trades per strategy:**

1. **Run final comparison:**
   ```bash
   ./compare-strategies.sh
   ```

2. **Download databases for analysis:**
   ```bash
   scp root@192.81.218.58:~/freqtradebot/freqtrade/user_data/tradesv3*.sqlite ~/Downloads/
   ```

3. **Make decision based on criteria (see Monitoring section)**

4. **Keep winner, stop loser:**
   ```bash
   # Stop CustomSampleStrategy if SampleStrategy wins
   docker compose stop freqtrade-custom
   
   # OR stop SampleStrategy if CustomSampleStrategy wins
   docker compose stop freqtrade
   ```

5. **If BOTH fail:** Try different strategy type:
   - Current: Mean-reversion
   - Alternative: Trend-following
   - See trading wiki for other patterns

---

## Resources

- **Freqtrade Docs:** https://www.freqtrade.io/
- **Discord:** https://discord.gg/freqtrade (10K+ members)
- **Strategy Examples:** https://github.com/freqtrade/freqtrade-strategies
- **Trading Wiki (local):** `/Users/nlanatta/Documents/Projects/Personal/llm-trading`

---

**Remember:** This is PAPER TRADING with NO REAL MONEY. The goal is to validate strategy profitability before considering live trading (3-6 months of profitable paper trading required).

**Current Status:** Both strategies deployed and running on droplet `192.81.218.58`.
