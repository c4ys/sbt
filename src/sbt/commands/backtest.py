import sys
import os
from typing import List
import click
from loguru import logger
from dotenv import load_dotenv
import pandas as pd

try:
    from backtesting import Backtest
except Exception as e:
    logger.error(f"无法导入 backtesting 库：{e}")
    Backtest = None


@click.group(help="回测相关命令")
def backtest():
    pass


def check_data_exists(code: str, period: str, start_date: str, end_date: str, data_dir: str) -> bool:
    """检查数据文件是否存在"""
    fname = f"{code}_{period}_{start_date}_{end_date}.parquet"
    fpath = os.path.join(data_dir, "history", fname)
    return os.path.exists(fpath)


def load_strategy_class(strategy_name: str, strategy_dir: str):
    """动态加载策略类"""
    strategy_file = os.path.join(strategy_dir, f"{strategy_name}.py")
    if not os.path.exists(strategy_file):
        raise FileNotFoundError(f"策略文件不存在: {strategy_file}")
    
    import importlib.util
    spec = importlib.util.spec_from_file_location(strategy_name, strategy_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 查找策略类（通常与文件名相同）
    if hasattr(module, strategy_name):
        return getattr(module, strategy_name)
    else:
        # 如果没有同名类，查找继承自 Strategy 的类
        from backtesting import Strategy
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, Strategy) and 
                attr != Strategy):
                return attr
        raise AttributeError(f"在 {strategy_file} 中找不到有效的策略类")


def load_data(code: str, period: str, start_date: str, end_date: str, data_dir: str) -> pd.DataFrame:
    """加载股票数据"""
    fname = f"{code}_{period}_{start_date}_{end_date}.parquet"
    fpath = os.path.join(data_dir, "history", fname)
    
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"数据文件不存在: {fpath}")
    
    df = pd.read_parquet(fpath)
    
    # 转换为 backtesting 需要的格式
    # 需要列名: Open, High, Low, Close, Volume
    df_bt = pd.DataFrame()
    
    # 处理时间索引
    if 'time' in df.columns:
        df['datetime'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('datetime', inplace=True)
    
    # 重命名列以符合 backtesting 要求
    column_mapping = {
        'open': 'Open',
        'high': 'High', 
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in df.columns:
            df_bt[new_col] = df[old_col]
    
    # 确保必要的列存在
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df_bt.columns:
            raise ValueError(f"缺少必要的数据列: {col}")
    
    # 处理NaN值 - 删除包含NaN的行
    logger.info(f"数据处理前行数: {len(df_bt)}")
    df_bt = df_bt.dropna()
    logger.info(f"删除NaN后行数: {len(df_bt)}")
    
    if len(df_bt) == 0:
        raise ValueError("删除NaN值后数据为空，无法进行回测")
    
    return df_bt


@backtest.command("run", help="运行回测")
@click.option("--code_list", required=True, help="以逗号分隔的证券代码，如 000001.SH,002097.SZ")
@click.option("--start_date", required=True, help="开始日期，YYYYMMDD，如 20240901")
@click.option("--end_date", required=True, help="结束日期，YYYYMMDD，如 20250808")
@click.option("--period", default="1d", show_default=True, help="周期，如 1d, 30m, 5m")
@click.option("--strategy", required=True, help="策略名称，如 SMACross")
@click.option("--cash", default=10000, show_default=True, help="初始资金")
@click.option("--commission", default=0.002, show_default=True, help="手续费率")
@click.option("--verbose/--no-verbose", default=True, show_default=True, help="是否打印详细日志")
def run_backtest(code_list: str, start_date: str, end_date: str, period: str, strategy: str, cash: float, commission: float, verbose: bool):
    """运行回测"""
    if Backtest is None:
        click.echo("backtesting 库未就绪，无法运行回测。", err=True)
        sys.exit(1)
    
    # 读取.env配置
    load_dotenv()
    data_dir = os.getenv("DATA_DIR", "./data")
    strategy_dir = os.getenv("STRATEGY_DIR", "./strategies")
    
    if verbose:
        logger.remove()
        logger.add(sys.stdout, level="INFO")
    else:
        logger.remove()
        logger.add(sys.stdout, level="WARNING")
    
    codes: List[str] = [c.strip() for c in code_list.split(",") if c.strip()]
    if not codes:
        click.echo("未提供有效的证券代码。", err=True)
        sys.exit(2)
    
    # 确保策略目录存在
    if not os.path.exists(strategy_dir):
        os.makedirs(strategy_dir, exist_ok=True)
        logger.info(f"创建策略目录: {strategy_dir}")
    
    # 加载策略类
    try:
        strategy_class = load_strategy_class(strategy, strategy_dir)
        logger.info(f"加载策略: {strategy}")
    except Exception as e:
        logger.error(f"加载策略失败: {e}")
        sys.exit(3)
    
    # 检查并下载数据
    missing_data = []
    for code in codes:
        if not check_data_exists(code, period, start_date, end_date, data_dir):
            missing_data.append(code)
    
    if missing_data:
        logger.info(f"以下股票数据缺失，开始下载: {missing_data}")
        # 调用数据下载功能
        from click.testing import CliRunner
        from .data import download_history as download_cmd
        
        runner = CliRunner()
        result = runner.invoke(download_cmd, [
            '--code_list', ','.join(missing_data),
            '--start_date', start_date,
            '--end_date', end_date,
            '--period', period,
            '--verbose' if verbose else '--no-verbose'
        ])
        
        if result.exit_code != 0:
            logger.error(f"数据下载失败: {result.output}")
            sys.exit(4)
        
        logger.info("数据下载完成")
    
    # 对每只股票运行回测
    results = {}
    for code in codes:
        try:
            logger.info(f"开始回测: {code}")
            
            # 加载数据
            df = load_data(code, period, start_date, end_date, data_dir)
            logger.info(f"{code} 数据加载完成，数据量: {len(df)}")
            
            # 运行回测
            bt = Backtest(df, strategy_class, cash=cash, commission=commission)
            result = bt.run()
            
            results[code] = result
            
            # 输出结果
            logger.info(f"{code} 回测完成:")
            logger.info(f"  总收益率: {result['Return [%]']:.2f}%")
            logger.info(f"  年化收益率: {result.get('Return (Ann.) [%]', 'N/A')}")
            logger.info(f"  最大回撤: {result.get('Max. Drawdown [%]', 'N/A')}")
            logger.info(f"  夏普比率: {result.get('Sharpe Ratio', 'N/A')}")
            logger.info(f"  交易次数: {result.get('# Trades', 'N/A')}")
            
            # 保存结果图表（如果有的话）
            try:
                output_dir = os.path.join(data_dir, "backtest_results")
                os.makedirs(output_dir, exist_ok=True)
                chart_path = os.path.join(output_dir, f"{code}_{strategy}_{period}_{start_date}_{end_date}.html")
                bt.plot(filename=chart_path)
                logger.info(f"  图表已保存: {chart_path}")
            except Exception as e:
                logger.warning(f"保存图表失败: {e}")
                
        except Exception as e:
            logger.error(f"{code} 回测失败: {e}")
            continue
    
    # 汇总结果
    if results:
        logger.info("\n=== 回测汇总 ===")
        for code, result in results.items():
            logger.info(f"{code}: 收益率 {result['Return [%]']:.2f}%")
    else:
        logger.error("所有回测都失败了")
        sys.exit(5)
