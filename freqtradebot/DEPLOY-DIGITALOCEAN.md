# Deploy Freqtrade to DigitalOcean

> **⚠️ NOTE:** This guide has been superseded by [DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md) which includes A/B testing setup and is kept more up-to-date. This file is kept for historical reference.

## Prerequisites

- DigitalOcean account with $5 credit
- SSH key (we'll generate if needed)

---

## Step 1: Create Droplet

### Via Web UI (Recommended):

1. Go to cloud.digitalocean.com
2. Click "Create" → "Droplets"
3. Choose:
   - **Image:** Ubuntu 24.04 LTS
   - **Plan:** Basic
   - **CPU:** 
     - **512 MB RAM / 1 vCPU ($4/mo)** - Works for 2 pairs, might need upgrade if OOM
     - **1GB RAM / 1 vCPU ($6/mo)** - Safer option, no memory issues
   - **Datacenter:** Closest to you (lower latency to exchanges)
   - **Authentication:** SSH Key (IMPORTANT: check your key before creating)
   - **Hostname:** `freqtrade-bot`
4. Click "Create Droplet"
5. Wait 1-2 minutes for IP address
6. **Note your droplet IP** - you'll need it for SSH

**SSH Key Tips:**
- If you see "Permission denied" when connecting, the SSH key wasn't selected during creation
- Check which key is in DigitalOcean: Settings → Security → SSH Keys
- Your local key location: `~/.ssh/id_*.pub`

### Via CLI (Alternative):

```bash
# Install doctl (DigitalOcean CLI)
brew install doctl  # macOS

# Authenticate
doctl auth init

# Create droplet
doctl compute droplet create freqtrade-bot \
  --image ubuntu-24-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc3 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Get IP address
doctl compute droplet list
```

---

## Step 2: Initial Server Setup

```bash
# SSH into droplet (replace with your IP and key path)
ssh -i ~/.ssh/id_do root@YOUR_DROPLET_IP
# Note: Use the key that was added to DigitalOcean during droplet creation
# Common key paths: ~/.ssh/id_do, ~/.ssh/id_ed25519, ~/.ssh/id_rsa

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose-v2 -y

# Verify installation
docker --version
docker compose version
```

**Troubleshooting SSH:**
- If "Permission denied (publickey)": wrong key or key not added to droplet
- List your keys: `ls -la ~/.ssh/id_*.pub`
- Try different key: `ssh -i ~/.ssh/id_ed25519 root@YOUR_IP`
- Add key to existing droplet: DigitalOcean UI → Droplet → Access → Add SSH Key

---

## Step 3: Deploy Freqtrade

### Option A: Rsync (Recommended - Includes Config & Data)

From your **local machine** (not SSH session):

```bash
# Upload all files (excludes git/hidden folders)
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@YOUR_DROPLET_IP:~/freqtradebot/
```

**What gets transferred:**
- ✅ Your working config (config-poc.json with Telegram setup)
- ✅ Downloaded historical data (saves re-downloading 30 days)
- ✅ Strategy files (SampleStrategy.py)
- ✅ docker-compose.yml
- ❌ .git, .github, .claude (excluded for speed)

**Update just the config after changes:**
```bash
# Same rsync command - only transfers changed files (takes <5 seconds)
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@YOUR_DROPLET_IP:~/freqtradebot/
```

### Option B: Git Clone (Clean but requires re-download)

```bash
# SSH into droplet first
ssh -i ~/.ssh/id_do root@YOUR_DROPLET_IP

# Clone repo
git clone https://github.com/YOUR_USERNAME/freqtradebot.git
cd freqtradebot/freqtrade

# Need to re-download data (takes 5 minutes)
docker compose run --rm freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT ETH/USDT \
  --timeframe 5m \
  --days 30
```

---

### Verify & Start

```bash
# SSH into droplet (if not already)
ssh -i ~/.ssh/id_do root@YOUR_DROPLET_IP

# Go to freqtrade directory
cd ~/freqtradebot/freqtrade

# Verify config is paper trading
cat user_data/config-poc.json | grep dry_run
# Should show: "dry_run": true

# Verify Telegram is configured
cat user_data/config-poc.json | grep -A 3 telegram
# Should show: "enabled": true with your token/chat_id

# Start bot in background
docker compose up -d

# Check logs (you should see Telegram startup message)
docker compose logs -f freqtrade
```

---

## Step 4: Monitor Bot

### View Logs:
```bash
docker compose logs -f freqtrade
```

### Check Status:
```bash
docker compose ps
```

### Restart Bot:
```bash
docker compose restart
```

### Stop Bot:
```bash
docker compose down
```

---

## Step 5: Enable Auto-Restart on Reboot

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

## Step 6: Set Up Telegram Alerts

### Get Bot Token & Chat ID (Do This Locally First):

1. **Create bot:** Message @BotFather on Telegram
   - Send: `/newbot`
   - Name: `Freqtrade POC Bot`
   - Username: `your_freqtrade_bot` (must end in 'bot')
   - **Copy the token** (looks like: `123456789:ABCdefGHIjkl...`)

2. **Get chat ID:** Message @userinfobot
   - It replies with your chat ID (looks like: `123456789`)

3. **Update config locally:**
   ```bash
   # Edit on your local machine
   nano /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade/user_data/config-poc.json
   ```

   Change telegram section:
   ```json
   "telegram": {
     "enabled": true,
     "token": "YOUR_BOT_TOKEN_FROM_BOTFATHER",
     "chat_id": "YOUR_CHAT_ID_FROM_USERINFOBOT"
   }
   ```

4. **Test locally first:**
   ```bash
   cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade
   docker compose up
   # You should get Telegram message: "Freqtrade starting..."
   # Press Ctrl+C to stop
   ```

5. **Sync to droplet:**
   ```bash
   # From local machine - rsync only transfers changed config
   rsync -avz -e "ssh -i ~/.ssh/id_do" \
     --exclude='.*' \
     --exclude='__pycache__' \
     --exclude='*.pyc' \
     /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
     root@YOUR_DROPLET_IP:~/freqtradebot/
   ```

6. **Restart on droplet:**
   ```bash
   ssh -i ~/.ssh/id_do root@YOUR_DROPLET_IP
   cd ~/freqtradebot/freqtrade
   docker compose restart
   
   # Check logs - you should see "Connected to Telegram"
   docker compose logs -f freqtrade
   ```

---

## Step 7: Monitor Performance

### Check trades:
```bash
docker compose run --rm freqtrade show-trades --days 7
```

### Check profit:
```bash
docker compose run --rm freqtrade profit --days 7
```

### View database:
```bash
# Install sqlite3
apt install sqlite3 -y

# Query database
sqlite3 user_data/tradesv3.sqlite "SELECT * FROM trades LIMIT 10;"
```

---

## Costs

### 512 MB RAM Option ($4/mo):
- **Droplet:** $4/mo (512 MB RAM)
- **Your credit:** $5 → First month FREE + $1 credit remaining
- **After credit:** $4/mo billed hourly
- **Risk:** May hit out-of-memory (OOM) errors with 2 pairs
- **Monitor:** `free -h` on droplet - if using >90%, upgrade to 1GB

### 1GB RAM Option ($6/mo - Safer):
- **Droplet:** $6/mo (1GB RAM)
- **Your credit:** $5 → First month costs $1
- **After credit:** $6/mo billed hourly
- **Pro:** No memory issues, stable for 2-5 pairs

**To stay within free credit:** Destroy droplet after POC testing (Settings → Destroy).

**Memory monitoring:**
```bash
# Check memory usage
free -h

# Watch in real-time
watch -n 1 free -h
```

If 512 MB droplet crashes or shows OOM errors → upgrade to 1GB (takes 5 min, no data loss).

---

## Security Best Practices

### 1. Set up firewall:
```bash
ufw allow OpenSSH
ufw enable
```

### 2. Disable root SSH (optional):
```bash
# Create non-root user
adduser freqtrader
usermod -aG sudo freqtrader
usermod -aG docker freqtrader

# Disable root login
nano /etc/ssh/sshd_config
# Change: PermitRootLogin no
systemctl restart sshd
```

### 3. Set up automatic security updates:
```bash
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades
```

---

## Troubleshooting

### Bot not starting:
```bash
docker compose logs freqtrade
```

### Out of memory (1GB too small):
Upgrade to 2GB droplet:
```bash
# Via web UI: Droplet → Resize → 2GB ($12/mo)
```

### Can't connect to exchange:
```bash
# Test internet from container
docker compose run --rm freqtrade bash
ping binance.com
```

### Want to test locally first:
```bash
# On your laptop:
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade
docker compose up
# Press Ctrl+C to stop
```

---

## Next Steps After Deployment

1. **Let it run for 24-48 hours**
2. **Check logs for trades:** `docker compose logs -f freqtrade`
3. **Compare paper trading to backtest results**
4. **If profitable after 3-6 months:** Consider switching to live trading (small amounts)
5. **If unprofitable:** Destroy droplet, modify strategy, backtest again

---

## Quick Reference Commands

```bash
# SSH into droplet (use your key path)
ssh -i ~/.ssh/id_do root@YOUR_DROPLET_IP

# View logs
cd ~/freqtradebot/freqtrade && docker compose logs -f

# Restart bot (after config changes)
docker compose restart

# Check memory usage
free -h

# Check trades
docker compose run --rm freqtrade show-trades --days 1

# Check profit
docker compose run --rm freqtrade profit --days 7

# Stop bot
docker compose down

# Start bot
docker compose up -d

# Sync config changes from local
# (Run from LOCAL machine, not SSH)
rsync -avz -e "ssh -i ~/.ssh/id_do" \
  --exclude='.*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/ \
  root@YOUR_DROPLET_IP:~/freqtradebot/
```

---

## SAFETY REMINDERS

- ✅ **dry_run: true** in config = NO REAL MONEY
- ✅ Empty API keys = Read-only mode
- ✅ $10K virtual balance only
- ❌ **DO NOT** change dry_run to false until strategy is proven profitable (3-6 months)
- ❌ **DO NOT** add real API keys with trading permissions yet

---

## When to Destroy Droplet (Save Money)

If after 1-2 weeks paper trading shows **negative profit**:

```bash
# Download logs first
scp root@YOUR_DROPLET_IP:~/freqtradebot/freqtrade/user_data/tradesv3.sqlite ~/Downloads/

# Then destroy via web UI
# Settings → Destroy → Type droplet name to confirm
```

You'll get ~$5 credit back (hourly billing).

---

**Current Status:** Ready to deploy. Follow Step 1 to create your droplet.
