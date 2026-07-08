# AI-Powered Trading System - Implementation Plan

**Created:** 2026-07-08  
**Goal:** Achieve 50-100% annual returns through AI-driven strategy selection and market analysis  
**Current:** 8.4% annual with static ImprovedAdaptiveV3  
**Capital:** $1000 USDT  

---

## Executive Summary

Transform static single-strategy trading into dynamic AI-powered system that:
- Analyzes market conditions every 4-6 hours
- Selects optimal strategy for current regime
- Deploys specialized strategies for specific market conditions
- Adapts in real-time to news, sentiment, and technical shifts

**Target Performance:**
- Phase 1: 20-30% annual (AI Strategy Selector)
- Phase 2: 30-50% annual (+ News Trader)
- Phase 3: 45-75% annual (+ Sentiment Scalper)
- Phase 4: 65-105% annual (+ Liquidation Trader)

---

## Current State Assessment

### What We Have:
- ✅ Freqtrade bot running on DigitalOcean droplet
- ✅ ImprovedAdaptiveV3 strategy (mean reversion, 100% win rate, 0.12 trades/day)
- ✅ 26 trading pairs (BTC, ETH, SOL, ADA, DOT, LINK, + 20 more)
- ✅ BingX API integration
- ✅ Trading wiki with sentiment analysis knowledge
- ✅ Current market: Extreme Fear (20), perfect for contrarian strategies

### What's Missing:
- ❌ Dynamic strategy selection (currently static)
- ❌ Market regime detection
- ❌ Real-time sentiment analysis
- ❌ News/event-driven trading
- ❌ Multiple specialized strategies for different conditions

### Current Problems:
- **Low profit:** 8.4% annual (worse than 12% risk-free alternatives)
- **Missed opportunities:** ADX >25 filter blocks trend-following
- **Single strategy:** Can't adapt to different market regimes
- **Manual intervention:** No automated response to market shifts

---

## Phase 1: AI Strategy Selector (Weeks 1-2)

### Objective
Deploy AI that analyzes market conditions every 4-6 hours and selects the optimal strategy.

### Components to Build

#### 1. Market Data Collector (`market_data.py`)
**Purpose:** Fetch all relevant market indicators

**Data Sources:**
- **Fear & Greed Index** (alternative.me API)
  - Current value, yesterday, last week, last month
  - Detect extreme fear (<25) or extreme greed (>75)
  
- **BTC Price & Volume** (Binance API)
  - Current price, 24h high/low, 24h change
  - Volume spike detection (>2× average)
  
- **Funding Rate** (Binance Futures API)
  - Current funding rate (every 8h)
  - Detect extremes (>+0.10% or <-0.10%)
  
- **Technical Indicators** (calculate from candles)
  - RSI (14-period): Oversold <30, Overbought >70
  - ADX (14-period): Ranging <25, Trending >25
  - EMA 50/200: Bull/bear regime detection
  - Bollinger Bands: Price deviation from mean
  
- **On-Chain Metrics** (Glassnode API - optional, requires subscription)
  - MVRV ratio: <1.0 = capitulation, >3.5 = top
  - Exchange reserves: Declining = supply squeeze
  
- **Social Sentiment** (LunarCrush API - optional, requires subscription)
  - Twitter mentions, engagement rate
  - Reddit sentiment, comment volume

**Output Format:**
```json
{
  "timestamp": "2026-07-08T10:00:00Z",
  "btc_price": 61716.0,
  "fear_greed_index": 20,
  "funding_rate": 0.0007,
  "rsi_14": 52.56,
  "adx_14": 18.3,
  "volume_24h": 19521.0,
  "volume_spike": false,
  "ema_50_over_200": true,
  "regime": "bull_consolidation"
}
```

**Files:**
- `scripts/market_data.py` - Data fetching logic
- `scripts/indicators.py` - Technical indicator calculations
- `scripts/config_apis.json` - API keys storage

---

#### 2. Strategy Library (4 Specialized Strategies)

##### Strategy A: ImprovedAdaptiveV3 (Already Exists)
**When to Use:** Ranging markets, neutral sentiment (F&G 30-70), ADX <25  
**Performance:** 100% win rate, 0.12 trades/day, 1-3% per trade  
**Timeframe:** 5m  
**Win Rate:** 100% (backtest)  
**File:** `strategies/ImprovedAdaptiveV3.py`

##### Strategy B: ContrarianbuyDips (NEW - Create)
**When to Use:** Extreme Fear (F&G <25), RSI <40, volume spike, ADX <25  
**Logic:**
- Buy capitulation dips aggressively
- Tighter stops (3% vs 5%)
- Larger position sizes (2× standard)
- Target 5-10% bounces
- Exit on Fear & Greed returning to 40+

**Parameters:**
```python
minimal_roi = {
    "0": 0.10,    # 10% target
    "60": 0.05,   # 5% after 1h
    "120": 0.03,  # 3% after 2h
}
stoploss = -0.03  # Tight 3% stop
buy_rsi = 35      # Enter earlier (vs 25)
volume_factor = 2.0  # Require 2× volume spike
```

**Expected:** 70-80% win rate, 3-5% per trade, 0.3-0.5 trades/day  
**File:** `strategies/ContrarianbuyDips.py`

##### Strategy C: TrendFollowingFixed (Fix Existing)
**When to Use:** ADX >25, clear trend direction, momentum building  
**Current Problem:** -10% stop loss too wide (lost money in backtest)  
**Fix:**
- Tighten stop loss: -10% → -5%
- Add ATR-based trailing stop (2× ATR)
- Require volume confirmation (≥1.5×)
- Add trend strength filter (ADX >30 for entries)

**Parameters:**
```python
minimal_roi = {
    "0": 0.20,     # 20% - let winners run
    "1440": 0.10,  # 10% after 1 day
    "2880": 0.05,  # 5% after 2 days
}
stoploss = -0.05   # Tighter 5% (was -10%)
adx_threshold = 30  # Stronger trends only (was 25)
volume_factor = 1.5
```

**Expected:** 45-55% win rate, 5-15% per trade, 0.1-0.2 trades/day  
**File:** `strategies/TrendFollowingFixed.py`

##### Strategy D: RangeScalper (NEW - Create)
**When to Use:** Low volatility, ADX <20, clear support/resistance  
**Logic:**
- Buy at support, sell at resistance
- Very tight stops (1-2%)
- High frequency (many small trades)
- Target 1-2% per trade

**Parameters:**
```python
minimal_roi = {
    "0": 0.03,    # 3% target
    "15": 0.02,   # 2% after 15min
    "30": 0.01,   # 1% after 30min
}
stoploss = -0.015  # Very tight 1.5%
timeframe = "5m"
adx_threshold = 20  # Only range-bound (<20)
```

**Expected:** 60-70% win rate, 1-2% per trade, 1-2 trades/day  
**File:** `strategies/RangeScalper.py`

---

#### 3. AI Strategy Selector (`ai_selector.py`)
**Purpose:** Analyze market data and select optimal strategy

**Logic Flow:**
```python
def select_strategy(market_data):
    """
    Uses Claude API to analyze market and recommend strategy
    """
    
    # Prepare prompt with current conditions
    prompt = f"""
You are an expert crypto trading AI. Analyze current market conditions and select the BEST strategy.

CURRENT MARKET DATA:
- Fear & Greed Index: {market_data['fear_greed_index']} (0=Extreme Fear, 100=Extreme Greed)
- BTC Price: ${market_data['btc_price']:,.2f}
- 24h Change: {market_data['price_change_24h']}%
- Funding Rate: {market_data['funding_rate']*100:.4f}% every 8h
- RSI (14): {market_data['rsi_14']:.2f}
- ADX (14): {market_data['adx_14']:.2f}
- Volume 24h: {market_data['volume_24h']:,.0f} BTC
- Volume Spike: {market_data['volume_spike']}
- Regime: {market_data['regime']}

AVAILABLE STRATEGIES:

1. ImprovedAdaptiveV3
   - Best for: Ranging markets (ADX <25), neutral sentiment (F&G 30-70)
   - Performance: 100% win rate, 1-3% per trade, 0.12 trades/day
   - Risk: Very low

2. ContrarianbuyDips
   - Best for: Extreme Fear (F&G <25), RSI <40, volume spike, capitulation
   - Performance: 70-80% win rate, 3-5% per trade, 0.3-0.5 trades/day
   - Risk: Medium

3. TrendFollowingFixed
   - Best for: Strong trends (ADX >30), momentum building, clear direction
   - Performance: 45-55% win rate, 5-15% per trade, 0.1-0.2 trades/day
   - Risk: High

4. RangeScalper
   - Best for: Low volatility (ADX <20), clear support/resistance
   - Performance: 60-70% win rate, 1-2% per trade, 1-2 trades/day
   - Risk: Low-Medium

RULES:
- If Fear & Greed <25 AND RSI <40 AND volume spike: STRONGLY favor ContrarianbuyDips
- If ADX >30 AND clear trend: Consider TrendFollowingFixed
- If ADX <20 AND low volatility: Consider RangeScalper
- If neutral conditions: Default to ImprovedAdaptiveV3 (safest)
- NEVER deploy TrendFollowing during Fear <25 (catastrophic in bear markets)

Respond ONLY with JSON (no markdown, no explanation):
{{
  "strategy": "strategy_name",
  "confidence": 1-10,
  "reasoning": "2-3 sentence explanation",
  "duration": "4h/8h/12h/24h",
  "max_drawdown_acceptable": "5%/10%/15%",
  "alternative": "backup strategy if primary fails"
}}
"""
    
    # Call Claude API
    response = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")).messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Parse JSON response
    decision = json.loads(response.content[0].text)
    
    return decision
```

**Output Example:**
```json
{
  "strategy": "ContrarianbuyDips",
  "confidence": 9,
  "reasoning": "Extreme Fear (20) with neutral RSI suggests capitulation near. No volume spike yet, but fear this low often precedes recoveries. ADX <25 confirms no strong downtrend.",
  "duration": "12h",
  "max_drawdown_acceptable": "10%",
  "alternative": "ImprovedAdaptiveV3"
}
```

**Files:**
- `scripts/ai_selector.py` - AI decision logic
- `scripts/.env` - ANTHROPIC_API_KEY storage

---

#### 4. Strategy Deployer (`deploy.py`)
**Purpose:** Update Freqtrade config and restart bot with selected strategy

**Logic:**
```python
def deploy_strategy(strategy_name, duration_hours):
    """
    1. Stop current Freqtrade container
    2. Update config-live.json with new strategy
    3. Restart container
    4. Log deployment
    """
    
    # Stop bot
    subprocess.run(["docker-compose", "-f", "docker-compose.yml", "stop", "freqtrade-live"])
    
    # Update config
    config = load_json("config-live.json")
    config["strategy"] = strategy_name
    save_json("config-live.json", config)
    
    # Restart bot
    subprocess.run(["docker-compose", "-f", "docker-compose.yml", "up", "-d", "freqtrade-live"])
    
    # Log deployment
    log_deployment(strategy_name, duration_hours, datetime.now())
    
    print(f"✅ Deployed: {strategy_name} for {duration_hours}h")
```

**Files:**
- `scripts/deploy.py` - Deployment logic
- `logs/deployments.json` - Deployment history

---

#### 5. Main Orchestrator (`run_ai_selector.py`)
**Purpose:** Main script that runs every 4-6 hours

**Logic:**
```python
#!/usr/bin/env python3
import time
from market_data import fetch_market_data
from ai_selector import select_strategy
from deploy import deploy_strategy, get_current_strategy
from logger import log_decision

def main():
    print("🤖 AI Strategy Selector - Running Analysis...")
    
    # 1. Fetch current market data
    market_data = fetch_market_data()
    print(f"📊 Market Data: F&G={market_data['fear_greed_index']}, RSI={market_data['rsi_14']:.1f}, ADX={market_data['adx_14']:.1f}")
    
    # 2. Get AI recommendation
    decision = select_strategy(market_data)
    print(f"🧠 AI Decision: {decision['strategy']} (confidence: {decision['confidence']}/10)")
    print(f"💡 Reasoning: {decision['reasoning']}")
    
    # 3. Check if we should deploy
    current_strategy = get_current_strategy()
    
    if decision['strategy'] == current_strategy:
        print(f"✅ Already running {current_strategy}, no change needed")
    elif decision['confidence'] >= 7:
        print(f"🚀 Deploying new strategy: {decision['strategy']}")
        deploy_strategy(decision['strategy'], decision['duration'])
    else:
        print(f"⚠️  Confidence too low ({decision['confidence']}/10), keeping {current_strategy}")
    
    # 4. Log decision
    log_decision(market_data, decision, deployed=(decision['confidence'] >= 7))
    
    print("✅ Analysis complete\n")

if __name__ == "__main__":
    main()
```

**Cron Job (runs every 4 hours):**
```bash
# /etc/cron.d/ai-selector
0 */4 * * * cd /Users/nlanatta/Documents/Projects/Personal/traidingAI/freqtradebot && python3 scripts/run_ai_selector.py >> logs/ai_selector.log 2>&1
```

**Files:**
- `scripts/run_ai_selector.py` - Main orchestrator
- `scripts/logger.py` - Decision logging
- `logs/ai_selector.log` - Execution logs
- `logs/decisions.json` - All AI decisions

---

#### 6. Monitoring Dashboard (Optional)
**Purpose:** Web UI to monitor AI decisions and performance

**Features:**
- Current strategy deployed
- AI decision history (last 7 days)
- Performance metrics per strategy
- Market conditions timeline
- Next analysis countdown

**Tech Stack:**
- Flask (Python web framework)
- Chart.js (visualizations)
- Tailwind CSS (styling)

**Files:**
- `dashboard/app.py` - Flask app
- `dashboard/templates/index.html` - Dashboard UI
- `dashboard/static/` - CSS/JS assets

---

### Implementation Steps (Phase 1)

**Week 1:**
- [ ] Day 1-2: Create `market_data.py` - Fetch all market indicators
- [ ] Day 3: Create `ai_selector.py` - AI decision logic
- [ ] Day 4: Create `deploy.py` - Strategy deployment
- [ ] Day 5: Create `run_ai_selector.py` - Main orchestrator
- [ ] Day 6: Test manually (run selector, verify deployment)
- [ ] Day 7: Set up cron job, monitor first 24h

**Week 2:**
- [ ] Day 8-9: Create `ContrarianbuyDips.py` strategy
- [ ] Day 10-11: Fix `TrendFollowingFixed.py` strategy
- [ ] Day 12-13: Create `RangeScalper.py` strategy
- [ ] Day 14: Backtest all strategies, verify performance

### Expected Results (Phase 1)

**Performance Targets:**
- 20-30% annual return (vs 8.4% currently)
- 0.5-1.0 trades/day (vs 0.12 currently)
- 70-85% win rate across all strategies
- Max drawdown: 15-20%

**Key Metrics to Track:**
- Strategy selection accuracy (did AI pick optimal strategy?)
- Win rate per strategy
- Profit per strategy
- Time deployed per strategy
- Market regime detection accuracy

**Success Criteria:**
- [ ] AI selector runs automatically every 4h without errors
- [ ] Strategies deploy successfully and execute trades
- [ ] Combined performance >15% after 1 month
- [ ] No catastrophic losses (max -20% drawdown)

---

## Phase 2: AI News Trader (Weeks 3-4)

### Objective
Add event-driven trading based on real-time news and announcements.

### Components to Build

#### 1. News Monitor (`news_monitor.py`)
**Data Sources:**
- CoinTelegraph RSS feed
- Decrypt RSS feed
- CryptoNews RSS feed
- Twitter API (whale alerts, major influencers)
- Binance announcements (new listings, delistings)

#### 2. News Analyzer (`news_analyzer.py`)
**Uses AI to detect:**
- Exchange listing announcements → Buy before listing
- Token unlock announcements → Sell before unlock
- Partnership announcements → Buy on news
- Regulatory news → Short/long based on impact
- Whale movements → Follow smart money

#### 3. Quick Executor (`quick_executor.py`)
**Purpose:** Execute trades within minutes of news

**Logic:**
- Bypass normal strategy (direct API execution)
- Tight stops (1-2%)
- Target 3-10% profit
- 15min-4h hold time

### Expected Results (Phase 2)
- 5-10 event-driven trades per month
- 5-20% profit per trade
- **Combined with Phase 1: 30-50% annual**

---

## Phase 3: AI Sentiment Scalper (Weeks 5-6)

### Objective
Trade real-time sentiment extremes on social media.

### Components to Build

#### 1. Sentiment Monitor (`sentiment_monitor.py`)
**Data Sources:**
- LunarCrush API (Twitter sentiment, mentions)
- Reddit API (r/cryptocurrency sentiment)
- Google Trends API (search volume spikes)
- Telegram API (group activity tracking)

#### 2. Sentiment Analyzer (`sentiment_analyzer.py`)
**Detects:**
- FOMO spikes (mentions 5× normal → short setup)
- Fear spikes (mentions drop 80% → buy setup)
- Sentiment divergence (price up, sentiment down → distribution)

#### 3. Sentiment Scalper (`sentiment_scalper.py`)
**Executes:**
- Quick scalps (15min-2h holds)
- Target 2-5% per trade
- 20-40 trades per month

### Expected Results (Phase 3)
- 20-40 sentiment scalps per month
- 2-5% profit per trade
- **Combined: 45-75% annual**

---

## Phase 4: AI Liquidation Trader (Weeks 7-8)

### Objective
Position before predictable liquidation cascades.

### Components to Build

#### 1. Liquidation Monitor (`liquidation_monitor.py`)
**Data Sources:**
- Coinglass API (liquidation heatmap)
- Binance liquidation data
- Aggregate liquidation clusters

#### 2. Cascade Predictor (`cascade_predictor.py`)
**AI Analyzes:**
- Liquidation cluster sizes
- Distance from current price
- Likelihood of cascade trigger
- Direction (up or down)

#### 3. Cascade Trader (`cascade_trader.py`)
**Strategies:**
- Short before downward cascade
- Buy the V-bottom after cascade
- Target 5-20% moves

### Expected Results (Phase 4)
- 3-5 cascade trades per month
- 5-15% profit per trade
- **Combined: 65-105% annual**

---

## Technical Architecture

### File Structure
```
freqtradebot/
├── config-live.json          # Freqtrade config
├── docker-compose.yml         # Docker setup
├── AI-TRADING-PLAN.md        # This document
│
├── strategies/               # Trading strategies
│   ├── ImprovedAdaptiveV3.py       ✅ Exists
│   ├── ContrarianbuyDips.py        🔨 Create (Phase 1)
│   ├── TrendFollowingFixed.py      🔧 Fix (Phase 1)
│   └── RangeScalper.py             🔨 Create (Phase 1)
│
├── scripts/                  # AI trading scripts
│   ├── market_data.py              🔨 Create (Phase 1)
│   ├── indicators.py               🔨 Create (Phase 1)
│   ├── ai_selector.py              🔨 Create (Phase 1)
│   ├── deploy.py                   🔨 Create (Phase 1)
│   ├── run_ai_selector.py          🔨 Create (Phase 1)
│   ├── logger.py                   🔨 Create (Phase 1)
│   ├── news_monitor.py             🔨 Create (Phase 2)
│   ├── news_analyzer.py            🔨 Create (Phase 2)
│   ├── quick_executor.py           🔨 Create (Phase 2)
│   ├── sentiment_monitor.py        🔨 Create (Phase 3)
│   ├── sentiment_analyzer.py       🔨 Create (Phase 3)
│   ├── sentiment_scalper.py        🔨 Create (Phase 3)
│   ├── liquidation_monitor.py      🔨 Create (Phase 4)
│   ├── cascade_predictor.py        🔨 Create (Phase 4)
│   ├── cascade_trader.py           🔨 Create (Phase 4)
│   ├── config_apis.json            🔨 Create (Phase 1)
│   └── .env                        🔨 Create (Phase 1)
│
├── logs/                     # Logs and history
│   ├── ai_selector.log
│   ├── decisions.json
│   ├── deployments.json
│   └── trades.json
│
└── dashboard/                # Monitoring UI (optional)
    ├── app.py
    ├── templates/
    └── static/
```

### APIs Required

**Free (No Cost):**
- ✅ Binance API (price, volume, funding, candles)
- ✅ Alternative.me (Fear & Greed Index)
- ✅ CoinTelegraph RSS (news)
- ✅ Decrypt RSS (news)
- ✅ Twitter API (limited free tier)

**Paid (Optional):**
- 💰 Anthropic Claude API ($15/month for ~500k tokens)
- 💰 LunarCrush API ($50/month for sentiment data)
- 💰 Glassnode API ($29/month for on-chain metrics)
- 💰 Coinglass API ($20/month for liquidation data)

**Phase 1 Costs:**
- Anthropic Claude API only: ~$15/month
- **Total Phase 1:** ~$15/month

---

## Risk Management

### Position Sizing Rules
- Max 20% capital per strategy at any time
- Max 5% risk per trade
- Emergency stop: -20% portfolio drawdown

### Strategy Allocation
- **Low Risk (V3, RangeScalper):** 60% capital
- **Medium Risk (ContrarianbuyDips):** 30% capital
- **High Risk (TrendFollowing):** 10% capital

### Safety Mechanisms
- [ ] AI confidence threshold (≥7/10 to deploy)
- [ ] Max 3 strategy switches per day (prevent thrashing)
- [ ] Manual override capability
- [ ] Emergency stop button
- [ ] Daily PnL limits (-5% per day = pause trading)

---

## Success Metrics

### Phase 1 (Weeks 1-2)
- [ ] AI selector running automatically every 4h
- [ ] 3+ strategies deployed in first week
- [ ] Win rate ≥65% across all strategies
- [ ] Return ≥5% in first 2 weeks

### Phase 2 (Weeks 3-4)
- [ ] 5+ event-driven trades executed
- [ ] News detection <5min latency
- [ ] Event trade win rate ≥60%
- [ ] Cumulative return ≥10%

### Phase 3 (Weeks 5-6)
- [ ] 20+ sentiment scalps executed
- [ ] Sentiment detection real-time (<1min)
- [ ] Scalp win rate ≥60%
- [ ] Cumulative return ≥20%

### Phase 4 (Weeks 7-8)
- [ ] 3+ liquidation cascade trades
- [ ] Cascade prediction accuracy ≥70%
- [ ] Cascade trade win rate ≥65%
- [ ] Cumulative return ≥30%

---

## Rollback Plan

### If Phase 1 Fails (<10% return after 2 weeks):
1. Revert to static ImprovedAdaptiveV3
2. Increase stake_amount to $80 (simple profit boost)
3. Debug AI selector decision accuracy
4. Adjust confidence threshold

### If Any Strategy Loses >10%:
1. Immediately disable that strategy
2. Analyze failure mode
3. Backtest fixes before re-enabling
4. Lower allocation to 5% capital for testing

### Emergency Stop Triggers:
- Portfolio drawdown >20% (stop all trading)
- Any single strategy drawdown >15% (disable strategy)
- 3 consecutive losing days (pause for review)

---

## Next Steps

**Immediate (Today):**
1. ✅ Create this plan document
2. 🔨 Set up project structure (folders: scripts/, logs/, dashboard/)
3. 🔨 Create `scripts/market_data.py` - First component

**This Week:**
1. Complete market_data.py and test API connections
2. Build ai_selector.py with Claude API integration
3. Create deploy.py for strategy switching
4. Test full flow manually

**Next Week:**
1. Build 3 new strategies (ContrarianbuyDips, RangeScalper, fix TrendFollowing)
2. Set up cron job for automated execution
3. Monitor first 24h of automated AI selection

---

## Appendix A: API Keys Needed

**Required for Phase 1:**
- `ANTHROPIC_API_KEY` - Claude API (get from console.anthropic.com)
- `BINANCE_API_KEY` - Already have (BingX)
- `BINANCE_API_SECRET` - Already have (BingX)

**Optional for Phase 2+:**
- `LUNARCRUSH_API_KEY` - Sentiment data
- `GLASSNODE_API_KEY` - On-chain metrics
- `COINGLASS_API_KEY` - Liquidation data
- `TWITTER_BEARER_TOKEN` - Twitter API

---

## Appendix B: Current Market Analysis (2026-07-08)

**Current Conditions:**
- Fear & Greed Index: 20 (Extreme Fear)
- BTC Price: $61,716
- Funding Rate: +0.0007% (neutral)
- RSI: 52.56 (neutral)
- ADX: ~18-20 (ranging)

**AI Would Select:**
**Strategy:** ContrarianbuyDips (if RSI drops below 40) OR ImprovedAdaptiveV3 (current neutral RSI)  
**Confidence:** 7-8/10  
**Reasoning:** Extreme Fear suggests capitulation near, but RSI not yet oversold. Deploy conservative mean reversion, watch for volume spike + RSI <40 to switch to aggressive contrarian.

---

**Plan Version:** 1.0  
**Last Updated:** 2026-07-08  
**Status:** Ready to implement Phase 1
