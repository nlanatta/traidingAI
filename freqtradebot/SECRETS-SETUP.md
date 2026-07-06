# Secrets Management Guide

## Overview

API keys and secrets are stored in a `.env` file that is **NOT tracked in git**. This keeps your credentials secure.

## Setup on Droplet

### 1. Create .env File

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58
cd ~/freqtradebot

# Create .env file
nano .env
```

### 2. Add Your Secrets

Paste this into `.env` and replace with your actual values:

```bash
# BingX API Credentials
BINGX_API_KEY=your_actual_api_key_here
BINGX_API_SECRET=your_actual_api_secret_here

# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

### 3. Secure the File

```bash
# Make it readable only by root
chmod 600 .env

# Verify it's not in git
cat .gitignore | grep .env
# Should show: .env
```

### 4. Restart Containers

```bash
cd ~/freqtradebot
docker compose down
docker compose up -d
```

### 5. Verify Secrets Are Loaded

```bash
# Check if environment variables are loaded (should show nothing for security)
docker compose exec freqtrade env | grep BINGX_API_KEY
# Output: BINGX_API_KEY=your_key (confirms it's loaded)

# Or check logs for successful connection
docker compose logs -f | grep -i "exchange"
```

---

## Getting API Keys

### BingX API Keys

1. Go to [bingx.com](https://bingx.com)
2. Login → API Management → Create API
3. Name: `Freqtrade Bot`
4. Permissions:
   - ✅ Enable Trading
   - ✅ Enable Reading
   - ❌ **NEVER** enable Withdrawals
5. IP Whitelist (Optional but recommended):
   - Add your droplet IP: `192.81.218.58`
6. Copy API Key and Secret

### Telegram Bot Token

1. Open Telegram, search for `@BotFather`
2. Send: `/newbot`
3. Follow prompts:
   - Bot name: `My Freqtrade Bot`
   - Username: `myfreqtrade_bot` (must end with `_bot`)
4. Copy the token (looks like: `123456:ABCdef...`)

### Telegram Chat ID

1. Search for `@userinfobot` on Telegram
2. Send: `/start`
3. Bot replies with your chat ID (e.g., `7881870362`)

---

## Security Best Practices

### ✅ DO:
- Keep `.env` file on server only (never commit to git)
- Use `chmod 600 .env` to restrict access
- Use IP whitelist on exchange
- Enable 2FA on exchange account
- Never enable withdrawal permissions on API keys
- Regularly rotate API keys (monthly)

### ❌ DON'T:
- Don't commit `.env` to git
- Don't share API keys in Slack/email
- Don't enable withdrawal permissions
- Don't reuse API keys across bots
- Don't store secrets in config files

---

## Updating Secrets

```bash
# SSH into droplet
ssh -i ~/.ssh/id_do root@192.81.218.58
cd ~/freqtradebot

# Edit .env file
nano .env

# Restart containers to pick up changes
docker compose restart
```

---

## Troubleshooting

### Secrets Not Loading

```bash
# Check .env file exists
ls -la ~/freqtradebot/.env

# Check docker-compose references it
cat docker-compose.yml | grep env_file

# Check container has environment variables
docker compose exec freqtrade env | grep BINGX
```

### API Connection Errors

```bash
# Test API connection
docker compose exec freqtrade freqtrade test-pairlist --config /freqtrade/config.json

# Check logs for auth errors
docker compose logs -f | grep -i "auth\|api\|key"
```

### Wrong API Keys

```bash
# Update .env
nano ~/freqtradebot/.env

# Restart
docker compose restart

# Verify
docker compose logs -f freqtrade
```

---

## Backup .env (Optional)

Store encrypted backup in password manager:

```bash
# On droplet - display .env contents
cat ~/freqtradebot/.env

# Copy output and save in password manager (1Password, Bitwarden, etc.)
```

**Never store plain .env file in Dropbox, Google Drive, or email!**

---

## Alternative: Direct Environment Variables

Instead of `.env` file, you can set environment variables directly in docker-compose:

```yaml
services:
  freqtrade-live:
    environment:
      - BINGX_API_KEY=your_key
      - BINGX_API_SECRET=your_secret
```

**Not recommended:** This exposes secrets in docker-compose.yml which might be committed to git.

---

## Summary

1. **Local repo:** `.env` is in `.gitignore` ✅
2. **Remote server:** Create `.env` with real API keys
3. **Docker:** Loads `.env` automatically via `env_file: .env`
4. **Config:** References `${BINGX_API_KEY}` placeholders
5. **Security:** File is `chmod 600`, never committed to git

Your API keys are now secure! 🔒
