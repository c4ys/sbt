# STB - Simple Backtest

基于xtquant和Backtesting.py打造的简单回测框架

## 用法

```python

# 获取股票历史数据
rye run sbt data download_history --code_list=000001.SH,002097.SZ --start_date=20240901 --end_date=20250808 --period=30m

# 运行回测
rye run sbt backtest run --code_list=000001.SH,002097.SZ --start_date=20240901 --end_date=20250808 --period=30m --strategy=SMACross
```
