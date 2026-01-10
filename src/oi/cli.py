"""Command-line interface for Open Intelligence."""

import os
import click

from .storage import load_state
from .conversation import process_turn


DEFAULT_MODEL = os.environ.get("OI_MODEL", "deepseek/deepseek-chat")


def print_conclusion(conclusion, raw_tokens: int, compacted_tokens: int) -> None:
    """Print conclusion notification with token stats."""
    savings = (1 - compacted_tokens / raw_tokens) * 100 if raw_tokens > 0 else 0
    click.echo()
    click.echo(f"[Conclusion extracted: {conclusion.content}]")
    click.echo(f"[Tokens: {raw_tokens:,} raw → {compacted_tokens:,} compacted | Savings: {savings:.0f}%]")
    click.echo()


@click.command()
@click.option("--model", default=DEFAULT_MODEL, help="LLM model to use")
@click.option("--llm-detection", is_flag=True, help="Use LLM for disagreement detection")
def main(model: str, llm_detection: bool) -> None:
    """Open Intelligence - Conclusion-based conversation system."""
    state = load_state()

    while True:
        try:
            user_input = input("> ").strip()

            if not user_input:
                continue

            if user_input.lower() == "exit":
                break

            # Process the turn
            response, conclusion, token_stats = process_turn(
                state,
                user_input,
                model,
                use_llm_detection=llm_detection
            )

            # Print AI response
            click.echo()
            click.echo(response)
            click.echo()

            # Print conclusion if extracted
            if conclusion and token_stats:
                print_conclusion(conclusion, token_stats[0], token_stats[1])

        except KeyboardInterrupt:
            click.echo("\nExiting...")
            break
        except Exception as e:
            click.echo(f"Error: {e}")


if __name__ == "__main__":
    main()
