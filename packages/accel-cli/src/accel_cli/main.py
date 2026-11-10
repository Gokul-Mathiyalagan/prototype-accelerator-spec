"""The `accel` command."""

from __future__ import annotations

import typer

from accel_cli.commands import setup

app = typer.Typer(
    name="accel",
    help="Prototype Accelerator: repo intelligence, skills and the AISDLC.",
    no_args_is_help=True,
    add_completion=False,
)
app.command("setup")(setup.setup)
app.command("doctor")(setup.doctor)


def main() -> None:
    """Entry point for the `accel` script."""
    app()
