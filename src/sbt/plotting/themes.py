"""
绘图主题配置模块
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class PlotTheme:
    """绘图主题配置"""
    
    # 基础设置
    theme: str = 'light'  # light, dark
    width: str = '100%'
    height: str = '800px'
    
    # 颜色配置
    up_color: str = '#ec0000'      # 上涨颜色 (红)
    down_color: str = '#00da3c'    # 下跌颜色 (绿)
    background_color: str = '#ffffff'
    grid_color: str = '#e0e0e0'
    text_color: str = '#000000'
    
    # 买卖点标记
    buy_color: str = '#00da3c'     # 买入标记颜色
    sell_color: str = '#ec0000'    # 卖出标记颜色
    buy_symbol: str = 'triangle'   # 买入标记符号
    sell_symbol: str = 'pin'       # 卖出标记符号
    
    # 指标颜色
    ma_colors: Dict[str, str] = None
    indicator_colors: Dict[str, str] = None
    
    def __post_init__(self):
        if self.ma_colors is None:
            self.ma_colors = {
                'MA5': '#FF6B6B',
                'MA10': '#4ECDC4', 
                'MA20': '#45B7D1',
                'MA30': '#96CEB4',
                'MA60': '#FFEAA7',
                'EMA12': '#DDA0DD',
                'EMA26': '#98D8C8'
            }
        
        if self.indicator_colors is None:
            self.indicator_colors = {
                'MACD': '#FF6B6B',
                'MACD_signal': '#4ECDC4',
                'MACD_hist': '#45B7D1',
                'RSI': '#FF6B6B',
                'RSI_30': '#CCCCCC',
                'RSI_70': '#CCCCCC',
                'BOLL_upper': '#DDA0DD',
                'BOLL_middle': '#98D8C8',
                'BOLL_lower': '#DDA0DD',
                'KDJ_K': '#FF6B6B',
                'KDJ_D': '#4ECDC4',
                'KDJ_J': '#45B7D1'
            }


# 预定义主题
LIGHT_THEME = PlotTheme()

DARK_THEME = PlotTheme(
    theme='dark',
    background_color='#1f1f1f',
    grid_color='#404040',
    text_color='#ffffff'
)

# 主题映射
THEMES = {
    'light': LIGHT_THEME,
    'dark': DARK_THEME
}


def get_theme(theme_name: str) -> PlotTheme:
    """获取主题配置"""
    return THEMES.get(theme_name, LIGHT_THEME)
