from sbt.backtest import BacktestEngine
import pandas as pd


def make_demo_df(n=300):
    import random
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    # 生成一个略带趋势和噪声的价格序列（无 numpy 依赖）
    close = []
    cur = 100.0
    step = (120.0 - 100.0) / n
    for _ in range(n):
        cur += step + random.uniform(-0.8, 0.8)
        close.append(cur)
    return pd.DataFrame({"Close": close}, index=idx)


def run():
    df = make_demo_df()
    from strategies.SMACrossSimple import SMACrossSimple
    bt = BacktestEngine(df, SMACrossSimple, cash=100000, commission=0.002)
    res = bt.run()
    html = bt.plot("example_result.html")
    print(res)
    print("saved:", html)


if __name__ == "__main__":
    run()
