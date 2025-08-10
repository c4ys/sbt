from sbt.backtest import StrategyBase
import talib


class SMACross(StrategyBase):
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
        close = self.data['Close'].astype(float)
        try:
            self.ma1 = talib.EMA(close.values, timeperiod=self.n1)
            self.ma2 = talib.EMA(close.values, timeperiod=self.n2)
        except Exception:
            # 如果没有 TA-Lib，使用 pandas 的 ewm
            self.ma1 = close.ewm(span=self.n1, adjust=False).mean().values
            self.ma2 = close.ewm(span=self.n2, adjust=False).mean().values
    
    def next(self, i: int):
        """策略逻辑"""
        # 需要足够历史数据
        if i == 0 or i < max(self.n1, self.n2):
            return
        
        # 获取前一时刻和当前时刻的均线值
        a1_prev, a2_prev = self.ma1[i-1], self.ma2[i-1]
        a1_curr, a2_curr = self.ma1[i], self.ma2[i]
        
        # 检查是否有 NaN 值
        if any(map(lambda x: x != x, [a1_prev, a2_prev, a1_curr, a2_curr])):
            return

        price = float(self.data['Close'].iloc[i])
        lot = 100
        
        # 如果短期均线上穿长期均线，买入
        if a1_prev <= a2_prev and a1_curr > a2_curr:
            # 计算能买多少股（资金的30%）
            size = int((self.cash * 0.3) / price / lot) * lot
            if size >= 100:  # 至少买1手
                self.buy(i, size)
        
        # 如果短期均线下穿长期均线，平仓
        elif a1_prev >= a2_prev and a1_curr < a2_curr:
            self.close(i)
