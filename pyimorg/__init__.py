from __future__ import annotations

import click

from .cli import diff, groupby

__all__ = ['cli']

@click.group()
def cli():
    """Command-line tool for organizing images."""
    pass

cli.command(diff)
cli.command(groupby)
