from __future__ import annotations
from typing import Type, Dict, Any
import pandas as pd
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

    def plot(self, filename: str = None, show_in_browser: bool = False, use_new_plotter: bool = True) -> str:
        """
        绘制回测结果
        
        Args:
            filename: 输出文件名
            show_in_browser: 是否在浏览器中显示
            use_new_plotter: 是否使用新的绘图模块（默认True）
            
        Returns:
            生成的HTML文件路径
        """
        if len(self.strategy.equity_curve) == 0:
            raise ValueError("没有权益曲线数据，请先运行回测")
        
        if use_new_plotter:
            return self._plot_with_new_plotter(filename, show_in_browser)
        else:
            return self._plot_legacy(filename, show_in_browser)
    
    def _plot_with_new_plotter(self, filename: str = None, show_in_browser: bool = False) -> str:
        """使用新的绘图模块绘图"""
        from ..plotting import AutoPlotter
        
        # 创建绘图器
        plotter = AutoPlotter(theme=self.strategy.plot_theme)
        
        # 添加策略配置的指标
        for indicator_config in self.strategy.plot_indicators:
            if indicator_config.get('enabled', True):
                try:
                    plotter.add_indicator(
                        data=self.data,
                        indicator_name=indicator_config['name'],
                        **indicator_config.get('params', {})
                    )
                except Exception as e:
                    print(f"添加指标 {indicator_config['name']} 失败: {e}")
        
        # 绘制图表
        return plotter.plot(
            data=self.data,
            trades=self.strategy.trades,
            equity_curve=self.strategy.equity_curve,
            filename=filename,
            show_in_browser=show_in_browser,
            title="回测结果"
        )
    
    def _plot_legacy(self, filename: str = None, show_in_browser: bool = False) -> str:
        """使用原有绘图代码（保持向后兼容）"""
        # 这里保留原有的复杂绘图逻辑作为后备
        # 为了简化，这里只提供基本功能
        
        if filename is None:
            filename = "backtest_result_legacy.html"
        
        # 创建一个简单的HTML页面显示结果
        metrics = self.strategy.metrics()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>回测结果</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>回测结果</h1>
            <h2>策略指标</h2>
            <ul>
                <li>总收益率: {metrics['Return [%]']:.2f}%</li>
                <li>年化收益率: {metrics['Return (Ann.) [%]']:.2f}%</li>
                <li>最大回撤: {metrics['Max. Drawdown [%]']:.2f}%</li>
                <li>夏普比率: {metrics['Sharpe Ratio']:.4f}</li>
                <li>交易次数: {metrics['# Trades']}</li>
            </ul>
            <p>请使用新的绘图模块 (use_new_plotter=True) 获得完整的图表功能。</p>
        </body>
        </html>
        """
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if show_in_browser:
            webbrowser.open("file://" + os.path.realpath(filename))
        
        return filename
