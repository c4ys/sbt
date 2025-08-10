from __future__ import annotations
from typing import Any, Dict
import pandas as pd

class StrategyBase:
    """最小策略基类：
    - init(self): 初始化指标
    - next(self, i): 在索引 i 上执行交易逻辑
    提供 buy/sell/close 以及访问 data/position/cash/equity。
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
        self.init()

    # 用户可覆盖的方法
    def init(self):
        pass

    def next(self, i: int):
        pass

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
