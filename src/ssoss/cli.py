import sys
import click

from . import ssoss_cli
from .signal_layer import build_signal_layer


@click.group(invoke_without_command=True, context_settings={"help_option_names": ["-h", "--help"]})
@click.pass_context
def cli(ctx):
    """SSOSS command line interface."""
    if ctx.invoked_subcommand is None:
        ssoss_cli.main()


cli.add_command(build_signal_layer)

if __name__ == "__main__":
    cli()

