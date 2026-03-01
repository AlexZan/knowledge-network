"""Prompt loading utilities."""

from pathlib import Path

from ..schemas import build_knowledge_prompt_section

PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt from the prompts directory.

    Args:
        name: Prompt name without extension (e.g., "system", "interpret")

    Returns:
        Prompt content as string

    Placeholders filled:
        {knowledge_types_section} — dynamic type descriptions from schema
    """
    prompt_path = PROMPTS_DIR / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    content = prompt_path.read_text(encoding="utf-8")
    if "{knowledge_types_section}" in content:
        content = content.replace("{knowledge_types_section}", build_knowledge_prompt_section())
    return content
