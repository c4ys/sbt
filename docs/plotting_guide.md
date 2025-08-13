# SBT 独立绘图模块

基于 autotrader 的 autoplot 设计理念，SBT 新增了独立的绘图模块，支持在交易策略中配置指标参数，提供更灵活和强大的图表绘制功能。

## 主要特性

### 🎨 独立绘图模块
- **模块化设计**: 绘图功能独立于回测引擎
- **灵活配置**: 支持主题、样式、指标参数自定义
- **扩展性强**: 易于添加新指标和图表类型

### 📊 丰富的技术指标
- **趋势指标**: MA、EMA、SMA
- **动量指标**: MACD、RSI、KDJ、Stochastic
- **波动指标**: Bollinger Bands、ATR
- **成交量指标**: Volume
- **自定义指标**: 支持用户自定义技术指标

### ⚙️ 策略配置指标参数
- **策略内配置**: 在策略类中直接配置绘图指标
- **参数化指标**: 支持灵活的指标参数配置
- **动态启用**: 可动态启用/禁用特定指标

## 快速开始

### 1. 在策略中配置指标

```python
from sbt.backtest import StrategyBase

class MyStrategy(StrategyBase):
    def init(self):
        # 配置绘图主题
        self.configure_plot(theme='light')
        
        # 添加移动平均线指标
        self.add_plot_indicator('MA20', period=20)
        self.add_plot_indicator('MA60', period=60)
        
        # 添加MACD指标
        self.add_plot_indicator('MACD', fast=12, slow=26, signal=9)
        
        # 添加RSI指标
        self.add_plot_indicator('RSI', period=14)
        
        # 添加布林带
        self.add_plot_indicator('BOLL', period=20, std=2)
        
        # 可选指标（默认禁用）
        self.add_plot_indicator('KDJ', n=9, m1=3, m2=3, enabled=False)
    
    def next(self, i: int):
        # 策略逻辑
        pass
```

### 2. 使用回测引擎绘图

```python
from sbt.backtest import BacktestEngine

# 运行回测
engine = BacktestEngine(data, MyStrategy)
results = engine.run()

# 生成图表（默认使用新绘图模块）
filename = engine.plot(filename="backtest_result.html", show_in_browser=True)
```

### 3. 使用独立绘图器

```python
from sbt.plotting import AutoPlotter

# 创建绘图器
plotter = AutoPlotter(theme='light')

# 添加指标
plotter.add_indicator(data, 'MA20', period=20)
plotter.add_indicator(data, 'MACD', fast=12, slow=26, signal=9)
plotter.add_indicator(data, 'RSI', period=14)

# 生成图表
filename = plotter.plot(
    data=data,
    trades=trades,
    equity_curve=equity_curve,
    filename="custom_plot.html",
    title="自定义图表"
)
```

## 支持的指标

### 趋势指标
- `MA{period}`: 简单移动平均线
- `EMA{period}`: 指数移动平均线
- `SMA{period}`: 简单移动平均线（同MA）

### 动量指标
- `MACD`: MACD指标
- `RSI`: 相对强弱指标
- `KDJ`: KDJ随机指标
- `STOCH`: 随机指标

### 波动指标
- `BOLL`: 布林带
- `ATR`: 平均真实波幅
- `WILLR`: 威廉指标

## 指标参数配置

### 移动平均线
```python
self.add_plot_indicator('MA20', period=20)
self.add_plot_indicator('EMA12', period=12)
```

### MACD
```python
self.add_plot_indicator('MACD', fast=12, slow=26, signal=9)
```

### RSI
```python
self.add_plot_indicator('RSI', period=14)
```

### 布林带
```python
self.add_plot_indicator('BOLL', period=20, std=2)
```

### KDJ
```python
self.add_plot_indicator('KDJ', n=9, m1=3, m2=3)
```

## 主题配置

### 内置主题
- `light`: 浅色主题（默认）
- `dark`: 深色主题

```python
# 在策略中配置主题
self.configure_plot(theme='dark')

# 或在绘图器中配置
plotter = AutoPlotter(theme='dark')
```

### 自定义主题
```python
from sbt.plotting import PlotTheme

custom_theme = PlotTheme(
    theme='custom',
    up_color='#FF0000',      # 上涨颜色
    down_color='#00FF00',    # 下跌颜色
    background_color='#FFFFFF',
    buy_color='#00FF00',     # 买入标记颜色
    sell_color='#FF0000'     # 卖出标记颜色
)

plotter = AutoPlotter(theme=custom_theme)
```

## 自定义指标

### 创建自定义指标配置
```python
from sbt.plotting.indicators import create_custom_indicator, IndicatorType, PlotType

config = create_custom_indicator(
    name='CustomMA',
    indicator_type=IndicatorType.OVERLAY,  # 叠加在主图
    plot_type=PlotType.LINE,
    params={'period': 10},
    style={'color': '#FF00FF', 'width': 2}
)
```

### 添加自定义指标数据
```python
# 计算自定义指标
custom_data = data['Close'].rolling(window=10).mean()

# 添加到绘图器
plotter.add_custom_indicator(
    name='CustomMA',
    data=custom_data,
    x_data=data.index.strftime('%Y-%m-%d').tolist(),
    config=config
)
```

## API 参考

### AutoPlotter 类
主要的绘图器类，提供完整的图表绘制功能。

#### 方法
- `add_indicator(data, indicator_name, config=None, **params)`: 添加技术指标
- `add_custom_indicator(name, data, x_data, config)`: 添加自定义指标
- `plot(data, trades=None, equity_curve=None, ...)`: 绘制完整图表
- `clear_indicators()`: 清除所有指标

### StrategyBase 新增方法
策略基类新增的绘图配置方法。

#### 方法
- `configure_plot(theme='light')`: 配置绘图主题
- `add_plot_indicator(indicator_name, enabled=True, **params)`: 添加绘图指标
- `remove_plot_indicator(indicator_name)`: 移除绘图指标
- `enable_plot_indicator(indicator_name, enabled=True)`: 启用/禁用指标

### BacktestEngine 更新
回测引擎集成新的绘图功能。

#### 方法
- `plot(filename=None, show_in_browser=False, use_new_plotter=True)`: 绘制回测结果
  - `use_new_plotter=True`: 使用新绘图模块（推荐）
  - `use_new_plotter=False`: 使用原有绘图代码（兼容性）

## 示例

完整的使用示例请参考：
- `examples/plot_demo.py`: 演示脚本
- `strategies/SMACross.py`: 更新后的示例策略

运行演示：
```bash
cd examples
python plot_demo.py
```

## 优势对比

### 与原有绘图模块对比

| 特性 | 原有模块 | 新绘图模块 |
|------|----------|------------|
| 模块化 | 集成在引擎中 | 独立模块 |
| 指标配置 | 硬编码 | 策略中配置 |
| 扩展性 | 有限 | 高度可扩展 |
| 自定义指标 | 不支持 | 完全支持 |
| 主题支持 | 基础 | 丰富的主题选项 |
| 代码复用 | 低 | 高 |

### 向后兼容性
- 保留原有的 `engine.plot()` 接口
- 通过 `use_new_plotter` 参数选择绘图模块
- 原有策略代码无需修改即可工作

## 注意事项

1. **依赖库**: 确保安装了 `pyecharts` 和 `ta-lib`（可选）
2. **数据格式**: 输入数据应包含 OHLCV 列
3. **性能**: 大量指标可能影响绘图性能
4. **浏览器**: 生成的HTML文件需要在现代浏览器中查看

## 扩展开发

### 添加新指标
1. 在 `calculator.py` 中添加计算函数
2. 在 `indicators.py` 中添加配置
3. 更新 `calculate_indicator` 函数

### 添加新图表类型
1. 在 `indicators.py` 中添加 `PlotType` 枚举值
2. 在 `plotter.py` 中实现对应的绘图方法

### 自定义主题
继承 `PlotTheme` 类或创建新的主题配置。

## 未来计划

- [ ] 支持更多技术指标
- [ ] 3D图表支持
- [ ] 实时数据绘图
- [ ] 图表交互功能
- [ ] 导出为图片格式
- [ ] 移动端适配
