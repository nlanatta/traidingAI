# Trading Strategies

This directory contains your custom freqtrade trading strategies.

## Available Strategies

- `SampleStrategy.py` - Example strategy from freqtrade (reference)
- `CustomSampleStrategy.py` - Modified sample strategy

## Creating a New Strategy

1. Copy an existing strategy as a template:
   ```bash
   cp CustomSampleStrategy.py MyNewStrategy.py
   ```

2. Edit the class name and implement your logic:
   ```python
   class MyNewStrategy(IStrategy):
       # Your strategy implementation
   ```

3. Test with backtesting:
   ```bash
   cd ../freqtrade
   freqtrade backtesting --config ../config.json --strategy MyNewStrategy
   ```

4. Commit to git:
   ```bash
   cd /Users/nlanatta/Documents/Projects/Personal/traidingAI
   git add freqtradebot/strategies/MyNewStrategy.py
   git commit -m "Add new strategy"
   ```

## Strategy Development Tips

- Start with backtesting on historical data
- Use dry-run mode before live trading
- Test across different market conditions
- Keep strategies simple and understandable
- Document your strategy logic

## Resources

- [Freqtrade Strategy Customization](https://www.freqtrade.io/en/stable/strategy-customization/)
- [Strategy Callbacks](https://www.freqtrade.io/en/stable/strategy-callbacks/)
- [Strategy Analysis](https://www.freqtrade.io/en/stable/strategy-analysis/)
