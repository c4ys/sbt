from __future__ import annotations
from typing import Type, Dict, Any
import pandas as pd
from bokeh.plotting import figure, output_file, save, show
from bokeh.layouts import gridplot
from bokeh.models import (
    ColumnDataSource, Range1d, CustomJSTickFormatter, NumeralTickFormatter, 
    HoverTool, Span, CrosshairTool
)

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

        # 通用工具配置（移除crosshair，我们将手动实现）
        tools = "xpan,xwheel_zoom,xwheel_pan,box_zoom,reset"
        
        # 参考 backtesting.py 的链接十字星实现
        linked_crosshair = CrosshairTool(
            dimensions='both', 
            line_color='lightgrey',
            overlay=(
                Span(dimension="width", line_dash="dotted", line_width=1),
                Span(dimension="height", line_dash="dotted", line_width=1)
            ),
        )

        # 1) K线图 - 参考 backtesting.py 的 OHLC 实现
        p_ohlc = figure(
            title="K线图",
            x_axis_type="linear",
            height=400,
            width=1200,
            sizing_mode="stretch_width",
            x_range=x_range,
            tools=tools,
            toolbar_location=None,
        )
        
        # 为K线图添加悬停工具
        ohlc_hover = HoverTool(
            tooltips=[
                ("时间", "@datetime{%F %T}"),
                ("开盘", "@Open{0,0.00}"),
                ("最高", "@High{0,0.00}"),
                ("最低", "@Low{0,0.00}"),
                ("收盘", "@Close{0,0.00}"),
                ("成交量", "@Volume{0,0}")
            ],
            formatters={'@datetime': 'datetime'},
            mode='vline'
        )
        p_ohlc.add_tools(ohlc_hover)
        p_ohlc.add_tools(linked_crosshair)
        
        # 绘制K线 - 使用连续的时间轴
        w = 0.8
        
        # 为每根K线添加颜色和形状信息到数据源
        df_plot = df.copy()
        df_plot['color'] = ['red' if close > open else 'green' for close, open in zip(df['Close'], df['Open'])]
        df_plot['top'] = [max(close, open) for close, open in zip(df['Close'], df['Open'])]
        df_plot['bottom'] = [min(close, open) for close, open in zip(df['Close'], df['Open'])]
        
        # 更新数据源包含新字段
        source_ohlc = ColumnDataSource(data={
            'index': list(range(len(df_plot))),
            'datetime': df_plot.index.tolist(),
            'Open': df_plot['Open'].tolist(),
            'High': df_plot['High'].tolist(),
            'Low': df_plot['Low'].tolist(),
            'Close': df_plot['Close'].tolist(),
            'Volume': df_plot['Volume'].tolist(),
            'color': df_plot['color'].tolist(),
            'top': df_plot['top'].tolist(),
            'bottom': df_plot['bottom'].tolist(),
        })
        
        # 绘制影线（高低线）- 使用连续的索引
        p_ohlc.segment('index', 'High', 'index', 'Low', source=source_ohlc, color="black", line_width=1)
        
        # 绘制K线实体 - 使用单一数据源和颜色字段
        p_ohlc.vbar(x='index', width=w, top='top', bottom='bottom', 
                   source=source_ohlc, color='color', alpha=0.8, line_color="black")

        # 添加买卖点标记 - 参考 backtesting.py 的交易标记
        if hasattr(self.strategy, 'trades') and len(self.strategy.trades) > 0:
            trades_df = pd.DataFrame(self.strategy.trades)
            if not trades_df.empty:
                # 买入点（绿色向上三角形）
                buy_trades = trades_df[trades_df['side'] == 'buy'].copy()
                if not buy_trades.empty:
                    # 使用交易时的索引位置
                    buy_trades['x'] = buy_trades['i']  # 使用策略记录的索引
                    buy_trades['y'] = buy_trades['price']
                    buy_source = ColumnDataSource(buy_trades)
                    p_ohlc.scatter(x='x', y='y', source=buy_source, 
                                  marker='triangle', size=12, color="green", alpha=0.8, 
                                  legend_label="买入")
                
                # 卖出点（红色向下三角形）  
                sell_trades = trades_df[trades_df['side'] == 'sell'].copy()
                if not sell_trades.empty:
                    # 使用交易时的索引位置
                    sell_trades['x'] = sell_trades['i']  # 使用策略记录的索引
                    sell_trades['y'] = sell_trades['price']
                    sell_source = ColumnDataSource(sell_trades)
                    p_ohlc.scatter(x='x', y='y', source=sell_source,
                                  marker='inverted_triangle', size=12, color="red", alpha=0.8,
                                  legend_label="卖出")
        
        # 设置K线图的图例位置
        p_ohlc.legend.location = "top_left"
        p_ohlc.legend.click_policy = "hide"
        
        # 为K线图添加时间格式化
        p_ohlc.xaxis.formatter = CustomJSTickFormatter(
            args=dict(source=source_ohlc),
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

        # 2) 成交量图
        p_volume = figure(
            title="成交量",
            x_axis_type="linear",
            height=120,
            width=1200,
            sizing_mode="stretch_width",
            x_range=x_range,
            tools=tools,
            toolbar_location=None,  # 隐藏单个图表的工具栏
        )
        
        # 为成交量图添加悬停工具
        volume_hover = HoverTool(
            tooltips=[
                ("时间", "@datetime{%F %T}"),
                ("开盘价", "@Open{0,0.00}"),
                ("最高价", "@High{0,0.00}"),
                ("最低价", "@Low{0,0.00}"),
                ("收盘价", "@Close{0,0.00}"),
                ("成交量", "@Volume{0,0}")
            ],
            formatters={'@datetime': 'datetime'},
            mode='vline'
        )
        p_volume.add_tools(volume_hover)
        
        # 添加链接十字星工具
        p_volume.add_tools(linked_crosshair)
        
        w = 0.8
        inc = df['Close'] > df['Open']
        dec = ~inc
        inc_idx = [i for i in range(n_bars) if inc.iloc[i]]
        dec_idx = [i for i in range(n_bars) if dec.iloc[i]]
        
        # 创建涨跌分组的数据源
        if 'Volume' in df.columns:
            if inc_idx:
                inc_source = ColumnDataSource(data={
                    'x': inc_idx,
                    'top': df['Volume'].iloc[inc_idx].values,
                    'datetime': df['datetime'].iloc[inc_idx],
                    'Open': df['Open'].iloc[inc_idx],
                    'High': df['High'].iloc[inc_idx],
                    'Low': df['Low'].iloc[inc_idx],
                    'Close': df['Close'].iloc[inc_idx],
                    'Volume': df['Volume'].iloc[inc_idx]
                })
                p_volume.vbar(x='x', width=w, top='top', bottom=0, 
                            color="green", alpha=0.7, source=inc_source)
            
            if dec_idx:
                dec_source = ColumnDataSource(data={
                    'x': dec_idx,
                    'top': df['Volume'].iloc[dec_idx].values,
                    'datetime': df['datetime'].iloc[dec_idx],
                    'Open': df['Open'].iloc[dec_idx],
                    'High': df['High'].iloc[dec_idx],
                    'Low': df['Low'].iloc[dec_idx],
                    'Close': df['Close'].iloc[dec_idx],
                    'Volume': df['Volume'].iloc[dec_idx]
                })
                p_volume.vbar(x='x', width=w, top='top', bottom=0, 
                            color="red", alpha=0.7, source=dec_source)
        p_volume.yaxis.formatter = NumeralTickFormatter(format="0 a")
        p_volume.xaxis.visible = False

        # 3) 资金曲线图
        p_equity = figure(
            title="资金曲线",
            x_axis_type="linear",
            height=250,
            width=1200,
            sizing_mode="stretch_width",
            x_range=x_range,
            tools=tools,
            toolbar_location=None,  # 隐藏单个图表的工具栏
        )
        
        # 为资金曲线创建数据源
        eq_idx = list(range(len(eq)))
        # 计算收益率
        eq_returns = (eq / eq.iloc[0] - 1) * 100  # 转换为百分比
        equity_source = ColumnDataSource(data={
            'index': eq_idx,
            'equity': eq.values,
            'returns': eq_returns.values,
            'datetime': eq.index[:len(eq_idx)]
        })
        
        # 为资金曲线图添加悬停工具
        equity_hover = HoverTool(
            tooltips=[
                ("时间", "@datetime{%F %T}"),
                ("资金", "@equity{$ 0,0.00}"),
                ("收益率", "@returns{+0.00}%"),
                ("索引", "@index")
            ],
            formatters={'@datetime': 'datetime'},
            mode='vline'
        )
        p_equity.add_tools(equity_hover)
        
        # 添加链接十字星工具
        p_equity.add_tools(linked_crosshair)
        
        # 绘制资金曲线线条
        p_equity.line('index', 'equity', source=equity_source, color="navy", 
                     line_width=2, alpha=0.9, legend_label="资金曲线")
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

        # 布局与输出 - 使用 gridplot 而不是 column 以避免显示问题
        figs = [p_ohlc, p_volume, p_equity]
        
        # 配置工具栏选项
        kwargs = {}
        kwargs['sizing_mode'] = 'stretch_width'
        
        layout = gridplot(
            figs,
            ncols=1,
            toolbar_location='right',
            toolbar_options=dict(logo=None),
            merge_tools=True,
            **kwargs
        )
        if filename is None:
            filename = "backtest_result.html"
        output_file(filename, title="回测结果")
        if show_in_browser:
            show(layout)
        else:
            save(layout)
        return filename
