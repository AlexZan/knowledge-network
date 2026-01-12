"""Command-line interface for Open Intelligence."""

import os
import warnings
from dotenv import load_dotenv

# Suppress litellm's pydantic serialization warnings
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

load_dotenv()

import click

from .storage import load_state
from .conversation import process_turn
from .models import Artifact


DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")


def print_artifact(artifact: Artifact) -> None:
    """Print artifact notification."""
    click.echo()
    tags_str = f" [{', '.join(artifact.tags)}]" if artifact.tags else ""
    status_str = f" ({artifact.status})" if artifact.status else ""

    click.echo(f"[{artifact.artifact_type}{status_str}{tags_str}]")
    click.echo(f"  {artifact.summary}")

    if artifact.resolution:
        click.echo(f"  => {artifact.resolution}")

    click.echo()


@click.command()
@click.option("--model", default=DEFAULT_MODEL, help="LLM model to use")
def main(model: str) -> None:
    """Open Intelligence - Artifact-based knowledge system."""
    state = load_state()

    # Show current state summary
    open_efforts = state.get_open_efforts()
    if open_efforts:
        click.echo(f"[{len(open_efforts)} open effort(s)]")
        click.echo()

    while True:
        try:
            user_input = input("> ").strip()
        except EOFError:
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            break

        try:
            response, artifact = process_turn(state, user_input, model)

            # Print AI response
            click.echo()
            click.echo(response)
            click.echo()

            # Print artifact if created
            if artifact:
                print_artifact(artifact)

        except KeyboardInterrupt:
            click.echo("\nExiting...")
            break
        except Exception as e:
            click.echo(f"Error: {e}")


if __name__ == "__main__":
    main()
