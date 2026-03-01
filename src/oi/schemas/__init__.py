"""Schema loading utilities for the knowledge graph.

Loads node type and edge type definitions from node_types.yaml.
User overrides are checked first at ~/.oi/schemas/node_types.yaml.
"""

import yaml
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).parent
USER_SCHEMAS_DIR = Path.home() / ".oi" / "schemas"


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Load the full schema (node types + edge types).

    Checks user directory first, falls back to package defaults.
    Result is cached for the process lifetime.
    """
    user_path = USER_SCHEMAS_DIR / "node_types.yaml"
    if user_path.exists():
        return yaml.safe_load(user_path.read_text(encoding="utf-8"))

    default_path = SCHEMAS_DIR / "node_types.yaml"
    return yaml.safe_load(default_path.read_text(encoding="utf-8"))


def get_node_type_names() -> list[str]:
    """Get all node type names."""
    return list(load_schema()["node_types"].keys())


def get_extractable_types() -> list[str]:
    """Get node types that extract_knowledge can produce (extractable=true)."""
    return [name for name, cfg in load_schema()["node_types"].items() if cfg.get("extractable")]


def get_tool_addable_types() -> list[str]:
    """Get node types that appear in add_knowledge/query_knowledge tool enums (tool_addable=true)."""
    return [name for name, cfg in load_schema()["node_types"].items() if cfg.get("tool_addable")]


def get_display_visible_types() -> list[str]:
    """Get node types shown in the knowledge section of the system prompt (show_in_display=true)."""
    return [name for name, cfg in load_schema()["node_types"].items() if cfg.get("show_in_display")]


def get_linkable_edge_types() -> list[str]:
    """Get edge types that the auto-linker can produce (linkable=true)."""
    return [name for name, cfg in load_schema().get("edge_types", {}).items() if cfg.get("linkable")]


def get_all_edge_type_names() -> list[str]:
    """Get all edge type names."""
    return list(load_schema().get("edge_types", {}).keys())


def node_display_prefix(node: dict) -> str:
    """Build display prefix for a knowledge node.

    Returns "[fact]" for most types, or "[principle, 3 instances]" for principles
    with instance_count, using the display_with_instances format from the schema.
    """
    node_type = node.get("type", "")
    schema = load_schema()
    type_cfg = schema.get("node_types", {}).get(node_type, {})

    fmt = type_cfg.get("display_with_instances")
    if fmt and node.get("instance_count"):
        return fmt.format(instance_count=node["instance_count"])

    return f"[{node_type}]"


def build_knowledge_prompt_section() -> str:
    """Build the dynamic type descriptions section for the system prompt.

    Generates the **Types:** block from schema prompt_description fields.
    Only includes tool_addable types (fact, preference, decision).
    """
    schema = load_schema()
    lines = ["**Types:**"]
    for name, cfg in schema["node_types"].items():
        if not cfg.get("tool_addable"):
            continue
        desc = cfg.get("prompt_description", "").strip()
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines)


def build_extraction_type_list() -> str:
    """Build the type constraint string for extract_knowledge prompts.

    Returns e.g. 'node_type must be one of: fact, preference, decision'
    """
    types = get_extractable_types()
    return "node_type must be one of: " + ", ".join(types)


# ------------------------------------------------------------------
# Backward compatibility aliases (used by interpret.py and old tests)
# ------------------------------------------------------------------

def load_artifact_types() -> dict[str, Any]:
    """Legacy alias: load artifact type definitions."""
    schema = load_schema()
    # Reshape to old format for backward compat
    types = {}
    for name, cfg in schema["node_types"].items():
        types[name] = {
            "description": cfg.get("prompt_description", "").strip(),
            "expires": False,
            "has_status": name == "effort",
            "has_resolution": name == "effort",
        }
    return {"types": types}


def get_artifact_type_names() -> list[str]:
    """Legacy alias: get list of valid artifact type names."""
    return get_node_type_names()


def build_interpretation_prompt_section() -> str:
    """Legacy alias: build artifact types section for interpretation prompt."""
    schema = load_artifact_types()
    types = schema["types"]

    lines = ["## Artifact Types", "", "| Type | Description | Expires? |", "|------|-------------|----------|"]

    for name, config in types.items():
        expires = "Yes" if config.get("expires", False) else "No"
        lines.append(f"| {name} | {config['description']} | {expires} |")

    lines.append("")

    has_status_types = [n for n, c in types.items() if c.get("has_status")]
    if has_status_types:
        lines.append("## Effort Status")
        lines.append("")
        lines.append("- **open**: User is still working on this, no decision yet")
        lines.append("- **resolved**: User made a decision or completed the goal - MUST include resolution")
        lines.append("")

    return "\n".join(lines)
