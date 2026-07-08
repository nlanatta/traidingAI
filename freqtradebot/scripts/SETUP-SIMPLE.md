# AI Trading System - Simple Setup

## Two Options to Use Claude

### Option 1: Anthropic API (Recommended for automation)
**Best for**: Autonomous cron jobs, structured JSON responses, production use

**Cost**: ~$6/month for 6 runs per day

**Setup**:
```bash
# Get API key from: https://console.anthropic.com/
cd scripts
cp .env.example .env
nano .env  # Add: ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Test**:
```bash
python3 ai_selector.py
```

**Pros**:
- ✅ Returns pure JSON (no conversational text)
- ✅ Perfect for automation
- ✅ Consistent structured output
- ✅ Works great in cron jobs

**Cons**:
- ❌ Costs $6/month (~$0.20/day)
- ❌ Requires separate API key

---

### Option 2: Local Claude CLI (Free but limited)
**Best for**: Testing, manual runs, development

**Cost**: FREE (uses your existing Claude Code auth)

**Setup**:
```bash
# Already installed! You're using Claude Code
# No API key needed
```

**Test**:
```bash
python3 ai_selector_local.py
```

**Pros**:
- ✅ FREE
- ✅ Uses existing Claude Code authentication
- ✅ No separate API key needed

**Cons**:
- ❌ Returns conversational text mixed with JSON
- ❌ Requires manual interaction (can't run fully headless in cron)
- ❌ Not designed for automation
- ❌ May hit rate limits with frequent use

---

## Recommendation

**For your autonomous trading system**, use **Option 1 (API)**:
- The $6/month cost is negligible compared to potential 20-30% returns
- Cron jobs need reliable, structured output
- API is designed for this exact use case

**Cost/Benefit**:
- $6/month API cost
- Target: 20-30% annual return
- On $1,000 capital = $200-300/year profit
- API cost = 2-3% of profit
- Break-even: Just 0.6% monthly return (you're targeting 1.7-2.5%)

---

## Quick Start (API Method)

1. Get API key: https://console.anthropic.com/
2. Add to `.env`:
   ```bash
   cd scripts
   cp .env.example .env
   nano .env  # Paste: ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Test:
   ```bash
   python3 ai_selector.py
   ```
4. Install automation:
   ```bash
   ./setup_cron.sh
   ```

Done! Your AI trader runs every 4 hours automatically.

---

## Why Not Local CLI for Cron?

The Claude CLI you're using now is interactive - it's designed for conversations, not headless automation:

```bash
# Interactive CLI (what you use now)
claude "analyze this market data"
# Returns: "Let me analyze... Based on the data... I recommend..."

# API (designed for automation)
curl https://api.anthropic.com/v1/messages -d '{...}'
# Returns: {"strategy": "...", "confidence": 8, ...}
```

For cron jobs that run while you sleep, you need the API's structured responses.

---

## Both Files Available

I've created both versions:
- `ai_selector.py` - API version (recommended)
- `ai_selector_local.py` - Local CLI version (testing only)

The main orchestrator (`run_ai_selector.py`) tries local first, falls back to API if local isn't configured.

---

## Summary

| Feature | API (Recommended) | Local CLI |
|---------|-------------------|-----------|
| Cost | $6/month | FREE |
| Setup | API key required | Already works |
| Automation | ✅ Perfect | ❌ Not suitable |
| Cron Jobs | ✅ Works great | ❌ Interactive only |
| JSON Output | ✅ Pure JSON | ⚠️  Mixed with text |
| Production Use | ✅ Designed for this | ❌ Development only |

**For autonomous trading**: Use the API. The cost is worth it for reliable automation.
