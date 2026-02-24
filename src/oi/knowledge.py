"""Knowledge graph mutation operations.

Extracted from tools.py — add_knowledge is the primary entry point for
creating nodes and auto-linking them into the knowledge graph.
"""

import json
from pathlib import Path
from datetime import datetime

from .state import _load_knowledge, _save_knowledge


def add_knowledge(
    session_dir: Path,
    node_type: str,
    summary: str,
    source: str = None,
    related_to: list = None,
    edge_type: str = "supports",
    model: str = None,
) -> str:
    """Add a fact, preference, or decision to the knowledge graph. Returns JSON result."""
    from .llm import DEFAULT_MODEL
    from .confidence import compute_confidence

    knowledge = _load_knowledge(session_dir)

    # Generate ID: type-NNN where NNN is max existing + 1
    existing_ids = [n["id"] for n in knowledge["nodes"] if n["id"].startswith(f"{node_type}-")]
    counter = len(existing_ids) + 1
    node_id = f"{node_type}-{counter:03d}"
    now = datetime.now().isoformat()

    node = {
        "id": node_id,
        "type": node_type,
        "summary": summary,
        "raw_file": None,
        "status": "active",
        "source": source,
        "created": now,
        "updated": now,
    }
    knowledge["nodes"].append(node)

    # Add edges if related_to provided (manual edges)
    if related_to:
        for target_id in related_to:
            knowledge["edges"].append({
                "source": node_id,
                "target": target_id,
                "type": edge_type,
                "created": now,
            })

    # Auto-linking: find candidates and classify relationships
    auto_edges = []
    try:
        from .linker import run_linking
        link_results = run_linking(node, knowledge, model=model or DEFAULT_MODEL)
        existing_targets = {e["target"] for e in knowledge["edges"] if e["source"] == node_id}
        for lr in link_results:
            if lr["target_id"] not in existing_targets:
                knowledge["edges"].append({
                    "source": node_id,
                    "target": lr["target_id"],
                    "type": lr["edge_type"],
                    "reasoning": lr.get("reasoning", ""),
                    "created": now,
                })
                existing_targets.add(lr["target_id"])
                auto_edges.append(lr)
                if lr["edge_type"] == "contradicts":
                    node["has_contradiction"] = True
                    for n in knowledge["nodes"]:
                        if n["id"] == lr["target_id"]:
                            n["has_contradiction"] = True
    except Exception:
        pass  # Best-effort: linking failure doesn't block knowledge addition

    _save_knowledge(session_dir, knowledge)

    result = {"status": "added", "node_id": node_id, "node_type": node_type}
    if auto_edges:
        result["edges_created"] = auto_edges

    # Compute confidence from current graph state
    conf = compute_confidence(node_id, knowledge)
    result["confidence"] = conf

    return json.dumps(result)
