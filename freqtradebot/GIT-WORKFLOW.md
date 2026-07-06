# Git Workflow - Freqtrade Submodule

## Overview

The `freqtradebot/freqtrade` directory is configured as a Git submodule pointing to your fork of freqtrade. This setup allows you to:
- Make custom changes (strategies, configs)
- Pull upstream freqtrade updates
- Maintain your fork separate from the official repository

## Repository Structure

- **Your fork:** https://github.com/nlanatta/freqtrade
- **Parent repo:** https://github.com/nlanatta/traidingAI

## Remotes Configuration

Inside the `freqtradebot/freqtrade` submodule:
- `origin` → https://github.com/nlanatta/freqtrade (your fork - for pushing custom changes)
- `upstream` → https://github.com/freqtrade/freqtrade (official repo - for pulling updates)

## Daily Workflows

### 1. Making Custom Changes (Strategies, Configs)

```bash
# Navigate to the submodule
cd freqtradebot/freqtrade

# Create/edit your custom strategies
# Example: edit user_data/strategies/MyCustomStrategy.py

# Stage and commit your changes
git add user_data/strategies/MyCustomStrategy.py
git commit -m "Add custom momentum strategy"

# Push to your fork
git push origin develop
```

### 2. Pulling Upstream Updates

```bash
# Navigate to the submodule
cd freqtradebot/freqtrade

# Fetch latest changes from official freqtrade
git fetch upstream

# Merge upstream changes into your local branch
git merge upstream/develop  # or upstream/stable for stable releases

# Push updated branch to your fork
git push origin develop
```

### 3. Updating Parent Repo to Track New Submodule Commit

After making changes or updating the submodule, update the parent repo:

```bash
# Navigate to parent repo root
cd /Users/nlanatta/Documents/Projects/Personal/traidingAI

# Stage the submodule update
git add freqtradebot/freqtrade

# Commit the submodule pointer update
git commit -m "Update freqtrade submodule to latest version"

# Push to parent repo
git push origin main
```

## Common Scenarios

### Cloning This Repo on a New Machine

```bash
# Clone the parent repo
git clone git@github.com:nlanatta/traidingAI.git
cd traidingAI

# Initialize and update submodules
git submodule init
git submodule update --remote

# Set up remotes in the submodule
cd freqtradebot/freqtrade
git remote add upstream git@github.com:freqtrade/freqtrade.git
```

### Checking Submodule Status

```bash
# From parent repo root
git submodule status

# See if submodule has uncommitted changes
cd freqtradebot/freqtrade
git status
```

### Syncing with Upstream Before Making Changes

```bash
cd freqtradebot/freqtrade

# Fetch and merge upstream changes
git fetch upstream
git merge upstream/develop

# Resolve any conflicts if they arise
# Then push to your fork
git push origin develop
```

### Creating a New Strategy Branch

```bash
cd freqtradebot/freqtrade

# Create and switch to new branch
git checkout -b feature/new-strategy

# Make your changes
# ... edit files ...

# Commit and push to your fork
git add .
git commit -m "Implement new strategy"
git push origin feature/new-strategy
```

## Important Notes

- **Never commit directly to upstream:** You only have write access to your fork (`origin`), not the official repo (`upstream`)
- **Submodule commits are pointers:** When you commit the submodule in the parent repo, you're committing a specific commit hash, not the files themselves
- **Keep fork synced:** Regularly pull from `upstream` to stay current with official freqtrade updates
- **Branch tracking:** The submodule is configured to track the `develop` branch by default

## Troubleshooting

### Submodule shows modified content

```bash
cd freqtradebot/freqtrade
git status  # Check what changed
git diff    # See the differences

# Either commit the changes or reset
git reset --hard origin/develop  # Discard changes
```

### Detached HEAD state in submodule

```bash
cd freqtradebot/freqtrade
git checkout develop
git pull origin develop
```

### Merge conflicts when pulling upstream

```bash
cd freqtradebot/freqtrade
git fetch upstream
git merge upstream/develop

# Resolve conflicts in your editor
# Then:
git add .
git commit -m "Merge upstream changes"
git push origin develop
```

## Resources

- [Official Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- [Git Submodules Documentation](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [Your Freqtrade Fork](https://github.com/nlanatta/freqtrade)
- [Official Freqtrade Repo](https://github.com/freqtrade/freqtrade)
