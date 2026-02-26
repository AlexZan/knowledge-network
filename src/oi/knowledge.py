"""Knowledge graph operations: query, add, and link nodes.

add_knowledge is the primary entry point for creating nodes and auto-linking
them into the knowledge graph. query_knowledge searches the graph by keyword.
"""

import json
from pathlib import Path
from datetime import datetime

from .state import _load_knowledge, _save_knowledge


def query_knowledge(
    session_dir: Path,
    query: str,
    node_type: str = None,
    min_confidence: str = None,
) -> str:
    """Search the knowledge graph by keyword. Returns JSON with matching nodes."""
    from .confidence import compute_confidence
    from .decay import extract_keywords

    knowledge = _load_knowledge(session_dir)
    active_nodes = [n for n in knowledge.get("nodes", []) if n.get("status") != "superseded"]

    query_kw = extract_keywords(query)
    query_lower = query.lower()

    matches = []
    for node in active_nodes:
        node_kw = extract_keywords(node.get("summary", ""))

        # Match by node ID directly
        if node["id"].lower() in query_lower:
            score = 1.0
        elif not query_kw or not node_kw:
            continue
        else:
            # Jaccard similarity
            intersection = query_kw & node_kw
            union = query_kw | node_kw
            score = len(intersection) / len(union) if union else 0.0
            if score < 0.05:
                continue

        matches.append((node, score))

    # Sort by score descending
    matches.sort(key=lambda m: m[1], reverse=True)

    # Build results with confidence and edges
    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}
    results = []
    for node, score in matches:
        conf = compute_confidence(node["id"], knowledge)

        # Check because_of targets for staleness (1-hop)
        stale_deps = []
        for edge in knowledge.get("edges", []):
            if edge["source"] == node["id"] and edge["type"] == "because_of":
                target = nodes_by_id.get(edge["target"])
                if target:
                    if target.get("status") == "superseded":
                        stale_deps.append({"node_id": target["id"], "reason": "superseded"})
                    elif target.get("has_contradiction"):
                        stale_deps.append({"node_id": target["id"], "reason": "contested"})

        # Cap confidence at medium if stale deps exist (contested overrides)
        if stale_deps and conf.get("level") not in ("contested",):
            if conf.get("level") == "high":
                conf["level"] = "medium"

        # Apply filters
        if node_type and node.get("type") != node_type:
            continue
        if min_confidence:
            level = conf.get("level", "low")
            level_order = {"low": 0, "medium": 1, "high": 2, "contested": 1}
            min_order = {"low": 0, "medium": 1, "high": 2}.get(min_confidence, 0)
            if level_order.get(level, 0) < min_order:
                continue

        # Gather edges for this node
        node_edges = []
        for edge in knowledge.get("edges", []):
            if edge["source"] == node["id"] or edge["target"] == node["id"]:
                node_edges.append({
                    "source": edge["source"],
                    "target": edge["target"],
                    "type": edge["type"],
                })

        entry = {
            "node_id": node["id"],
            "type": node.get("type"),
            "summary": node.get("summary"),
            "source": node.get("source"),
            "confidence": conf,
            "edges": node_edges,
        }
        if stale_deps:
            entry["stale_dependencies"] = stale_deps

        results.append(entry)

    total_active = len(active_nodes)
    return json.dumps({"results": results, "total_active": total_active})


def add_knowledge(
    session_dir: Path,
    node_type: str,
    summary: str,
    source: str = None,
    related_to: list = None,
    edge_type: str = "supports",
    model: str = None,
    supersedes: list = None,
    session_id: str = None,
    abstraction_level: int = None,
    instance_count: int = None,
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
    if session_id:
        node["created_in_session"] = session_id
    if abstraction_level is not None:
        node["abstraction_level"] = abstraction_level
    if instance_count is not None:
        node["instance_count"] = instance_count
    knowledge["nodes"].append(node)

    # Handle supersession: mark old nodes and transfer edges
    superseded_ids = set()
    if supersedes:
        superseded_ids = set(supersedes)
        for old_node in knowledge["nodes"]:
            if old_node["id"] in superseded_ids:
                old_node["status"] = "superseded"
                old_node["superseded_by"] = node_id
                old_node["updated"] = now
                # Create supersedes edge from new → old
                knowledge["edges"].append({
                    "source": node_id,
                    "target": old_node["id"],
                    "type": "supersedes",
                    "created": now,
                })
                # Copy inbound support edges from old node to new node
                for edge in list(knowledge["edges"]):
                    if edge["target"] == old_node["id"] and edge["type"] == "supports":
                        knowledge["edges"].append({
                            "source": edge["source"],
                            "target": node_id,
                            "type": "supports",
                            "created": now,
                        })

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
            # Skip linking against superseded nodes
            if lr["target_id"] in superseded_ids:
                continue
            if lr["target_id"] not in existing_targets:
                knowledge["edges"].append({
                    "source": node_id,
                    "target": lr["target_id"],
                    "type": lr["edge_type"],
                    "reasoning": lr.get("reasoning", ""),
                    "created": now,
                })
                existing_targets.add(lr["target_id"])
                # Include target_summary for contradictions
                if lr["edge_type"] == "contradicts":
                    for n in knowledge["nodes"]:
                        if n["id"] == lr["target_id"]:
                            lr["target_summary"] = n.get("summary", "")
                            break
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
