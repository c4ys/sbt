from backtesting import Strategy
from backtesting.lib import crossover
import talib


class SMACross(Strategy):
    """指数移动平均线交叉策略（EMA Crossover Strategy）
    
    当短期EMA上穿长期EMA时买入
    当短期EMA下穿长期EMA时卖出
    """
    
    # 策略参数
    n1 = 52  # 短期EMA周期
    n2 = 104  # 长期EMA周期
    
    def init(self):
        """初始化策略"""
        # 使用 TA-Lib 计算指数移动平均线
        self.ma1 = self.I(talib.EMA, self.data.Close, timeperiod=self.n1, name=f'EMA{self.n1}')
        self.ma2 = self.I(talib.EMA, self.data.Close, timeperiod=self.n2, name=f'EMA{self.n2}')
    
    def next(self):
        """策略逻辑"""
        # 如果短期均线上穿长期均线，买入
        if crossover(self.ma1, self.ma2):
            # 计算能买多少股（资金的30%）
            cash = self.equity  # 总资产
            price = self.data.Close[-1]
            max_shares = int((cash * 0.3) / price / 100) * 100  # 买整手
            if max_shares >= 100:  # 至少买1手
                self.buy(size=max_shares)
        
        # 如果短期均线下穿长期均线，卖出
        elif crossover(self.ma2, self.ma1):
            self.position.close()
