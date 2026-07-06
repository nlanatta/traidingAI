# Freqtrade Bot Setup

This directory contains a complete freqtrade trading bot setup with A/B testing capabilities.

## 📁 Structure

```
freqtradebot/
├── strategies/              # Your custom trading strategies (tracked in git)
│   ├── SampleStrategy.py
│   ├── CustomSampleStrategy.py
│   └── README.md
├── freqtrade/              # Official freqtrade code (gitignored, cloned from upstream)
├── config-sample.json      # Config for SampleStrategy
├── config-custom.json      # Config for CustomSampleStrategy  
├── config.json             # Config for local development
├── docker-compose.yml      # A/B testing setup (2 bots in parallel)
└── *.md                    # Documentation
```

## 🚀 Quick Start

### Option 1: Docker (Recommended for A/B Testing)

```bash
cd freqtradebot

# Ensure freqtrade is cloned
git clone https://github.com/freqtrade/freqtrade.git

# Start both bots
docker-compose up -d

# View logs
docker-compose logs -f
```

See [DOCKER-GUIDE.md](DOCKER-GUIDE.md) for details.

### Option 2: Local Development

```bash
cd freqtradebot/freqtrade

# Install
./setup.sh -i

# Run with your custom strategy
freqtrade trade --config ../config.json --strategy CustomSampleStrategy
```

See [GIT-WORKFLOW.md](GIT-WORKFLOW.md) for details.

## 📚 Documentation

- **[GIT-WORKFLOW.md](GIT-WORKFLOW.md)** - Git workflow and freqtrade updates
- **[DOCKER-GUIDE.md](DOCKER-GUIDE.md)** - Docker setup and A/B testing
- **[DEPLOYMENT-GUIDE.md](DEPLOYMENT-GUIDE.md)** - Production deployment
- **[DEPLOY-DIGITALOCEAN.md](DEPLOY-DIGITALOCEAN.md)** - DigitalOcean specific setup
- **[POC-GUIDE.md](POC-GUIDE.md)** - Proof of concept walkthrough
- **[AB-TEST-GUIDE.md](AB-TEST-GUIDE.md)** - A/B testing methodology

## 🔑 Key Features

### Separated Architecture
- **Strategies stay private** - No public fork needed
- **Easy updates** - Pull from official freqtrade anytime
- **Clean separation** - Your code vs freqtrade code

### A/B Testing
- Run **two strategies side-by-side** with Docker
- Separate databases and logs
- Compare performance in real-time

### Version Control
- ✅ Tracked: Strategies, configs, docker-compose, docs
- ❌ Ignored: Freqtrade code, generated data, logs

## 🛠️ Common Tasks

### Create a new strategy

```bash
cd strategies/
cp CustomSampleStrategy.py MyNewStrategy.py
# Edit MyNewStrategy.py
git add MyNewStrategy.py
git commit -m "Add new strategy"
```

### Update freqtrade

```bash
cd freqtrade/
git pull upstream stable
```

### Test a strategy

```bash
cd freqtrade/
freqtrade backtesting \
  --config ../config.json \
  --strategy MyNewStrategy \
  --timerange 20240101-20240630
```

### Deploy changes

```bash
# Push strategies to git
git add strategies/
git commit -m "Update strategy"
git push origin main

# On server: pull and restart
git pull
docker-compose restart
```

## ⚠️ Important Notes

1. **Private repo required** - Configs contain API keys and Telegram tokens
2. **Clone freqtrade manually** - It's gitignored, clone on each machine
3. **Strategies are tracked** - Your custom strategies ARE in git
4. **Update regularly** - Pull upstream freqtrade updates frequently

## 🔗 Resources

- [Official Freqtrade Docs](https://www.freqtrade.io/en/stable/)
- [Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Freqtrade GitHub](https://github.com/freqtrade/freqtrade)

## 🤝 Contributing

This is a private trading bot setup. Strategies and configs should not be shared publicly.
