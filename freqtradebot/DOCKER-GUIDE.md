# Docker Setup Guide

## Overview

This setup runs two freqtrade instances in parallel for A/B testing:
- **freqtrade** - Runs `SampleStrategy` (baseline)
- **freqtrade-custom** - Runs `CustomSampleStrategy` (test variant)

## Directory Structure

```
freqtradebot/
├── strategies/              # Your custom strategies (tracked in git)
├── config-sample.json       # Config for SampleStrategy
├── config-custom.json       # Config for CustomSampleStrategy
├── docker-compose.yml       # Docker orchestration
└── freqtrade/               # Official freqtrade (gitignored)
    └── user_data/           # Shared data, logs, databases
```

## Quick Start

### 1. Ensure freqtrade is cloned

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot

# If freqtrade directory doesn't exist:
git clone https://github.com/freqtrade/freqtrade.git
```

### 2. Start both bots

```bash
# Start both containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Stop the bots

```bash
# Stop both
docker-compose down

# Stop just one
docker-compose stop freqtrade
docker-compose stop freqtrade-custom
```

## Container Details

### freqtrade (SampleStrategy)
- **Container:** `freqtrade`
- **Config:** `config-sample.json`
- **Strategy:** `SampleStrategy`
- **Port:** 8080
- **Database:** `tradesv3.sqlite`
- **Log:** `logs/freqtrade.log`

### freqtrade-custom (CustomSampleStrategy)
- **Container:** `freqtrade-custom`
- **Config:** `config-custom.json`
- **Strategy:** `CustomSampleStrategy`
- **Port:** 8081
- **Database:** `tradesv3-custom.sqlite`
- **Log:** `logs/freqtrade-custom.log`

## Volume Mappings

Both containers share:
- **user_data** - Market data, logs, databases
- **strategies** - Your custom strategies (read-only)
- **config** - Strategy-specific configuration (read-only)

## Useful Commands

### View logs for a specific bot

```bash
# SampleStrategy logs
docker-compose logs -f freqtrade

# CustomSampleStrategy logs
docker-compose logs -f freqtrade-custom
```

### Restart a specific bot

```bash
docker-compose restart freqtrade
docker-compose restart freqtrade-custom
```

### Execute commands inside a container

```bash
# Access freqtrade CLI in baseline bot
docker-compose exec freqtrade freqtrade list-strategies

# Access custom bot
docker-compose exec freqtrade-custom freqtrade list-strategies
```

### Update freqtrade image

```bash
# Pull latest stable image
docker-compose pull

# Restart with new image
docker-compose up -d
```

## A/B Testing Workflow

### 1. Create a new strategy

```bash
cd strategies/
cp CustomSampleStrategy.py MyNewStrategy.py
# Edit MyNewStrategy.py
```

### 2. Test it against baseline

Edit `docker-compose.yml` to change the custom bot's strategy:

```yaml
freqtrade-custom:
  command: >
    trade
    ...
    --strategy MyNewStrategy  # Changed here
```

### 3. Restart and compare

```bash
# Restart the custom bot
docker-compose restart freqtrade-custom

# Compare performance
docker-compose logs freqtrade | grep "Profit"
docker-compose logs freqtrade-custom | grep "Profit"
```

### 4. Check databases

```bash
# Baseline trades
sqlite3 freqtrade/user_data/tradesv3.sqlite "SELECT * FROM trades;"

# Custom trades
sqlite3 freqtrade/user_data/tradesv3-custom.sqlite "SELECT * FROM trades;"
```

## Configuration

### Modifying Strategies

Edit files in `strategies/` directory. The changes are immediately available (read-only mount):

```bash
# Edit strategy
vim strategies/CustomSampleStrategy.py

# Restart container to pick up changes
docker-compose restart freqtrade-custom
```

### Modifying Configs

Edit `config-sample.json` or `config-custom.json`:

```bash
# Edit config
vim config-custom.json

# Restart to apply
docker-compose restart freqtrade-custom
```

### Adding API Keys

Update the config files with your exchange credentials:

```json
{
  "exchange": {
    "name": "kraken",
    "key": "YOUR_API_KEY",
    "secret": "YOUR_API_SECRET",
    ...
  }
}
```

**Important:** These files are tracked in your private git repo. Ensure your repo stays private!

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs freqtrade

# Common issues:
# - Invalid config (check JSON syntax)
# - Missing API keys
# - Strategy not found
```

### Strategy not found

```bash
# Verify strategy is mounted
docker-compose exec freqtrade ls -la /freqtrade/strategies/

# Verify strategy_path in config
docker-compose exec freqtrade cat /freqtrade/config.json | grep strategy_path
```

### Port already in use

```bash
# Check what's using the port
lsof -i :8080
lsof -i :8081

# Either stop the conflicting service or change ports in docker-compose.yml
```

### Database locked

```bash
# Stop all containers
docker-compose down

# Remove lock file
rm freqtrade/user_data/*.sqlite-shm
rm freqtrade/user_data/*.sqlite-wal

# Restart
docker-compose up -d
```

## Resources

- [Freqtrade Docker Documentation](https://www.freqtrade.io/en/stable/docker_quickstart/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Freqtrade Configuration](https://www.freqtrade.io/en/stable/configuration/)
