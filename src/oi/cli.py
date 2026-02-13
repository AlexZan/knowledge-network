"""Command-line interface for Open Intelligence."""

import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Suppress litellm's pydantic serialization warnings
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

load_dotenv()

import click
import yaml

from .orchestrator import process_turn


DEFAULT_SESSION_DIR = Path.home() / ".oi" / "session"


@click.command()
@click.option("--session-dir", default=str(DEFAULT_SESSION_DIR), help="Session directory path")
def main(session_dir: str) -> None:
    """Open Intelligence - Effort-based context management."""
    session_path = Path(session_dir)
    session_path.mkdir(parents=True, exist_ok=True)

    # Show current state
    manifest_path = session_path / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text())
        open_efforts = [e for e in manifest.get("efforts", []) if e.get("status") == "open"]
        if open_efforts:
            click.echo(f"[{len(open_efforts)} open effort(s)]")
            for e in open_efforts:
                click.echo(f"  - {e['id']}")
            click.echo()

    click.echo("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo()
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            break

        try:
            response = process_turn(session_path, user_input)
            click.echo()
            click.echo(response)
            click.echo()
        except Exception as e:
            click.echo(f"Error: {e}")


if __name__ == "__main__":
    main()
