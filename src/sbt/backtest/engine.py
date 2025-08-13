from __future__ import annotations
from typing import Type, Dict, Any
import pandas as pd
from pyecharts import options as opts
from pyecharts.charts import Kline, Line, Bar, Grid
from pyecharts.globals import ThemeType
import webbrowser
import os

from .strategy import StrategyBase

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, strategy_cls: Type[StrategyBase], cash: float = 1000000.0, commission: float = 0.002):
        self.data = data
        self.strategy = strategy_cls(data, cash=cash, commission=commission)

    def run(self) -> Dict[str, Any]:
        for i in range(len(self.data)):
            self.strategy.step(i)
        return self.strategy.metrics()

    def plot(self, filename: str = None, show_in_browser: bool = False) -> str:
        if len(self.strategy.equity_curve) == 0:
            raise ValueError("没有权益曲线数据，请先运行回测")

        # 准备数据
        df = self.data.copy()
        df['datetime'] = df.index.strftime('%Y-%m-%d %H:%M:%S')
        x_data = df['datetime'].tolist()
        ohlc_data = df[['Open', 'Close', 'Low', 'High']].values.tolist()
        volume_data = df['Volume'].values.tolist()
        eq = pd.Series(self.strategy.equity_curve, index=self.data.index[:len(self.strategy.equity_curve)])

        # 1) 资金曲线图
        equity_line = (
            Line()
            .add_xaxis(x_data)
            .add_yaxis(
                "资金曲线",
                eq.round(2).tolist(),
                is_smooth=True,
                linestyle_opts=opts.LineStyleOpts(width=2),
                label_opts=opts.LabelOpts(is_show=False),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="资金曲线", pos_left="5%", pos_top="1%", title_textstyle_opts=opts.TextStyleOpts(color="#000", font_size=12)),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    is_scale=True,
                    axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                    splitline_opts=opts.SplitLineOpts(is_show=False),
                    axislabel_opts=opts.LabelOpts(is_show=False),
                ),
                yaxis_opts=opts.AxisOpts(
                    is_scale=True,
                    splitline_opts=opts.SplitLineOpts(is_show=True, linestyle_opts=opts.LineStyleOpts(opacity=0.3)),
                ),
                datazoom_opts=[
                    opts.DataZoomOpts(
                        type_="inside",
                        xaxis_index=[0, 1, 2],
                        range_start=0,
                        range_end=100,
                    ),
                    opts.DataZoomOpts(
                        type_="slider",
                        xaxis_index=[0, 1, 2],
                        pos_bottom="0%",
                        range_start=0,
                        range_end=100,
                    ),
                ],
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="cross",
                    background_color="rgba(245, 245, 245, 0.8)",
                    border_width=1,
                    border_color="#ccc",
                    textstyle_opts=opts.TextStyleOpts(color="#000"),
                ),
                axispointer_opts=opts.AxisPointerOpts(
                    is_show=True,
                    link=[{"xAxisIndex": "all"}],
                    label=opts.LabelOpts(background_color="#777"),
                ),
            )
        )

        # 添加资金曲线的标记点
        equity_mark_points = []
        if len(eq) > 1:
            start_equity = eq.iloc[0]
            # Max Drawdown
            rolling_max = eq.cummax()
            drawdown = (eq / rolling_max - 1)
            max_dd_idx = drawdown.idxmin()
            max_dd_val = drawdown.min()
            max_dd_time = max_dd_idx.strftime('%Y-%m-%d %H:%M:%S')
            max_dd_equity = eq.loc[max_dd_idx]
            equity_mark_points.append(
                opts.MarkPointItem(
                    coord=[max_dd_time, max_dd_equity],
                    value=f"最大回撤: {max_dd_val:.2%}",
                    itemstyle_opts=opts.ItemStyleOpts(color="red"),
                    symbol_size=16
                )
            )
            # Peak value
            peak_val = eq.max()
            peak_percentage = (peak_val / start_equity) * 100  # 转换为以初始资金为100%的百分比
            peak_idx = eq.idxmax()
            peak_time = peak_idx.strftime('%Y-%m-%d %H:%M:%S')
            equity_mark_points.append(
                opts.MarkPointItem(
                    coord=[peak_time, peak_val],
                    value=f"峰值: {peak_percentage:.1f}%",
                    itemstyle_opts=opts.ItemStyleOpts(color="cyan"),
                    symbol_size=16
                )
            )
            # Final value
            final_val = eq.iloc[-1]
            final_percentage = (final_val / start_equity) * 100  # 转换为以初始资金为100%的百分比
            final_idx = eq.index[-1]
            final_time = final_idx.strftime('%Y-%m-%d %H:%M:%S')
            equity_mark_points.append(
                opts.MarkPointItem(
                    coord=[final_time, final_val],
                    value=f"最终: {final_percentage:.1f}%",
                    itemstyle_opts=opts.ItemStyleOpts(color="blue"),
                    symbol_size=16
                )
            )
        if equity_mark_points:
            equity_line.set_series_opts(
                markpoint_opts=opts.MarkPointOpts(data=equity_mark_points, label_opts=opts.LabelOpts(font_size=10))
            )

        # 2) K线图
        kline = (
            Kline()
            .add_xaxis(x_data)
            .add_yaxis(
                "K线",
                ohlc_data,
                itemstyle_opts=opts.ItemStyleOpts(
                    color="#ec0000",
                    color0="#00da3c",
                    border_color="#ec0000",
                    border_color0="#00da3c",
                ),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="价格走势", pos_left="5%", pos_top="21%", title_textstyle_opts=opts.TextStyleOpts(color="#000", font_size=12)),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    is_scale=True,
                    axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                    splitline_opts=opts.SplitLineOpts(is_show=False),
                    axislabel_opts=opts.LabelOpts(is_show=False),
                ),
                yaxis_opts=opts.AxisOpts(
                    is_scale=True,
                    splitarea_opts=opts.SplitAreaOpts(
                        is_show=True, 
                        areastyle_opts=opts.AreaStyleOpts(opacity=0.1)
                    ),
                    splitline_opts=opts.SplitLineOpts(is_show=True, linestyle_opts=opts.LineStyleOpts(opacity=0.3)),
                ),
                legend_opts=opts.LegendOpts(is_show=False),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="cross",
                    background_color="rgba(245, 245, 245, 0.8)",
                    border_width=1,
                    border_color="#ccc",
                    textstyle_opts=opts.TextStyleOpts(color="#000"),
                    formatter="""
                    function (params) {
                        var res = params[0].name + '<br/>';
                        res += '开盘: ' + params[0].data[1] + '<br/>';
                        res += '收盘: ' + params[0].data[2] + '<br/>';
                        res += '最低: ' + params[0].data[3] + '<br/>';
                        res += '最高: ' + params[0].data[4] + '<br/>';
                        return res;
                    }
                    """
                ),
                axispointer_opts=opts.AxisPointerOpts(
                    is_show=True,
                    link=[{"xAxisIndex": "all"}],
                    label=opts.LabelOpts(background_color="#777"),
                ),
            )
        )

        # 添加买卖点标记
        if hasattr(self.strategy, 'trades') and len(self.strategy.trades) > 0:
            trades_df = pd.DataFrame(self.strategy.trades)
            if not trades_df.empty:
                mark_points = []
                for _, trade in trades_df.iterrows():
                    trade_time = self.data.index[trade['i']].strftime('%Y-%m-%d %H:%M:%S')
                    if trade['side'] == 'buy':
                        mark_points.append(
                            opts.MarkPointItem(
                                coord=[trade_time, trade['price']],
                                value="B",
                                itemstyle_opts=opts.ItemStyleOpts(color="green"),
                                symbol='triangle',
                                symbol_size=12,
                            )
                        )
                    else:
                        mark_points.append(
                            opts.MarkPointItem(
                                coord=[trade_time, trade['price']],
                                value="S",
                                itemstyle_opts=opts.ItemStyleOpts(color="red"),
                                symbol='pin',
                                symbol_size=12,
                            )
                        )
                
                if mark_points:
                    kline.set_series_opts(
                        markpoint_opts=opts.MarkPointOpts(
                            data=mark_points,
                            label_opts=opts.LabelOpts(position="top")
                        )
                    )

        # 3) 成交量图
        # 准备成交量数据，为每个柱子设置颜色
        volume_data_with_style = []
        for i, volume in enumerate(volume_data):
            open_price, close_price = ohlc_data[i][0], ohlc_data[i][1]
            if close_price > open_price:  # 涨
                color = '#ec0000'  # 红色，与K线图一致
            else:  # 跌
                color = '#00da3c'  # 绿色，与K线图一致
            
            volume_data_with_style.append(
                opts.BarItem(
                    name=x_data[i],
                    value=volume,
                    itemstyle_opts=opts.ItemStyleOpts(color=color)
                )
            )
        
        bar = (
            Bar()
            .add_xaxis(x_data)
            .add_yaxis(
                "成交量",
                volume_data_with_style,
                xaxis_index=1,
                yaxis_index=1,
                label_opts=opts.LabelOpts(is_show=False),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(title="成交量", pos_left="5%", pos_top="81%", title_textstyle_opts=opts.TextStyleOpts(color="#000", font_size=12)),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    grid_index=1,
                    axislabel_opts=opts.LabelOpts(is_show=False),
                    axistick_opts=opts.AxisTickOpts(is_show=False),
                ),
                yaxis_opts=opts.AxisOpts(
                    grid_index=1,
                    split_number=3,
                    axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                    axistick_opts=opts.AxisTickOpts(is_show=False),
                    splitline_opts=opts.SplitLineOpts(is_show=True, linestyle_opts=opts.LineStyleOpts(opacity=0.3)),
                    axislabel_opts=opts.LabelOpts(is_show=True),
                    position="left",
                ),
                legend_opts=opts.LegendOpts(is_show=False),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="cross",
                    background_color="rgba(245, 245, 245, 0.8)",
                    border_width=1,
                    border_color="#ccc",
                    textstyle_opts=opts.TextStyleOpts(color="#000"),
                ),
                axispointer_opts=opts.AxisPointerOpts(
                    is_show=True,
                    link=[{"xAxisIndex": "all"}],
                    label=opts.LabelOpts(background_color="#777"),
                ),
            )
        )
        
        # 布局
        grid_chart = Grid(init_opts=opts.InitOpts(width="100%",height='800px', theme=ThemeType.LIGHT))
        
        grid_chart.add(
            equity_line,
            grid_opts=opts.GridOpts(pos_left="5%", pos_right="5%", height="10%",pos_top="5%"),
        )
        grid_chart.add(
            kline,
            grid_opts=opts.GridOpts(pos_left="5%", pos_right="5%", height="50%",pos_top="20%"),
        )
        grid_chart.add(
            bar,
            grid_opts=opts.GridOpts(pos_left="5%", pos_right="5%",height="15%",pos_top="80%"),
        )

        if filename is None:
            filename = "backtest_result.html"
        
        grid_chart.render(filename)

        if show_in_browser:
            webbrowser.open("file://" + os.path.realpath(filename))
            
        return filename
