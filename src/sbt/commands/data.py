
import sys
import os
from typing import List
import click
from loguru import logger
from dotenv import load_dotenv

try:
    from xtquant import xtdata
except Exception as e:  # pragma: no cover - runtime env dependent
    xtdata = None
    _import_err = e
else:
    _import_err = None


@click.group(help="数据相关命令")
def data():
    pass


@data.command("download_history", help="下载股票历史数据到 .env 配置目录并导出Parquet")
@click.option("--code_list", required=True, help="以逗号分隔的证券代码，如 000001.SH,002097.SZ")
@click.option("--start_date", required=True, help="开始日期，YYYYMMDD，如 20170101")
@click.option("--end_date", required=True, help="结束日期，YYYYMMDD，如 20171231")
@click.option("--period", default="1d", show_default=True, help="周期，如 1d, 60m, 30m, 15m, 5m, 1m")
@click.option("--dividend_type", default="none", show_default=True, help="复权方式，传给 get_market_data 时可用：none/backward/forward/back_ratio 等（下载阶段忽略）")
@click.option("--verbose/--no-verbose", default=True, show_default=True, help="是否打印详细日志")
def download_history(code_list: str, start_date: str, end_date: str, period: str, dividend_type: str, verbose: bool):
    """下载并校验指定代码在时间区间的历史数据，保存为Parquet到.env配置的DATA_DIR/history。"""
    if xtdata is None:
        click.echo(f"xtquant.xtdata 未就绪：{_import_err}", err=True)
        sys.exit(1)

    # 读取.env配置
    load_dotenv()
    env_data_dir = os.getenv("DATA_DIR", None)
    if not env_data_dir:
        click.echo(".env 文件未配置 DATA_DIR 变量，或未找到 .env 文件。", err=True)
        sys.exit(10)
    data_dir = os.path.abspath(os.path.join(env_data_dir, "history"))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

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

    logger.info(f"开始下载：codes={codes}, period={period}, {start_date}-{end_date}")

    ok, fail = [], []
    for code in codes:
        try:
            logger.info(f"下载 {code} {period} {start_date}-{end_date} ...")
            xtdata.download_history_data(code, period, start_date, end_date)
            ok.append(code)
        except Exception as e:
            logger.exception(f"下载 {code} 失败：{e}")
            fail.append(code)

    if ok:
        logger.info(f"下载成功：{ok}")

    # 读取数据并保存为Parquet
    if ok:
        try:
            logger.info("读取所有股票数据并导出Parquet ...")
            df_dict = xtdata.get_market_data(field_list=[], stock_list=ok, period=period, start_time=start_date, end_time=end_date, count=-1, dividend_type='back_ratio')
            
            if isinstance(df_dict, dict) and 'time' in df_dict:
                # get_market_data 返回按字段分组的字典: {'time': df, 'open': df, 'high': df, ...}
                # 每个 df 的 index 是股票代码，columns 是时间序列
                time_df = df_dict.get('time', None)
                if time_df is not None and not time_df.empty:
                    # 重构数据: 为每个股票创建包含所有字段的 DataFrame
                    for code in ok:
                        if code in time_df.index:
                            # 为每个股票构建完整的 OHLCV DataFrame
                            stock_data = {}
                            has_data = False
                            for field, field_df in df_dict.items():
                                if code in field_df.index:
                                    stock_data[field] = field_df.loc[code]
                                    if not field_df.loc[code].empty:
                                        has_data = True
                            
                            if has_data and stock_data:
                                # 转换为 DataFrame
                                import pandas as pd
                                df = pd.DataFrame(stock_data)
                                
                                if not df.empty:
                                    fname = f"{code}_{period}_{start_date}_{end_date}.parquet"
                                    fpath = os.path.join(data_dir, fname)
                                    df.to_parquet(fpath, index=True)  # 保留时间索引
                                    logger.info(f"已保存为Parquet: {fpath} (行数: {len(df)})")
                                else:
                                    logger.warning(f"{code} 无数据，未导出Parquet。")
                            else:
                                logger.warning(f"{code} 无数据，未导出Parquet。")
                else:
                    logger.warning("返回的数据为空")
            else:
                logger.warning("get_market_data 返回格式异常，未导出Parquet。")
        except Exception as e:
            logger.warning(f"导出Parquet失败：{e}")
            # 如果批量失败，尝试逐个处理
            logger.info("尝试逐个处理...")
            for code in ok:
                try:
                    df_dict = xtdata.get_market_data(field_list=[], stock_list=[code], period=period, start_time=start_date, end_time=end_date, count=-1, dividend_type='back_ratio')
                    if isinstance(df_dict, dict) and 'time' in df_dict:
                        time_df = df_dict.get('time', None)
                        if time_df is not None and not time_df.empty and code in time_df.index:
                            stock_data = {}
                            for field, field_df in df_dict.items():
                                if code in field_df.index:
                                    stock_data[field] = field_df.loc[code]
                            
                            import pandas as pd
                            df = pd.DataFrame(stock_data)
                            if not df.empty:
                                fname = f"{code}_{period}_{start_date}_{end_date}.parquet"
                                fpath = os.path.join(data_dir, fname)
                                df.to_parquet(fpath, index=True)
                                logger.info(f"已保存为Parquet: {fpath} (行数: {len(df)})")
                            else:
                                logger.warning(f"{code} 无数据，未导出Parquet。")
                        else:
                            logger.warning(f"{code} 无数据，未导出Parquet。")
                except Exception as e2:
                    logger.warning(f"导出 {code} Parquet 失败：{e2}")

    if fail:
        logger.error(f"下载失败：{fail}")
        sys.exit(3)

    logger.info(f"全部数据已保存到：{data_dir}")