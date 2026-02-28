"""Command-line interface for Open Intelligence."""

import json
import os
import warnings
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Suppress litellm's pydantic serialization warnings
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

load_dotenv()

import click

from .orchestrator import process_turn
from .state import _load_efforts, increment_session_count
from .session_log import create_session_log


DEFAULT_DATA_DIR = Path.home() / ".oi"


def _append_session_marker(session_dir: Path):
    """Append a session boundary marker to raw.jsonl."""
    raw_file = session_dir / "raw.jsonl"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "role": "system",
        "content": "--- New session started ---",
        "ts": datetime.now().isoformat(),
    }
    with open(raw_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _show_startup(session_dir: Path):
    """Show status on CLI launch."""
    efforts = _load_efforts(session_dir)
    open_efforts = [e for e in efforts if e.get("status") == "open"]
    concluded_count = sum(1 for e in efforts if e.get("status") == "concluded")

    if open_efforts:
        click.echo(f"[{len(open_efforts)} open effort(s)]")
        for e in open_efforts:
            click.echo(f"  - {e['id']}")
    if concluded_count:
        click.echo(f"[{concluded_count} concluded effort(s) searchable]")
    click.echo()


@click.command()
@click.option("--data-dir", default=None, help="Data directory (default: ~/.oi/)")
def main(data_dir: str | None) -> None:
    """Open Intelligence - Effort-based context management."""
    session_path = Path(data_dir) if data_dir else DEFAULT_DATA_DIR

    session_path.mkdir(parents=True, exist_ok=True)

    # Increment session count, create session log, and append session marker
    increment_session_count(session_path)
    session_id = create_session_log(session_path)
    _append_session_marker(session_path)

    # Show startup display
    _show_startup(session_path)

    click.echo("Type 'exit' to quit.\n")

    def _confirm_action(description: str) -> bool:
        """Prompt user to confirm an action before execution."""
        click.echo(f"\n[{description}] Allow? (y/n) ", nl=False)
        try:
            answer = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")

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
            response = process_turn(session_path, user_input, confirmation_callback=_confirm_action, session_id=session_id)
            click.echo()
            click.echo(response)
            click.echo()
        except Exception as e:
            click.echo(f"Error: {e}")


if __name__ == "__main__":
    main()
