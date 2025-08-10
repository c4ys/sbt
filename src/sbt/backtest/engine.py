from __future__ import annotations
from typing import Type, Dict, Any
import pandas as pd
from bokeh.plotting import figure, output_file, save, show
from bokeh.models import ColumnDataSource, Range1d, CustomJSTickFormatter, NumeralTickFormatter

from .strategy import StrategyBase

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, strategy_cls: Type[StrategyBase], cash: float = 10000.0, commission: float = 0.002):
        self.data = data
        self.strategy = strategy_cls(data, cash=cash, commission=commission)

    def run(self) -> Dict[str, Any]:
        for i in range(len(self.data)):
            self.strategy.step(i)
        return self.strategy.metrics()

    def plot(self, filename: str = None, show_in_browser: bool = False) -> str:
        if len(self.strategy.equity_curve) == 0:
            raise ValueError("没有权益曲线数据，请先运行回测")

        # 资金曲线序列（用于第三幅图）
        eq = pd.Series(self.strategy.equity_curve, index=self.data.index[:len(self.strategy.equity_curve)])

        # 准备数据源：保存原始时间戳，使用线性索引驱动坐标轴
        df = self.data.copy()
        df = df.assign(datetime=df.index)
        df = df.reset_index(drop=True)
        n_bars = len(df)
        source = ColumnDataSource(df)

        # 1) K线图：线性x轴，避免非交易时间的空隙
        pad = (n_bars - 1) / 20 if n_bars > 1 else 1
        x_range = Range1d(0, max(n_bars - 1, 1), min_interval=10, bounds=(-pad, max(n_bars - 1, 1) + pad))
        
        # 3) 资金曲线图
        p_equity = figure(
            title="资金曲线",
            x_axis_type="linear",
            height=250,
            width=1200,
            sizing_mode="stretch_width",
            x_range=x_range,
            tools="xpan,xwheel_zoom,xwheel_pan,box_zoom,reset",
        )
        eq_idx = list(range(len(eq)))
        p_equity.line(eq_idx, eq.values, color="navy", line_width=2, alpha=0.9, legend_label="资金曲线")
        if len(eq) > 1:
            # Max Drawdown
            rolling_max = eq.cummax()
            drawdown_pct = (eq / rolling_max - 1) * 100
            max_dd_idx = drawdown_pct.idxmin()
            max_dd_val = drawdown_pct.min()
            if max_dd_val < -1:
                max_dd_pos = eq.index.get_loc(max_dd_idx)
                p_equity.scatter([max_dd_pos], [eq.iloc[max_dd_pos]], size=8, color="red", alpha=0.8, legend_label=f"最大回撤 {max_dd_val:.1f}%")

            # Peak and Final values
            peak_val = eq.max()
            peak_idx = eq.index.get_loc(eq.idxmax())
            final_val = eq.iloc[-1]
            final_idx = len(eq) - 1

            start_equity = eq.iloc[0]
            peak_return_pct = peak_val / start_equity
            final_return_pct = final_val / start_equity
            
            p_equity.scatter([peak_idx], [peak_val], size=8, color="cyan", alpha=1.0, legend_label=f"峰值: {peak_return_pct:.2%}")
            p_equity.scatter([final_idx], [final_val], size=8, color="blue", alpha=1.0, legend_label=f"最终: {final_return_pct:.2%}")

            # Annualized return calculation
            start_date = eq.index[0]
            end_date = eq.index[-1]
            duration_days = (end_date - start_date).days
            
            # Avoid division by zero for very short backtests
            if duration_days > 0:
                duration_years = duration_days / 365.25
                total_return = (eq.iloc[-1] / eq.iloc[0]) - 1
                annualized_return = (1 + total_return) ** (1 / duration_years) - 1
                p_equity.title.text = f"资金曲线 (年化收益: {annualized_return:.2%})"
            else:
                p_equity.title.text = "资金曲线"

        p_equity.legend.location = "top_left"
        p_equity.yaxis.formatter = NumeralTickFormatter(format="0,0")
        
        p_equity.xaxis.formatter = CustomJSTickFormatter(
            args=dict(source=source),
            code="""
            const idx = Math.round(tick);
            const dts = source.data.datetime;
            if (idx >= 0 && idx < dts.length) {
                const dt = new Date(dts[idx]);
                const mm = String(dt.getMonth()+1).padStart(2,'0');
                const dd = String(dt.getDate()).padStart(2,'0');
                const hh = String(dt.getHours()).padStart(2,'0');
                const mi = String(dt.getMinutes()).padStart(2,'0');
                return `${mm}/${dd} ${hh}:${mi}`;
            }
            return '';
            """
        )

        # 布局与输出
        layout = p_equity
        if filename is None:
            filename = "backtest_result.html"
        output_file(filename, title="回测结果")
        if show_in_browser:
            show(layout)
        else:
            save(layout)
        return filename
