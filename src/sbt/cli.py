import sys
import click
from loguru import logger

from .commands.data import data as data_group
from .commands.backtest import backtest as backtest_group


@click.group(help="sbt - Simple Backtest CLI")
def app():
    """Root command group for sbt CLI."""
    pass


# register sub-commands
app.add_command(data_group, name="data")
app.add_command(backtest_group, name="backtest")


def main():  # pragma: no cover
    try:
        app(prog_name="sbt")
    except SystemExit:
        raise
    except Exception:
        logger.exception("Unhandled exception")
        sys.exit(1)
