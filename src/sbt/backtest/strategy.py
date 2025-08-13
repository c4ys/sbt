from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd


class StrategyBase:
    """最小策略基类：
    - init(self): 初始化指标
    - next(self, i): 在索引 i 上执行交易逻辑
    提供 buy/sell/close 以及访问 data/position/cash/equity。
    支持配置绘图指标。
    """

    def __init__(self, data: pd.DataFrame, cash: float = 10000.0, commission: float = 0.002):
        self.data = data
        self.cash = cash
        self.commission = commission
        self.position = 0  # 多头持仓股数
        self.avg_price = 0.0  # 持仓均价
        self.trades = []  # 交易记录
        self.equity_curve = []  # 权益曲线
        self.context: Dict[str, Any] = {}
        
        # 绘图配置
        self.plot_indicators: List[Dict[str, Any]] = []  # 绘图指标配置列表
        self.plot_theme: str = 'light'  # 绘图主题
        
        self.init()

    # 用户可覆盖的方法
    def init(self):
        pass

    def next(self, i: int):
        pass
    
    def configure_plot(self, theme: str = 'light'):
        """
        配置绘图主题
        
        Args:
            theme: 主题名称 ('light' 或 'dark')
        """
        self.plot_theme = theme
    
    def add_plot_indicator(self, 
                          indicator_name: str,
                          enabled: bool = True,
                          **params):
        """
        添加绘图指标配置
        
        Args:
            indicator_name: 指标名称 (如 'MA20', 'MACD', 'RSI' 等)
            enabled: 是否启用
            **params: 指标参数 (如 period=20, fast=12 等)
        
        Examples:
            >>> self.add_plot_indicator('MA20', period=20)
            >>> self.add_plot_indicator('MACD', fast=12, slow=26, signal=9)
            >>> self.add_plot_indicator('RSI', period=14)
            >>> self.add_plot_indicator('BOLL', period=20, std=2)
        """
        indicator_config = {
            'name': indicator_name,
            'enabled': enabled,
            'params': params
        }
        
        # 避免重复添加相同指标
        existing = next((ind for ind in self.plot_indicators if ind['name'] == indicator_name), None)
        if existing:
            existing.update(indicator_config)
        else:
            self.plot_indicators.append(indicator_config)
    
    def remove_plot_indicator(self, indicator_name: str):
        """
        移除绘图指标
        
        Args:
            indicator_name: 指标名称
        """
        self.plot_indicators = [ind for ind in self.plot_indicators if ind['name'] != indicator_name]
    
    def enable_plot_indicator(self, indicator_name: str, enabled: bool = True):
        """
        启用/禁用绘图指标
        
        Args:
            indicator_name: 指标名称
            enabled: 是否启用
        """
        for indicator in self.plot_indicators:
            if indicator['name'] == indicator_name:
                indicator['enabled'] = enabled
                break

    # 交易动作
    def buy(self, i: int, size: int):
        price = float(self.data['Close'].iloc[i])
        if size <= 0:
            return
        cost = price * size * (1 + self.commission)
        if self.cash >= cost:
            # 更新均价
            total_cost = self.avg_price * self.position + price * size
            self.position += size
            self.avg_price = total_cost / self.position if self.position > 0 else 0.0
            self.cash -= cost
            self.trades.append({
                'i': i, 'side': 'buy', 'price': price, 'size': size, 'cash': self.cash,
            })

    def sell(self, i: int, size: int):
        price = float(self.data['Close'].iloc[i])
        if size <= 0:
            return
        if self.position >= size:
            proceeds = price * size * (1 - self.commission)
            self.position -= size
            # 若清仓则清零均价
            if self.position == 0:
                self.avg_price = 0.0
            self.cash += proceeds
            self.trades.append({
                'i': i, 'side': 'sell', 'price': price, 'size': size, 'cash': self.cash,
            })

    def close(self, i: int):
        if self.position > 0:
            self.sell(i, self.position)

    # 引擎调用
    def step(self, i: int):
        if i < len(self.data):
            self.next(i)
            equity = self.cash + self.position * float(self.data['Close'].iloc[i])
            self.equity_curve.append(equity)

    def metrics(self) -> Dict[str, Any]:
        eq = pd.Series(self.equity_curve, index=self.data.index[:len(self.equity_curve)])
        ret = eq.pct_change().fillna(0)
        total_return = (eq.iloc[-1] / eq.iloc[0] - 1) * 100 if len(eq) > 1 else 0.0
        max_dd = 0.0
        if len(eq) > 0:
            roll_max = eq.cummax()
            drawdown = (eq / roll_max - 1) * 100
            max_dd = float(drawdown.min())
        ann_factor = 252  # 简化：按交易日计
        ann_return = ((1 + ret.mean()) ** ann_factor - 1) * 100 if len(ret) > 0 else 0.0
        sharpe = (ret.mean() / (ret.std() + 1e-9)) * (ann_factor ** 0.5) if len(ret) > 1 else 0.0
        return {
            'Return [%]': float(total_return),
            'Return (Ann.) [%]': float(ann_return),
            'Max. Drawdown [%]': float(max_dd),
            'Sharpe Ratio': float(sharpe),
            '# Trades': int(len(self.trades)),
        }
