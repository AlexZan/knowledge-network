"""Session state persistence: knowledge graph (unified store), expanded efforts, turn counter.

All file I/O for session state is centralized here to keep tools.py
focused on tool definitions/handlers and decay.py free of circular imports.
"""

import json
import yaml
from pathlib import Path
from datetime import datetime


# === Migration: manifest.yaml → knowledge.yaml ===

def _migrate_manifest_to_knowledge(session_dir: Path):
    """Migrate efforts from manifest.yaml into knowledge.yaml as type='effort' nodes.

    Reads manifest.yaml, converts each effort to a knowledge node with type='effort',
    merges into knowledge.yaml (skipping duplicates), and renames manifest to .bak.
    Idempotent: does nothing if manifest.yaml doesn't exist.
    """
    manifest_path = session_dir / "manifest.yaml"
    if not manifest_path.exists():
        return

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {"efforts": []}
    efforts = manifest.get("efforts", [])
    if not efforts:
        manifest_path.rename(session_dir / "manifest.yaml.bak")
        return

    knowledge = _load_knowledge(session_dir)
    existing_ids = {n["id"] for n in knowledge.get("nodes", [])}

    for effort in efforts:
        eid = effort["id"]
        if eid in existing_ids:
            continue  # Already migrated

        node = {
            "id": eid,
            "type": "effort",
            "status": effort.get("status", "open"),
            "summary": effort.get("summary"),
            "raw_file": effort.get("raw_file", f"efforts/{eid}.jsonl"),
            "created": effort.get("created"),
            "updated": effort.get("updated"),
        }
        # Preserve effort-specific fields
        if effort.get("active") is not None:
            node["active"] = effort["active"]

        knowledge["nodes"].append(node)

    _save_knowledge(session_dir, knowledge)
    manifest_path.rename(session_dir / "manifest.yaml.bak")


# === Effort helpers (unified store) ===

def _load_efforts(session_dir: Path) -> list[dict]:
    """Load effort nodes from knowledge.yaml, migrating manifest.yaml if needed.

    Returns list of effort dicts in manifest-compatible format.
    """
    manifest_path = session_dir / "manifest.yaml"
    if manifest_path.exists():
        _migrate_manifest_to_knowledge(session_dir)

    knowledge = _load_knowledge(session_dir)
    efforts = []
    for node in knowledge.get("nodes", []):
        if node.get("type") == "effort":
            effort = {
                "id": node["id"],
                "status": node.get("status", "open"),
                "summary": node.get("summary"),
                "raw_file": node.get("raw_file", f"efforts/{node['id']}.jsonl"),
                "created": node.get("created"),
                "updated": node.get("updated"),
            }
            if "active" in node:
                effort["active"] = node["active"]
            if node.get("description"):
                effort["description"] = node["description"]
            if node.get("provenance_uri"):
                effort["provenance_uri"] = node["provenance_uri"]
            efforts.append(effort)
    return efforts


def _save_efforts(session_dir: Path, efforts: list[dict]):
    """Save effort list back to knowledge.yaml, preserving non-effort nodes."""
    knowledge = _load_knowledge(session_dir)

    # Keep all non-effort nodes
    non_effort_nodes = [n for n in knowledge.get("nodes", []) if n.get("type") != "effort"]

    # Convert efforts to nodes
    effort_nodes = []
    for effort in efforts:
        node = {
            "id": effort["id"],
            "type": "effort",
            "status": effort.get("status", "open"),
            "summary": effort.get("summary"),
            "raw_file": effort.get("raw_file", f"efforts/{effort['id']}.jsonl"),
            "created": effort.get("created"),
            "updated": effort.get("updated"),
        }
        if "active" in effort:
            node["active"] = effort["active"]
        if effort.get("description"):
            node["description"] = effort["description"]
        if effort.get("provenance_uri"):
            node["provenance_uri"] = effort["provenance_uri"]
        effort_nodes.append(node)

    knowledge["nodes"] = non_effort_nodes + effort_nodes
    _save_knowledge(session_dir, knowledge)


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

    # Preserve summary_last_referenced_turn across saves
    existing_slrt = existing.get("summary_last_referenced_turn", {})

    data = {
        "expanded": list(expanded_set),
        "expanded_at": expanded_at,
        "last_referenced_turn": lrt,
        "summary_last_referenced_turn": existing_slrt,
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


def increment_session_count(session_dir: Path) -> int:
    """Increment the session count (number of CLI launches). Returns the new count."""
    state = _load_session_state(session_dir)
    state["session_count"] = state.get("session_count", 0) + 1
    _save_session_state(session_dir, state)
    return state["session_count"]


# === Summary reference tracking (for summary eviction) ===

def _load_summary_references(session_dir: Path) -> dict[str, int]:
    """Load summary_last_referenced_turn from expanded.json."""
    state = _load_expanded_state(session_dir)
    return state.get("summary_last_referenced_turn", {})


# === Knowledge graph (nodes + edges) ===

def _load_knowledge(session_dir: Path) -> dict:
    """Load knowledge.yaml, returning empty structure if missing."""
    path = session_dir / "knowledge.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {"nodes": [], "edges": []}
    return {"nodes": [], "edges": []}


def _save_knowledge(session_dir: Path, knowledge: dict):
    """Write knowledge.yaml."""
    path = session_dir / "knowledge.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(knowledge, f, default_flow_style=False)


def _save_summary_references(session_dir: Path, refs: dict[str, int]):
    """Update summary_last_referenced_turn in expanded.json (merge, don't overwrite)."""
    expanded_path = session_dir / "expanded.json"
    expanded_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_expanded_state(session_dir)
    existing["summary_last_referenced_turn"] = refs
    expanded_path.write_text(json.dumps(existing), encoding="utf-8")


# === Knowledge reference tracking (for knowledge eviction) ===

def _load_knowledge_references(session_dir: Path) -> dict[str, int]:
    """Load knowledge_last_referenced_turn from session_state.json."""
    state = _load_session_state(session_dir)
    return state.get("knowledge_last_referenced_turn", {})


def _save_knowledge_references(session_dir: Path, refs: dict[str, int]):
    """Update knowledge_last_referenced_turn in session_state.json."""
    state = _load_session_state(session_dir)
    state["knowledge_last_referenced_turn"] = refs
    _save_session_state(session_dir, state)


# === Expanded knowledge state (which knowledge nodes have context loaded) ===

def _load_expanded_knowledge(session_dir: Path) -> set:
    """Load the set of currently expanded knowledge node IDs from expanded.json."""
    state = _load_expanded_state(session_dir)
    return set(state.get("expanded_knowledge", []))


def _save_expanded_knowledge(session_dir: Path, node_id_set: set, last_expanded_turn: dict | None = None):
    """Save the set of expanded knowledge node IDs to expanded.json.

    Preserves existing expanded_knowledge_at timestamps for nodes that were already expanded.
    Updates knowledge_last_expanded_turn if provided.
    """
    expanded_path = session_dir / "expanded.json"
    expanded_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat()

    # Load existing state to preserve timestamps and other fields
    existing = _load_expanded_state(session_dir)

    # Build expanded_knowledge_at: keep existing timestamps, add new ones
    existing_at = existing.get("expanded_knowledge_at", {})
    expanded_at = {}
    for nid in node_id_set:
        expanded_at[nid] = existing_at.get(nid, now)

    # Build knowledge_last_expanded_turn: merge provided over existing, prune removed
    existing_let = existing.get("knowledge_last_expanded_turn", {})
    let = last_expanded_turn if last_expanded_turn is not None else existing_let
    let = {nid: let[nid] for nid in node_id_set if nid in let}

    # Update only the knowledge-related keys, preserving everything else
    existing["expanded_knowledge"] = list(node_id_set)
    existing["expanded_knowledge_at"] = expanded_at
    existing["knowledge_last_expanded_turn"] = let

    expanded_path.write_text(json.dumps(existing), encoding="utf-8")
