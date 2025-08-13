"""
技术指标配置模块
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum


class IndicatorType(Enum):
    """指标类型枚举"""
    OVERLAY = "overlay"      # 叠加在主图上（如移动平均线）
    SUBPLOT = "subplot"      # 独立子图（如MACD、RSI）


class PlotType(Enum):
    """绘图类型枚举"""
    LINE = "line"
    BAR = "bar"
    HISTOGRAM = "histogram"


@dataclass
class IndicatorConfig:
    """技术指标配置"""
    
    name: str                              # 指标名称
    indicator_type: IndicatorType          # 指标类型（叠加/子图）
    plot_type: PlotType                    # 绘图类型
    params: Dict[str, Any] = field(default_factory=dict)  # 指标参数
    style: Dict[str, Any] = field(default_factory=dict)   # 样式配置
    enabled: bool = True                   # 是否启用
    
    # 子图配置（仅当indicator_type为SUBPLOT时有效）
    subplot_height: str = "15%"            # 子图高度
    subplot_position: str = "bottom"       # 子图位置


@dataclass  
class PlotIndicator:
    """可绘制的指标数据"""
    
    name: str                              # 指标名称
    data: Union[List, Dict[str, List]]     # 指标数据（单序列或多序列）
    config: IndicatorConfig                # 指标配置
    x_data: List = field(default_factory=list)  # X轴数据（时间序列）


# 预定义指标配置
DEFAULT_INDICATORS = {
    # 移动平均线
    'MA5': IndicatorConfig(
        name='MA5',
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE,
        params={'period': 5},
        style={'color': '#FF6B6B', 'width': 1}
    ),
    'MA10': IndicatorConfig(
        name='MA10', 
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE,
        params={'period': 10},
        style={'color': '#4ECDC4', 'width': 1}
    ),
    'MA20': IndicatorConfig(
        name='MA20',
        indicator_type=IndicatorType.OVERLAY, 
        plot_type=PlotType.LINE,
        params={'period': 20},
        style={'color': '#45B7D1', 'width': 1}
    ),
    'MA30': IndicatorConfig(
        name='MA30',
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE, 
        params={'period': 30},
        style={'color': '#96CEB4', 'width': 1}
    ),
    'MA60': IndicatorConfig(
        name='MA60',
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE,
        params={'period': 60}, 
        style={'color': '#FFEAA7', 'width': 1}
    ),
    
    # 指数移动平均线
    'EMA12': IndicatorConfig(
        name='EMA12',
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE,
        params={'period': 12},
        style={'color': '#DDA0DD', 'width': 1}
    ),
    'EMA26': IndicatorConfig(
        name='EMA26',
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE,
        params={'period': 26}, 
        style={'color': '#98D8C8', 'width': 1}
    ),
    
    # MACD
    'MACD': IndicatorConfig(
        name='MACD',
        indicator_type=IndicatorType.SUBPLOT,
        plot_type=PlotType.LINE,
        params={'fast': 12, 'slow': 26, 'signal': 9},
        style={'macd_color': '#FF6B6B', 'signal_color': '#4ECDC4', 'hist_color': '#45B7D1'},
        subplot_height="20%"
    ),
    
    # RSI
    'RSI': IndicatorConfig(
        name='RSI',
        indicator_type=IndicatorType.SUBPLOT,
        plot_type=PlotType.LINE,
        params={'period': 14},
        style={'color': '#FF6B6B', 'width': 2},
        subplot_height="15%"
    ),
    
    # 布林带
    'BOLL': IndicatorConfig(
        name='BOLL',
        indicator_type=IndicatorType.OVERLAY,
        plot_type=PlotType.LINE,
        params={'period': 20, 'std': 2},
        style={
            'upper_color': '#DDA0DD',
            'middle_color': '#98D8C8', 
            'lower_color': '#DDA0DD',
            'fill_opacity': 0.1
        }
    ),
    
    # KDJ
    'KDJ': IndicatorConfig(
        name='KDJ',
        indicator_type=IndicatorType.SUBPLOT,
        plot_type=PlotType.LINE,
        params={'n': 9, 'm1': 3, 'm2': 3},
        style={
            'k_color': '#FF6B6B',
            'd_color': '#4ECDC4', 
            'j_color': '#45B7D1'
        },
        subplot_height="15%"
    )
}


def get_indicator_config(name: str) -> Optional[IndicatorConfig]:
    """获取指标配置"""
    return DEFAULT_INDICATORS.get(name)


def create_custom_indicator(
    name: str,
    indicator_type: IndicatorType,
    plot_type: PlotType,
    params: Dict[str, Any] = None,
    style: Dict[str, Any] = None,
    **kwargs
) -> IndicatorConfig:
    """创建自定义指标配置"""
    return IndicatorConfig(
        name=name,
        indicator_type=indicator_type,
        plot_type=plot_type,
        params=params or {},
        style=style or {},
        **kwargs
    )
