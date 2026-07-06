# Git Workflow - Freqtrade with Separate Strategies

## Overview

This repository uses a **separated strategies** approach where:
- **Freqtrade** is cloned from the official repo (not tracked in git)
- **Your custom strategies** are stored in the private parent repo
- Updates from upstream freqtrade are easy to pull
- Your strategies remain private

## Repository Structure

```
traidingAI/                          # Your private repo
├── freqtradebot/
│   ├── strategies/                  # YOUR CUSTOM STRATEGIES (tracked in git)
│   │   ├── CustomSampleStrategy.py
│   │   └── MyStrategy.py
│   ├── config.json                  # Custom config pointing to strategies/
│   ├── freqtrade/                   # Official freqtrade (NOT tracked, gitignored)
│   │   └── ...
│   └── *.md                         # Documentation (tracked in git)
└── .gitignore                       # Ignores freqtradebot/freqtrade/
```

## Initial Setup

### 1. Clone Freqtrade (First Time Only)

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot

# Clone official freqtrade
git clone https://github.com/freqtrade/freqtrade.git

# Or if it already exists, set up the remote
cd freqtrade
git remote add upstream https://github.com/freqtrade/freqtrade.git
```

### 2. Verify Configuration

The `freqtradebot/config.json` file is configured to use your separate strategies:

```json
{
  "user_data_dir": "/Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot",
  "strategy_path": "/Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/strategies",
  ...
}
```

## Daily Workflows

### 1. Creating a New Strategy

```bash
# Navigate to your strategies directory
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/strategies

# Create your new strategy
# Example: copy from template or create new
cp CustomSampleStrategy.py MyNewStrategy.py

# Edit your strategy
# ... make changes ...

# Commit to YOUR private repo (traidingAI)
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI
git add freqtradebot/strategies/MyNewStrategy.py
git commit -m "Add new trading strategy"
git push origin main
```

### 2. Updating Freqtrade from Upstream

```bash
# Navigate to freqtrade directory
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# Fetch latest changes
git fetch upstream

# Update to latest stable
git checkout stable
git pull upstream stable

# Or update to latest develop
git checkout develop
git pull upstream develop
```

### 3. Running Freqtrade with Your Strategies

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# Run with your custom config (which points to ../strategies/)
freqtrade trade --config ../config.json --strategy MyNewStrategy

# Or backtesting
freqtrade backtesting --config ../config.json --strategy MyNewStrategy
```

## Common Scenarios

### Cloning This Repo on a New Machine

```bash
# Clone your private repo
git clone git@github.com:nlanatta/traidingAI.git
cd traidingAI

# Clone freqtrade
cd freqtradebot
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade

# Install freqtrade
./setup.sh -i
```

### Checking for Freqtrade Updates

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# See what's new
git fetch upstream
git log HEAD..upstream/stable --oneline

# Or for develop branch
git log HEAD..upstream/develop --oneline
```

### Testing a Strategy

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade

# Dry-run backtesting
freqtrade backtesting \
  --config ../config.json \
  --strategy CustomSampleStrategy \
  --timerange 20240101-20240630

# List available strategies (should show your custom ones)
freqtrade list-strategies --config ../config.json
```

### Creating a Strategy Branch

```bash
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI

# Create feature branch
git checkout -b feature/new-momentum-strategy

# Work on your strategy
# ... edit freqtradebot/strategies/MomentumStrategy.py ...

# Commit
git add freqtradebot/strategies/
git commit -m "Add momentum-based strategy"
git push origin feature/new-momentum-strategy
```

## What Gets Tracked in Git

### ✅ Tracked (in traidingAI repo)
- `freqtradebot/strategies/` - Your custom strategies
- `freqtradebot/config.json` - Your custom config
- `freqtradebot/*.md` - Documentation
- `.gitignore` - Git ignore rules

### ❌ Not Tracked (gitignored)
- `freqtradebot/freqtrade/` - Official freqtrade code (pulled from upstream)
- `.idea/` - IDE settings
- `__pycache__/` - Python cache

## Benefits of This Approach

1. **Privacy**: Your strategies stay in your private repo
2. **Clean Updates**: Pull freqtrade updates without conflicts
3. **No Fork Needed**: No need for a public fork
4. **Separation of Concerns**: Your code separate from freqtrade code
5. **Easy Backup**: Only your strategies are backed up to GitHub

## Important Notes

- **Freqtrade directory is NOT in git**: It's gitignored and must be cloned manually on each machine
- **Strategies are tracked**: Your custom strategies in `strategies/` ARE in git
- **Config points to strategies**: The `config.json` uses absolute paths to your strategies directory
- **No conflicts**: Freqtrade updates won't conflict with your strategies

## Troubleshooting

### Strategy not found

```bash
# Verify config points to correct path
cat /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/config.json | grep strategy_path

# List strategies
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot/freqtrade
freqtrade list-strategies --config ../config.json
```

### Freqtrade missing after clone

```bash
# Clone it
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot
git clone https://github.com/freqtrade/freqtrade.git
cd freqtrade
./setup.sh -i
```

### Update conflicts

Since freqtrade is separate, there should be no conflicts. Just pull:

```bash
cd freqtradebot/freqtrade
git pull upstream stable
```

## Resources

- [Official Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- [Freqtrade Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Official Freqtrade Repo](https://github.com/freqtrade/freqtrade)
