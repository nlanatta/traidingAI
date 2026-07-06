#!/bin/bash
# Compare SampleStrategy vs CustomSampleStrategy performance

# Determine database path based on where script is run from
if [ -d "freqtrade/user_data" ]; then
    DB_PATH="freqtrade/user_data"
elif [ -d "user_data" ]; then
    DB_PATH="user_data"
else
    echo "Error: Cannot find user_data directory"
    exit 1
fi

echo "=========================================="
echo "STRATEGY COMPARISON"
echo "=========================================="
echo ""

echo "📊 SampleStrategy (Original - No ADX filter)"
echo "Database: ${DB_PATH}/tradesv3.sqlite"
echo "------------------------------------------"
sqlite3 "${DB_PATH}/tradesv3.sqlite" "
SELECT
  COUNT(*) as total_trades,
  SUM(CASE WHEN is_open=0 AND close_profit > 0 THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN is_open=0 AND close_profit <= 0 THEN 1 ELSE 0 END) as losses,
  ROUND(AVG(CASE WHEN is_open=0 THEN close_profit * 100 END), 2) as avg_profit_pct,
  ROUND(SUM(CASE WHEN is_open=0 THEN close_profit_abs END), 2) as total_profit_usdt,
  ROUND(MIN(CASE WHEN is_open=0 THEN close_profit * 100 END), 2) as worst_trade_pct,
  ROUND(MAX(CASE WHEN is_open=0 THEN close_profit * 100 END), 2) as best_trade_pct
FROM trades;
"
echo ""
echo "Recent trades:"
sqlite3 "${DB_PATH}/tradesv3.sqlite" "
SELECT
  pair,
  datetime(open_date, 'localtime') as opened,
  datetime(close_date, 'localtime') as closed,
  ROUND(close_profit_abs, 2) as profit_usdt,
  ROUND(close_profit * 100, 2) as profit_pct
FROM trades
WHERE is_open=0
ORDER BY close_date DESC
LIMIT 5;
"

echo ""
echo "=========================================="
echo ""

echo "🧪 CustomSampleStrategy (ADX < 25 filter)"
echo "Database: ${DB_PATH}/tradesv3-custom.sqlite"
echo "------------------------------------------"
sqlite3 "${DB_PATH}/tradesv3-custom.sqlite" "
SELECT
  COUNT(*) as total_trades,
  SUM(CASE WHEN is_open=0 AND close_profit > 0 THEN 1 ELSE 0 END) as wins,
  SUM(CASE WHEN is_open=0 AND close_profit <= 0 THEN 1 ELSE 0 END) as losses,
  ROUND(AVG(CASE WHEN is_open=0 THEN close_profit * 100 END), 2) as avg_profit_pct,
  ROUND(SUM(CASE WHEN is_open=0 THEN close_profit_abs END), 2) as total_profit_usdt,
  ROUND(MIN(CASE WHEN is_open=0 THEN close_profit * 100 END), 2) as worst_trade_pct,
  ROUND(MAX(CASE WHEN is_open=0 THEN close_profit * 100 END), 2) as best_trade_pct
FROM trades;
"
echo ""
echo "Recent trades:"
sqlite3 "${DB_PATH}/tradesv3-custom.sqlite" "
SELECT
  pair,
  datetime(open_date, 'localtime') as opened,
  datetime(close_date, 'localtime') as closed,
  ROUND(close_profit_abs, 2) as profit_usdt,
  ROUND(close_profit * 100, 2) as profit_pct
FROM trades
WHERE is_open=0
ORDER BY close_date DESC
LIMIT 5;
"

echo ""
echo "=========================================="
echo "KEY METRICS TO WATCH:"
echo "=========================================="
echo "✅ Win Rate: CustomSampleStrategy should have similar or better"
echo "✅ Worst Trade: Should avoid catastrophic -10% stop-losses"
echo "✅ Total Profit: Should be positive after 20-30 trades"
echo "⚠️  Total Trades: May have fewer trades (ADX filter rejects more entries)"
echo ""
