"""Session state persistence: manifest, expanded efforts, turn counter.

All file I/O for session state is centralized here to keep tools.py
focused on tool definitions/handlers and decay.py free of circular imports.
"""

import json
import yaml
from pathlib import Path
from datetime import datetime


# === Manifest (efforts list with status/summary) ===

def _load_manifest(session_dir: Path) -> dict:
    """Load manifest.yaml, returning empty structure if missing."""
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {"efforts": []}
    return {"efforts": []}


def _save_manifest(session_dir: Path, manifest: dict):
    """Write manifest.yaml."""
    manifest_path = session_dir / "manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, default_flow_style=False)


# === Expanded state (which concluded efforts have raw logs loaded) ===

def _load_expanded(session_dir: Path) -> set:
    """Load the set of currently expanded effort IDs from expanded.json."""
    state = _load_expanded_state(session_dir)
    return set(state.get("expanded", []))


def _load_expanded_state(session_dir: Path) -> dict:
    """Load the full expanded state dict from expanded.json."""
    expanded_path = session_dir / "expanded.json"
    if expanded_path.exists():
        return json.loads(expanded_path.read_text(encoding="utf-8"))
    return {"expanded": [], "expanded_at": {}, "last_referenced_turn": {}}


def _save_expanded(session_dir: Path, expanded_set: set, last_referenced_turn: dict | None = None):
    """Save the set of expanded effort IDs to expanded.json.

    Preserves existing expanded_at timestamps for efforts that were already expanded.
    Updates last_referenced_turn if provided.
    """
    expanded_path = session_dir / "expanded.json"
    expanded_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat()

    # Load existing state to preserve timestamps
    existing = _load_expanded_state(session_dir)
    existing_at = existing.get("expanded_at", {})
    existing_lrt = existing.get("last_referenced_turn", {})

    # Build expanded_at: keep existing timestamps, add new ones
    expanded_at = {}
    for eid in expanded_set:
        expanded_at[eid] = existing_at.get(eid, now)

    # Build last_referenced_turn: merge provided over existing, prune removed
    lrt = last_referenced_turn if last_referenced_turn is not None else existing_lrt
    lrt = {eid: lrt[eid] for eid in expanded_set if eid in lrt}

    data = {
        "expanded": list(expanded_set),
        "expanded_at": expanded_at,
        "last_referenced_turn": lrt,
    }
    expanded_path.write_text(json.dumps(data), encoding="utf-8")


# === Session state (turn counter) ===

def _load_session_state(session_dir: Path) -> dict:
    """Load session_state.json, returning default if missing."""
    state_path = session_dir / "session_state.json"
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"turn_count": 0}


def _save_session_state(session_dir: Path, state: dict):
    """Write session_state.json."""
    state_path = session_dir / "session_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state["updated"] = datetime.now().isoformat()
    state_path.write_text(json.dumps(state), encoding="utf-8")


def increment_turn(session_dir: Path) -> int:
    """Increment the session turn counter. Returns the new turn count."""
    state = _load_session_state(session_dir)
    state["turn_count"] = state.get("turn_count", 0) + 1
    _save_session_state(session_dir, state)
    return state["turn_count"]
