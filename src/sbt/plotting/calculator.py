"""
技术指标计算模块
"""

import pandas as pd
from typing import Dict, Tuple
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


class IndicatorCalculator:
    """技术指标计算器"""
    
    @staticmethod
    def ma(data: pd.Series, period: int) -> pd.Series:
        """简单移动平均线"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """指数移动平均线"""
        if HAS_TALIB:
            return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)
        else:
            return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """简单移动平均线（与ma相同）"""
        return IndicatorCalculator.ma(data, period)
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD指标"""
        if HAS_TALIB:
            macd_line, signal_line, hist = talib.MACD(data.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
            return (
                pd.Series(macd_line, index=data.index),
                pd.Series(signal_line, index=data.index),
                pd.Series(hist, index=data.index)
            )
        else:
            # 手动计算
            ema_fast = data.ewm(span=fast).mean()
            ema_slow = data.ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            hist = macd_line - signal_line
            return macd_line, signal_line, hist
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """RSI指标"""
        if HAS_TALIB:
            return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
        else:
            # 手动计算
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """布林带"""
        if HAS_TALIB:
            upper, middle, lower = talib.BBANDS(data.values, timeperiod=period, nbdevup=std, nbdevdn=std, matype=0)
            return (
                pd.Series(upper, index=data.index),
                pd.Series(middle, index=data.index),
                pd.Series(lower, index=data.index)
            )
        else:
            # 手动计算
            middle = data.rolling(window=period).mean()
            std_dev = data.rolling(window=period).std()
            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)
            return upper, middle, lower
    
    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """KDJ指标"""
        if HAS_TALIB:
            # 使用STOCH计算K和D
            k_percent, d_percent = talib.STOCH(high.values, low.values, close.values, 
                                               fastk_period=n, slowk_period=m1, slowd_period=m2)
            k = pd.Series(k_percent, index=close.index)
            d = pd.Series(d_percent, index=close.index)
            j = 3 * k - 2 * d
            return k, d, j
        else:
            # 手动计算
            lowest_low = low.rolling(window=n).min()
            highest_high = high.rolling(window=n).max()
            
            rsv = 100 * (close - lowest_low) / (highest_high - lowest_low)
            k = rsv.ewm(alpha=1/m1, adjust=False).mean()
            d = k.ewm(alpha=1/m2, adjust=False).mean()
            j = 3 * k - 2 * d
            
            return k, d, j
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """随机指标"""
        if HAS_TALIB:
            k_percent, d_percent = talib.STOCH(high.values, low.values, close.values,
                                               fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
            return (
                pd.Series(k_percent, index=close.index),
                pd.Series(d_percent, index=close.index)
            )
        else:
            # 手动计算
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
            d_percent = k_percent.rolling(window=d_period).mean()
            return k_percent, d_percent
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """平均真实波幅"""
        if HAS_TALIB:
            return pd.Series(talib.ATR(high.values, low.values, close.values, timeperiod=period), index=close.index)
        else:
            # 手动计算
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.rolling(window=period).mean()
    
    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """威廉指标"""
        if HAS_TALIB:
            return pd.Series(talib.WILLR(high.values, low.values, close.values, timeperiod=period), index=close.index)
        else:
            # 手动计算
            highest_high = high.rolling(window=period).max()
            lowest_low = low.rolling(window=period).min()
            wr = -100 * (highest_high - close) / (highest_high - lowest_low)
            return wr


def calculate_indicator(data: pd.DataFrame, indicator_name: str, params: Dict) -> Dict:
    """
    计算技术指标
    
    Args:
        data: OHLCV数据
        indicator_name: 指标名称
        params: 指标参数
    
    Returns:
        计算结果字典
    """
    calc = IndicatorCalculator()
    
    if indicator_name.upper().startswith('MA'):
        period = params.get('period', 20)
        result = calc.ma(data['Close'], period)
        return {indicator_name: result}
    
    elif indicator_name.upper().startswith('EMA'):
        period = params.get('period', 12)
        result = calc.ema(data['Close'], period)
        return {indicator_name: result}
    
    elif indicator_name.upper() == 'MACD':
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal = params.get('signal', 9)
        macd_line, signal_line, hist = calc.macd(data['Close'], fast, slow, signal)
        return {
            'MACD': macd_line,
            'MACD_signal': signal_line,
            'MACD_hist': hist
        }
    
    elif indicator_name.upper() == 'RSI':
        period = params.get('period', 14)
        result = calc.rsi(data['Close'], period)
        return {'RSI': result}
    
    elif indicator_name.upper() == 'BOLL':
        period = params.get('period', 20)
        std = params.get('std', 2)
        upper, middle, lower = calc.bollinger_bands(data['Close'], period, std)
        return {
            'BOLL_upper': upper,
            'BOLL_middle': middle,
            'BOLL_lower': lower
        }
    
    elif indicator_name.upper() == 'KDJ':
        n = params.get('n', 9)
        m1 = params.get('m1', 3)
        m2 = params.get('m2', 3)
        k, d, j = calc.kdj(data['High'], data['Low'], data['Close'], n, m1, m2)
        return {
            'KDJ_K': k,
            'KDJ_D': d,
            'KDJ_J': j
        }
    
    elif indicator_name.upper() == 'STOCH':
        k_period = params.get('k_period', 14)
        d_period = params.get('d_period', 3)
        k, d = calc.stochastic(data['High'], data['Low'], data['Close'], k_period, d_period)
        return {
            'STOCH_K': k,
            'STOCH_D': d
        }
    
    elif indicator_name.upper() == 'ATR':
        period = params.get('period', 14)
        result = calc.atr(data['High'], data['Low'], data['Close'], period)
        return {'ATR': result}
    
    elif indicator_name.upper() == 'WILLR':
        period = params.get('period', 14)
        result = calc.williams_r(data['High'], data['Low'], data['Close'], period)
        return {'WILLR': result}
    
    else:
        raise ValueError(f"未支持的指标: {indicator_name}")
