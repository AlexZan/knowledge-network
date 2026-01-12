"""Command-line interface for Open Intelligence."""

import os
import warnings
from dotenv import load_dotenv

# Suppress litellm's pydantic serialization warnings (DeepSeek response format mismatch)
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

load_dotenv()

import click

from .storage import load_state
from .conversation import process_turn
from .models import Artifact, Conclusion


DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")


def print_conclusion(conclusion, raw_tokens: int, compacted_tokens: int) -> None:
    """Print conclusion notification with token stats."""
    savings = (1 - compacted_tokens / raw_tokens) * 100 if raw_tokens > 0 else 0
    click.echo()
    click.echo(f"[Conclusion extracted: {conclusion.content}]")
    click.echo(f"[Tokens: {raw_tokens:,} raw -> {compacted_tokens:,} compacted | Savings: {savings:.0f}%]")
    click.echo()


def print_artifact(artifact: Artifact) -> None:
    """Print artifact notification."""
    click.echo()
    tags_str = f" [{', '.join(artifact.tags)}]" if artifact.tags else ""
    status_str = f" ({artifact.status})" if artifact.status else ""
    click.echo(f"[Artifact: {artifact.artifact_type}{status_str}{tags_str}]")
    click.echo(f"  {artifact.summary}")
    click.echo()


@click.command()
@click.option("--model", default=DEFAULT_MODEL, help="LLM model to use")
@click.option("--llm-detection", is_flag=True, help="Use LLM for disagreement detection")
@click.option("--artifacts", is_flag=True, help="Use new artifact system (agentic interpretation)")
def main(model: str, llm_detection: bool, artifacts: bool) -> None:
    """Open Intelligence - Conclusion-based conversation system."""
    state = load_state()

    if artifacts:
        click.echo("[Artifact mode enabled - LLM interprets each exchange]")
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
            # Process the turn
            response, result, token_stats = process_turn(
                state,
                user_input,
                model,
                use_llm_detection=llm_detection,
                use_artifacts=artifacts
            )

            # Print AI response
            click.echo()
            click.echo(response)
            click.echo()

            # Print result based on mode
            if result:
                if isinstance(result, Artifact):
                    print_artifact(result)
                elif isinstance(result, Conclusion) and token_stats:
                    print_conclusion(result, token_stats[0], token_stats[1])

        except KeyboardInterrupt:
            click.echo("\nExiting...")
            break
        except Exception as e:
            click.echo(f"Error: {e}")


if __name__ == "__main__":
    main()
