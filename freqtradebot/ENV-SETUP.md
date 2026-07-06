# Environment Variables Setup

## How Freqtrade Loads Secrets

Freqtrade uses a special naming convention for environment variables:

```
FREQTRADE__SECTION__KEY
```

The double underscores (`__`) are important! This maps to JSON config like:

```json
{
  "section": {
    "key": "value"
  }
}
```

## Setup on Droplet

### 1. Create .env File

```bash
ssh -i ~/.ssh/id_do root@192.81.218.58
cd ~/freqtradebot
nano .env
```

### 2. Add Environment Variables

For **freqtrade-live** container:

```bash
# Exchange API Credentials
FREQTRADE__EXCHANGE__KEY=your_bingx_api_key_here
FREQTRADE__EXCHANGE__SECRET=your_bingx_api_secret_here

# Telegram Bot
FREQTRADE__TELEGRAM__TOKEN=your_telegram_bot_token
FREQTRADE__TELEGRAM__CHAT_ID=your_chat_id
```

Example with real values:
```bash
FREQTRADE__EXCHANGE__KEY=abc123def456
FREQTRADE__EXCHANGE__SECRET=xyz789secret
FREQTRADE__TELEGRAM__TOKEN=8943167740:AAHi_1qatH9LZgxlBhvUL3ZslMjV6PDfjDY
FREQTRADE__TELEGRAM__CHAT_ID=7881870362
```

### 3. Secure the File

```bash
chmod 600 .env
ls -la .env  # Should show: -rw------- (only root can read/write)
```

### 4. Restart Containers

```bash
docker compose restart freqtrade-live

# Check logs
docker compose logs -f freqtrade-live
```

### 5. Verify Environment Variables Are Loaded

```bash
# Should NOT show the actual values (for security)
docker compose exec freqtrade-live env | grep FREQTRADE

# Check if Telegram connected
docker compose logs freqtrade-live | grep -i telegram

# Should see: "Telegram is listening for following commands"
```

---

## Multiple Strategies with Different Credentials

If you want different credentials per strategy, you can use docker-compose environment overrides:

```yaml
services:
  freqtrade-live:
    environment:
      - FREQTRADE__TELEGRAM__TOKEN=token_for_live
    env_file:
      - .env  # Loads base credentials
```

Or create separate .env files:

```yaml
services:
  freqtrade:
    env_file:
      - .env.sample

  freqtrade-custom:
    env_file:
      - .env.custom

  freqtrade-live:
    env_file:
      - .env.live
```

---

## Environment Variable Reference

### Exchange

```bash
FREQTRADE__EXCHANGE__NAME=bingx
FREQTRADE__EXCHANGE__KEY=your_api_key
FREQTRADE__EXCHANGE__SECRET=your_api_secret
```

Maps to:
```json
{
  "exchange": {
    "name": "bingx",
    "key": "your_api_key",
    "secret": "your_api_secret"
  }
}
```

### Telegram

```bash
FREQTRADE__TELEGRAM__ENABLED=true
FREQTRADE__TELEGRAM__TOKEN=your_token
FREQTRADE__TELEGRAM__CHAT_ID=your_chat_id
```

Maps to:
```json
{
  "telegram": {
    "enabled": true,
    "token": "your_token",
    "chat_id": "your_chat_id"
  }
}
```

### Dry Run

```bash
FREQTRADE__DRY_RUN=false  # ⚠️ LIVE TRADING
```

Maps to:
```json
{
  "dry_run": false
}
```

---

## Testing

### Test Exchange Connection

```bash
docker compose exec freqtrade-live freqtrade list-pairs --exchange bingx --quote USDT
```

### Test Balance Fetch

```bash
docker compose exec freqtrade-live freqtrade show-balance
```

### Test Telegram

```bash
# Check logs for successful connection
docker compose logs freqtrade-live | grep -i "telegram is listening"

# Send test command to your bot on Telegram
/status
```

---

## Troubleshooting

### Error: "The token `${FREQTRADE__TELEGRAM__TOKEN}` was rejected"

**Problem:** Environment variable not loaded

**Fix:**
```bash
# Check .env exists
ls -la ~/freqtradebot/.env

# Check variable is set
cat ~/freqtradebot/.env | grep FREQTRADE__TELEGRAM__TOKEN

# Restart
docker compose restart freqtrade-live
```

### Error: "API key is invalid"

**Problem:** Wrong API key or secret

**Fix:**
```bash
# Verify API keys on BingX website
# Copy fresh keys to .env
nano ~/freqtradebot/.env

# Restart
docker compose restart freqtrade-live
```

### Variables Not Loading

**Problem:** Typo in variable name

**Fix:** Variable names are **case-sensitive** and must have **double underscores**:
- ✅ `FREQTRADE__EXCHANGE__KEY`
- ❌ `FREQTRADE_EXCHANGE_KEY` (single underscore)
- ❌ `freqtrade__exchange__key` (lowercase)

---

## Security Checklist

- ✅ `.env` file has `chmod 600` permissions
- ✅ `.env` is in `.gitignore`
- ✅ Never commit `.env` to git
- ✅ API keys have IP whitelist enabled
- ✅ API keys have NO withdrawal permissions
- ✅ 2FA enabled on exchange account

---

## Summary

1. Use `FREQTRADE__SECTION__KEY` format (double underscores)
2. Create `.env` file on droplet only (never commit to git)
3. Freqtrade automatically loads these and overrides config values
4. Test with `dry_run: true` first
5. Only go live when everything works

Your secrets are now secure! 🔒
