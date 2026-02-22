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
import yaml

from .orchestrator import process_turn
from .state import increment_session_count


DEFAULT_SESSION_DIR = Path.home() / ".oi" / "projects" / "default"


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


def _show_startup(session_dir: Path, project_name: str, session_num: int):
    """Show project status on CLI launch."""
    manifest_path = session_dir / "manifest.yaml"
    open_efforts = []
    concluded_count = 0

    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        efforts = manifest.get("efforts", [])
        open_efforts = [e for e in efforts if e.get("status") == "open"]
        concluded_count = sum(1 for e in efforts if e.get("status") == "concluded")

    click.echo(f"[Project: {project_name} | Session #{session_num}]")
    if open_efforts:
        click.echo(f"[{len(open_efforts)} open effort(s)]")
        for e in open_efforts:
            click.echo(f"  - {e['id']}")
    if concluded_count:
        click.echo(f"[{concluded_count} concluded effort(s) searchable]")
    click.echo()


@click.command()
@click.option("--session-dir", default=None, help="Session directory path (overrides --project)")
@click.option("--project", default=None, help="Project name for per-project sessions")
def main(session_dir: str | None, project: str | None) -> None:
    """Open Intelligence - Effort-based context management."""
    if session_dir:
        session_path = Path(session_dir)
        project_name = session_path.name
    elif project:
        session_path = Path.home() / ".oi" / "projects" / project
        project_name = project
    else:
        session_path = DEFAULT_SESSION_DIR
        project_name = "default"

    session_path.mkdir(parents=True, exist_ok=True)

    # Increment session count and append session marker
    session_num = increment_session_count(session_path)
    _append_session_marker(session_path)

    # Show startup display
    _show_startup(session_path, project_name, session_num)

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
