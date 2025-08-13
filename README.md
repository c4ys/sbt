# STB - Simple Backtest

基于 xtquant 打造的简单回测框架，支持自研轻量回测引擎（Bokeh 可视化）与 Backtesting.py 双路径。

## 用法

```python

# 获取股票历史数据
rye run sbt data download_history --code_list=159922.SZ --start_date=20240901 --end_date=20250808 --period=5m

# 运行回测（自研引擎优先）
rye run sbt backtest run --code_list=159922.SZ --start_date=20240901 --end_date=20250808 --period=30m --strategy=SMACross --cash=10000000

```
