"""
自动绘图器模块

参考autotrader的autoplot设计，提供独立的回测结果绘图功能
"""

import pandas as pd
import webbrowser
import os
from typing import Dict, List, Optional, Union
from pyecharts import options as opts
from pyecharts.charts import Kline, Line, Bar, Grid
from pyecharts.globals import ThemeType

from .themes import PlotTheme, get_theme
from .indicators import IndicatorConfig, PlotIndicator, IndicatorType, PlotType
from .calculator import calculate_indicator


class AutoPlotter:
    """自动绘图器
    
    提供回测结果的可视化功能，支持：
    - 价格图表（K线图）
    - 技术指标图表
    - 交易信号标记
    - 权益曲线
    - 成交量图表
    """
    
    def __init__(self, theme: Union[str, PlotTheme] = 'light'):
        """
        初始化绘图器
        
        Args:
            theme: 主题名称或主题对象
        """
        if isinstance(theme, str):
            self.theme = get_theme(theme)
        else:
            self.theme = theme
        
        self.indicators: List[PlotIndicator] = []
        self.subplots_count = 0
    
    def add_indicator(self, 
                     data: pd.DataFrame,
                     indicator_name: str, 
                     config: Optional[IndicatorConfig] = None,
                     **params) -> 'AutoPlotter':
        """
        添加技术指标
        
        Args:
            data: OHLCV数据
            indicator_name: 指标名称
            config: 指标配置（可选）
            **params: 指标参数
            
        Returns:
            self: 支持链式调用
        """
        if config is None:
            from .indicators import get_indicator_config
            config = get_indicator_config(indicator_name)
            if config is None:
                raise ValueError(f"未找到指标配置: {indicator_name}")
        
        # 合并参数
        if params:
            config.params.update(params)
        
        # 计算指标数据
        try:
            indicator_data = calculate_indicator(data, indicator_name, config.params)
        except Exception as e:
            print(f"计算指标 {indicator_name} 失败: {e}")
            return self
        
        # 准备时间序列
        x_data = data.index.strftime('%Y-%m-%d %H:%M:%S').tolist()
        
        # 创建绘图指标对象
        plot_indicator = PlotIndicator(
            name=indicator_name,
            data=indicator_data,
            config=config,
            x_data=x_data
        )
        
        self.indicators.append(plot_indicator)
        
        # 如果是子图指标，增加子图计数
        if config.indicator_type == IndicatorType.SUBPLOT:
            self.subplots_count += 1
        
        return self
    
    def add_custom_indicator(self,
                           name: str,
                           data: Union[pd.Series, Dict[str, pd.Series]], 
                           x_data: List[str],
                           config: IndicatorConfig) -> 'AutoPlotter':
        """
        添加自定义指标
        
        Args:
            name: 指标名称
            data: 指标数据
            x_data: X轴数据
            config: 指标配置
            
        Returns:
            self: 支持链式调用
        """
        # 转换数据格式
        if isinstance(data, pd.Series):
            indicator_data = {name: data}
        else:
            indicator_data = data
        
        plot_indicator = PlotIndicator(
            name=name,
            data=indicator_data,
            config=config,
            x_data=x_data
        )
        
        self.indicators.append(plot_indicator)
        
        if config.indicator_type == IndicatorType.SUBPLOT:
            self.subplots_count += 1
            
        return self
    
    def plot(self, 
             data: pd.DataFrame,
             trades: List[Dict] = None,
             equity_curve: List[float] = None,
             filename: str = None,
             show_in_browser: bool = False,
             title: str = "回测结果") -> str:
        """
        绘制完整的回测图表
        
        Args:
            data: OHLCV数据
            trades: 交易记录
            equity_curve: 权益曲线
            filename: 输出文件名
            show_in_browser: 是否在浏览器中显示
            title: 图表标题
            
        Returns:
            生成的HTML文件路径
        """
        if len(data) == 0:
            raise ValueError("数据为空")
        
        # 准备基础数据
        df = data.copy()
        df['datetime'] = df.index.strftime('%Y-%m-%d %H:%M:%S')
        x_data = df['datetime'].tolist()
        ohlc_data = df[['Open', 'Close', 'Low', 'High']].values.tolist()
        volume_data = df['Volume'].values.tolist()
        
        # 创建图表组件
        charts = []
        grid_opts = []
        
        # 1. 权益曲线图（如果有）
        if equity_curve and len(equity_curve) > 0:
            equity_chart = self._create_equity_chart(x_data, equity_curve)
            charts.append(equity_chart)
            grid_opts.append(opts.GridOpts(pos_left="5%", pos_right="5%", height="10%", pos_top="5%"))
        
        # 2. 主图（K线图 + 叠加指标）
        main_chart = self._create_main_chart(x_data, ohlc_data, data, trades)
        charts.append(main_chart)
        
        # 计算主图位置
        equity_height = 15 if equity_curve else 0
        volume_height = 20
        subplot_total_height = self.subplots_count * 15
        main_height = 100 - equity_height - volume_height - subplot_total_height
        main_top = equity_height
        
        grid_opts.append(opts.GridOpts(
            pos_left="5%", 
            pos_right="5%", 
            height=f"{main_height}%", 
            pos_top=f"{main_top}%"
        ))
        
        # 3. 子图指标
        current_top = main_top + main_height
        subplot_charts = self._create_subplot_charts(x_data, data)
        for subplot_chart in subplot_charts:
            charts.append(subplot_chart)
            grid_opts.append(opts.GridOpts(
                pos_left="5%", 
                pos_right="5%", 
                height="15%", 
                pos_top=f"{current_top}%"
            ))
            current_top += 15
        
        # 4. 成交量图
        volume_chart = self._create_volume_chart(x_data, volume_data, ohlc_data)
        charts.append(volume_chart)
        grid_opts.append(opts.GridOpts(
            pos_left="5%", 
            pos_right="5%", 
            height="15%", 
            pos_top=f"{current_top}%"
        ))
        
        # 创建网格布局
        grid_chart = Grid(init_opts=opts.InitOpts(
            width=self.theme.width,
            height=self.theme.height,
            theme=ThemeType.LIGHT if self.theme.theme == 'light' else ThemeType.DARK
        ))
        
        # 添加所有图表到网格
        for chart, grid_opt in zip(charts, grid_opts):
            grid_chart.add(chart, grid_opts=grid_opt)
        
        # 渲染并保存
        if filename is None:
            filename = f"{title}_backtest_result.html"
        
        grid_chart.render(filename)
        
        if show_in_browser:
            webbrowser.open("file://" + os.path.realpath(filename))
        
        return filename
    
    def _create_equity_chart(self, x_data: List[str], equity_curve: List[float]) -> Line:
        """创建权益曲线图"""
        eq = pd.Series(equity_curve)
        
        equity_line = (
            Line()
            .add_xaxis(x_data[:len(equity_curve)])
            .add_yaxis(
                "资金曲线",
                eq.round(2).tolist(),
                is_smooth=True,
                linestyle_opts=opts.LineStyleOpts(width=2, color="#FF6B6B"),
                label_opts=opts.LabelOpts(is_show=False),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="资金曲线", 
                    pos_left="5%", 
                    pos_top="1%", 
                    title_textstyle_opts=opts.TextStyleOpts(color=self.theme.text_color, font_size=12)
                ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    is_scale=True,
                    axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                    splitline_opts=opts.SplitLineOpts(is_show=False),
                    axislabel_opts=opts.LabelOpts(is_show=False),
                ),
                yaxis_opts=opts.AxisOpts(
                    is_scale=True,
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True, 
                        linestyle_opts=opts.LineStyleOpts(opacity=0.3, color=self.theme.grid_color)
                    ),
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
            )
        )
        
        # 添加权益曲线标记点
        self._add_equity_markpoints(equity_line, eq, x_data[:len(equity_curve)])
        
        return equity_line
    
    def _add_equity_markpoints(self, chart: Line, equity: pd.Series, x_data: List[str]):
        """添加权益曲线标记点"""
        if len(equity) <= 1:
            return
        
        mark_points = []
        start_equity = equity.iloc[0]
        
        # 最大回撤点
        rolling_max = equity.cummax()
        drawdown = (equity / rolling_max - 1)
        max_dd_idx = drawdown.idxmin()
        max_dd_val = drawdown.min()
        max_dd_time = x_data[max_dd_idx]
        max_dd_equity = equity.iloc[max_dd_idx]
        
        mark_points.append(
            opts.MarkPointItem(
                coord=[max_dd_time, max_dd_equity],
                value=f"最大回撤: {max_dd_val:.2%}",
                itemstyle_opts=opts.ItemStyleOpts(color="red"),
                symbol_size=16
            )
        )
        
        # 峰值点
        peak_val = equity.max()
        peak_percentage = (peak_val / start_equity) * 100
        peak_idx = equity.idxmax()
        peak_time = x_data[peak_idx]
        
        mark_points.append(
            opts.MarkPointItem(
                coord=[peak_time, peak_val],
                value=f"峰值: {peak_percentage:.1f}%",
                itemstyle_opts=opts.ItemStyleOpts(color="cyan"),
                symbol_size=16
            )
        )
        
        # 最终值点
        final_val = equity.iloc[-1]
        final_percentage = (final_val / start_equity) * 100
        final_time = x_data[-1]
        
        mark_points.append(
            opts.MarkPointItem(
                coord=[final_time, final_val],
                value=f"最终: {final_percentage:.1f}%",
                itemstyle_opts=opts.ItemStyleOpts(color="blue"),
                symbol_size=16
            )
        )
        
        chart.set_series_opts(
            markpoint_opts=opts.MarkPointOpts(
                data=mark_points,
                label_opts=opts.LabelOpts(font_size=10)
            )
        )
    
    def _create_main_chart(self, x_data: List[str], ohlc_data: List, data: pd.DataFrame, trades: List[Dict] = None) -> Kline:
        """创建主图（K线图 + 叠加指标）"""
        kline = (
            Kline()
            .add_xaxis(x_data)
            .add_yaxis(
                "K线",
                ohlc_data,
                itemstyle_opts=opts.ItemStyleOpts(
                    color=self.theme.up_color,
                    color0=self.theme.down_color,
                    border_color=self.theme.up_color,
                    border_color0=self.theme.down_color,
                ),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="价格走势", 
                    pos_left="5%", 
                    title_textstyle_opts=opts.TextStyleOpts(color=self.theme.text_color, font_size=12)
                ),
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
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True, 
                        linestyle_opts=opts.LineStyleOpts(opacity=0.3, color=self.theme.grid_color)
                    ),
                ),
                legend_opts=opts.LegendOpts(is_show=True, pos_top="0%"),
                tooltip_opts=opts.TooltipOpts(
                    trigger="axis",
                    axis_pointer_type="cross",
                    background_color="rgba(245, 245, 245, 0.8)",
                    border_width=1,
                    border_color="#ccc",
                    textstyle_opts=opts.TextStyleOpts(color="#000"),
                ),
            )
        )
        
        # 添加叠加指标
        self._add_overlay_indicators(kline, x_data, data)
        
        # 添加交易信号标记
        if trades:
            self._add_trade_markers(kline, trades, data, x_data)
        
        return kline
    
    def _add_overlay_indicators(self, chart: Kline, x_data: List[str], data: pd.DataFrame):
        """添加叠加指标到主图"""
        for indicator in self.indicators:
            if indicator.config.indicator_type == IndicatorType.OVERLAY:
                for name, series in indicator.data.items():
                    if isinstance(series, pd.Series):
                        color = indicator.config.style.get('color', self.theme.ma_colors.get(name, '#FF6B6B'))
                        width = indicator.config.style.get('width', 1)
                        
                        chart.extend_axis(
                            yaxis=opts.AxisOpts(
                                type_="value",
                                is_show=False,
                            )
                        )
                        
                        line = Line().add_xaxis(x_data).add_yaxis(
                            name,
                            series.round(4).tolist(),
                            is_smooth=True,
                            linestyle_opts=opts.LineStyleOpts(width=width, color=color),
                            label_opts=opts.LabelOpts(is_show=False),
                            yaxis_index=len(chart.options.get('yAxis', [])),
                        )
                        
                        chart.overlap(line)
    
    def _add_trade_markers(self, chart: Kline, trades: List[Dict], data: pd.DataFrame, x_data: List[str]):
        """添加交易标记"""
        if not trades:
            return
        
        trades_df = pd.DataFrame(trades)
        if trades_df.empty:
            return
        
        mark_points = []
        for _, trade in trades_df.iterrows():
            if trade['i'] < len(x_data):
                trade_time = x_data[trade['i']]
                if trade['side'] == 'buy':
                    mark_points.append(
                        opts.MarkPointItem(
                            coord=[trade_time, trade['price']],
                            value="B",
                            itemstyle_opts=opts.ItemStyleOpts(color=self.theme.buy_color),
                            symbol=self.theme.buy_symbol,
                            symbol_size=12,
                        )
                    )
                else:
                    mark_points.append(
                        opts.MarkPointItem(
                            coord=[trade_time, trade['price']],
                            value="S",
                            itemstyle_opts=opts.ItemStyleOpts(color=self.theme.sell_color),
                            symbol=self.theme.sell_symbol,
                            symbol_size=12,
                        )
                    )
        
        if mark_points:
            chart.set_series_opts(
                markpoint_opts=opts.MarkPointOpts(
                    data=mark_points,
                    label_opts=opts.LabelOpts(position="top")
                )
            )
    
    def _create_subplot_charts(self, x_data: List[str], data: pd.DataFrame) -> List[Union[Line, Bar]]:
        """创建子图指标"""
        charts = []
        
        for indicator in self.indicators:
            if indicator.config.indicator_type == IndicatorType.SUBPLOT:
                if indicator.config.plot_type == PlotType.LINE:
                    chart = self._create_line_subplot(indicator, x_data)
                elif indicator.config.plot_type == PlotType.BAR:
                    chart = self._create_bar_subplot(indicator, x_data)
                else:
                    continue
                
                charts.append(chart)
        
        return charts
    
    def _create_line_subplot(self, indicator: PlotIndicator, x_data: List[str]) -> Line:
        """创建线形子图"""
        chart = Line()
        chart.add_xaxis(x_data)
        
        for name, series in indicator.data.items():
            if isinstance(series, pd.Series):
                color = indicator.config.style.get(f'{name.lower()}_color', 
                                                  self.theme.indicator_colors.get(name, '#FF6B6B'))
                width = indicator.config.style.get('width', 1)
                
                chart.add_yaxis(
                    name,
                    series.round(4).tolist(),
                    is_smooth=True,
                    linestyle_opts=opts.LineStyleOpts(width=width, color=color),
                    label_opts=opts.LabelOpts(is_show=False),
                )
        
        chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title=indicator.name,
                pos_left="5%",
                title_textstyle_opts=opts.TextStyleOpts(color=self.theme.text_color, font_size=12)
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                axislabel_opts=opts.LabelOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                splitline_opts=opts.SplitLineOpts(
                    is_show=True, 
                    linestyle_opts=opts.LineStyleOpts(opacity=0.3, color=self.theme.grid_color)
                ),
            ),
            legend_opts=opts.LegendOpts(is_show=True, pos_top="0%"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        )
        
        return chart
    
    def _create_bar_subplot(self, indicator: PlotIndicator, x_data: List[str]) -> Bar:
        """创建柱状子图"""
        chart = Bar()
        chart.add_xaxis(x_data)
        
        for name, series in indicator.data.items():
            if isinstance(series, pd.Series):
                color = indicator.config.style.get(f'{name.lower()}_color',
                                                  self.theme.indicator_colors.get(name, '#FF6B6B'))
                
                chart.add_yaxis(
                    name,
                    series.round(4).tolist(),
                    itemstyle_opts=opts.ItemStyleOpts(color=color),
                    label_opts=opts.LabelOpts(is_show=False),
                )
        
        chart.set_global_opts(
            title_opts=opts.TitleOpts(
                title=indicator.name,
                pos_left="5%",
                title_textstyle_opts=opts.TextStyleOpts(color=self.theme.text_color, font_size=12)
            ),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                axislabel_opts=opts.LabelOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                splitline_opts=opts.SplitLineOpts(
                    is_show=True,
                    linestyle_opts=opts.LineStyleOpts(opacity=0.3, color=self.theme.grid_color)
                ),
            ),
            legend_opts=opts.LegendOpts(is_show=True, pos_top="0%"),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        )
        
        return chart
    
    def _create_volume_chart(self, x_data: List[str], volume_data: List, ohlc_data: List) -> Bar:
        """创建成交量图"""
        # 准备成交量数据，为每个柱子设置颜色
        volume_data_with_style = []
        for i, volume in enumerate(volume_data):
            open_price, close_price = ohlc_data[i][0], ohlc_data[i][1]
            color = self.theme.up_color if close_price > open_price else self.theme.down_color
            
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
                label_opts=opts.LabelOpts(is_show=False),
            )
            .set_global_opts(
                title_opts=opts.TitleOpts(
                    title="成交量",
                    pos_left="5%",
                    title_textstyle_opts=opts.TextStyleOpts(color=self.theme.text_color, font_size=12)
                ),
                xaxis_opts=opts.AxisOpts(
                    type_="category",
                    axislabel_opts=opts.LabelOpts(is_show=True),
                    axistick_opts=opts.AxisTickOpts(is_show=False),
                ),
                yaxis_opts=opts.AxisOpts(
                    split_number=3,
                    axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                    axistick_opts=opts.AxisTickOpts(is_show=False),
                    splitline_opts=opts.SplitLineOpts(
                        is_show=True,
                        linestyle_opts=opts.LineStyleOpts(opacity=0.3, color=self.theme.grid_color)
                    ),
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
            )
        )
        
        return bar
    
    def clear_indicators(self) -> 'AutoPlotter':
        """清除所有指标"""
        self.indicators.clear()
        self.subplots_count = 0
        return self
