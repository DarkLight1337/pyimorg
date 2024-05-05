import click

from .diff import diff
from .groupby import groupby

__all__ = ['cli']

@click.group()
def cli():
    """Command-line tool for organizing images."""
    pass

cli.command(diff)
cli.command(groupby)
