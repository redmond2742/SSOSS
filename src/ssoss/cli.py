import sys
import click

from . import ssoss_cli
from .signal_layer import build_signal_layer
from .cli import review_photos


@click.group(invoke_without_command=True, add_help_option=False)
@click.option("-h", "--help", "show_help", is_flag=True, is_eager=True,
              help="Show this message and exit.")
@click.pass_context
def cli(ctx, show_help):
    """SSOSS command line interface."""
    if ctx.invoked_subcommand is None:
        if show_help:
            try:
                ssoss_cli.main(["--help"])
            except SystemExit:
                pass
            if cli.commands:
                click.echo("\nCommands:")
                for name, cmd in cli.commands.items():
                    click.echo(f"  {name:<20} {cmd.get_short_help_str()}")
            ctx.exit()
        else:
            ssoss_cli.main()


cli.add_command(build_signal_layer)
cli.add_command(review_photos)

if __name__ == "__main__":
    cli()

