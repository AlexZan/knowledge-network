"""Schema loading utilities."""

import yaml
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).parent
USER_SCHEMAS_DIR = Path.home() / ".oi" / "schemas"


def load_artifact_types() -> dict[str, Any]:
    """Load artifact type definitions.

    Checks user directory first, falls back to package defaults.

    Returns:
        Dict with 'types' key containing type definitions
    """
    # Check user override first
    user_path = USER_SCHEMAS_DIR / "artifact_types.yaml"
    if user_path.exists():
        return yaml.safe_load(user_path.read_text(encoding="utf-8"))

    # Fall back to package defaults
    default_path = SCHEMAS_DIR / "artifact_types.yaml"
    return yaml.safe_load(default_path.read_text(encoding="utf-8"))


def get_artifact_type_names() -> list[str]:
    """Get list of valid artifact type names."""
    schema = load_artifact_types()
    return list(schema["types"].keys())


def build_interpretation_prompt_section() -> str:
    """Build the artifact types section for the interpretation prompt.

    Dynamically generates from schema definitions.
    """
    schema = load_artifact_types()
    types = schema["types"]

    lines = ["## Artifact Types", "", "| Type | Description | Expires? |", "|------|-------------|----------|"]

    for name, config in types.items():
        expires = "Yes" if config.get("expires", False) else "No"
        lines.append(f"| {name} | {config['description']} | {expires} |")

    lines.append("")

    # Add status section if any type has status
    has_status_types = [n for n, c in types.items() if c.get("has_status")]
    if has_status_types:
        lines.append("## Effort Status")
        lines.append("")
        lines.append("- **open**: User is still working on this, no decision yet")
        lines.append("- **resolved**: User made a decision or completed the goal - MUST include resolution")
        lines.append("")

    return "\n".join(lines)
