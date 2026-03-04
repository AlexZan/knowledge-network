"""Pattern detection: distill principles from converging knowledge nodes.

When ≥3 related facts from ≥2 independent sources form a support-connected cluster,
an LLM distills a reusable principle node. Existing principles get updated with new
exemplifying instances.
"""

import json
from pathlib import Path

from .state import _load_knowledge
from .knowledge import add_knowledge

MIN_CLUSTER_SIZE = 3
MIN_INDEPENDENT_SOURCES = 2


def detect_patterns(session_dir: Path, new_node_ids: list[str], model: str) -> list[dict]:
    """Main entry. Returns [{"action": "created"|"updated"|"skipped", "principle_id", "instance_count", "summary"}].
    Best-effort: returns [] on any failure."""
    try:
        results = []
        knowledge = _load_knowledge(session_dir)
        clusters = _build_clusters(new_node_ids, knowledge)

        for cluster in clusters:
            existing = _find_existing_principle(cluster["node_ids"], knowledge)
            if existing:
                r = _update_existing_principle(session_dir, existing, cluster["new_ids"])
                results.append(r)
            else:
                r = _generate_principle(session_dir, cluster["nodes"], model)
                results.append(r)
            # Reload knowledge between iterations (new nodes/edges may have been created)
            knowledge = _load_knowledge(session_dir)

        return results
    except Exception:
        return []


def _build_clusters(new_node_ids: list[str], knowledge: dict) -> list[dict]:
    """Build 1-hop support-connected clusters from new nodes.
    Returns [{"nodes": [...], "node_ids": set, "new_ids": [...], "sources": set}]
    Filters: >= MIN_CLUSTER_SIZE nodes, >= MIN_INDEPENDENT_SOURCES."""
    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", []) if n.get("status") == "active"}
    edges = knowledge.get("edges", [])

    # Build bidirectional adjacency for supports/exemplifies edges
    adjacency = {}
    for edge in edges:
        if edge["type"] in ("supports", "exemplifies"):
            adjacency.setdefault(edge["source"], set()).add(edge["target"])
            adjacency.setdefault(edge["target"], set()).add(edge["source"])

    seen_clusters = set()
    clusters = []

    for nid in new_node_ids:
        if nid not in nodes_by_id:
            continue
        # Cluster = {new_node} ∪ 1-hop neighbors
        neighbors = adjacency.get(nid, set())
        cluster_ids = {nid} | neighbors
        # Only include nodes that exist and are active
        cluster_ids = {cid for cid in cluster_ids if cid in nodes_by_id}

        # Deduplicate by frozenset
        key = frozenset(cluster_ids)
        if key in seen_clusters:
            continue
        seen_clusters.add(key)

        if len(cluster_ids) < MIN_CLUSTER_SIZE:
            continue

        # Collect sources
        sources = set()
        for cid in cluster_ids:
            src = nodes_by_id[cid].get("source")
            if src:
                sources.add(src)

        if len(sources) < MIN_INDEPENDENT_SOURCES:
            continue

        cluster_nodes = [nodes_by_id[cid] for cid in cluster_ids]
        new_ids_in_cluster = [nid2 for nid2 in new_node_ids if nid2 in cluster_ids]
        clusters.append({
            "nodes": cluster_nodes,
            "node_ids": cluster_ids,
            "new_ids": new_ids_in_cluster,
            "sources": sources,
        })

    return clusters


def _find_existing_principle(cluster_node_ids: set, knowledge: dict) -> str | None:
    """Check if any cluster member already has an exemplifies edge to a principle."""
    edges = knowledge.get("edges", [])
    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}

    for edge in edges:
        if edge["type"] == "exemplifies":
            # source exemplifies target — target should be a principle
            if edge["source"] in cluster_node_ids:
                target = nodes_by_id.get(edge["target"])
                if target and target.get("type") == "principle" and target.get("status") == "active":
                    return edge["target"]
            if edge["target"] in cluster_node_ids:
                target = nodes_by_id.get(edge["target"])
                if target and target.get("type") == "principle" and target.get("status") == "active":
                    return edge["target"]
    return None


def _update_existing_principle(session_dir: Path, principle_id: str, new_exemplifying_ids: list[str]) -> dict:
    """Add exemplifies edges from new facts, bump instance_count."""
    knowledge = _load_knowledge(session_dir)
    nodes_by_id = {n["id"]: n for n in knowledge["nodes"]}
    principle = nodes_by_id.get(principle_id)

    if not principle:
        return {"action": "skipped", "principle_id": principle_id, "instance_count": 0, "summary": ""}

    # Add exemplifies edges for new nodes that don't already exemplify this principle
    existing_exemplifiers = set()
    for edge in knowledge["edges"]:
        if edge["type"] == "exemplifies" and edge["target"] == principle_id:
            existing_exemplifiers.add(edge["source"])

    from datetime import datetime
    now = datetime.now().isoformat()
    added_count = 0
    for nid in new_exemplifying_ids:
        if nid not in existing_exemplifiers:
            knowledge["edges"].append({
                "source": nid,
                "target": principle_id,
                "type": "exemplifies",
                "created": now,
            })
            added_count += 1

    # Bump instance_count
    old_count = principle.get("instance_count", 0)
    new_count = old_count + len(new_exemplifying_ids)
    principle["instance_count"] = new_count
    principle["updated"] = now

    from .state import _save_knowledge
    _save_knowledge(session_dir, knowledge)

    return {
        "action": "updated",
        "principle_id": principle_id,
        "instance_count": new_count,
        "summary": principle.get("summary", ""),
    }


def _generate_principle(session_dir: Path, cluster_nodes: list[dict], model: str) -> dict:
    """LLM generates principle, creates node via add_knowledge + exemplifies edges."""
    summaries = [n.get("summary", "") for n in cluster_nodes]
    result = detect_principle(summaries, model)

    if not result or not result.get("summary"):
        return {"action": "skipped", "principle_id": None, "instance_count": 0, "summary": ""}

    # Create principle node
    node_ids = [n["id"] for n in cluster_nodes]
    add_result = json.loads(add_knowledge(
        session_dir,
        "principle",
        result["summary"],
        source="pattern-detection",
        abstraction_level=result.get("abstraction_level", 2),
        instance_count=len(cluster_nodes),
    ))

    if add_result.get("status") != "added":
        return {"action": "skipped", "principle_id": None, "instance_count": 0, "summary": ""}

    principle_id = add_result["node_id"]

    # Add exemplifies edges from cluster nodes to principle
    from datetime import datetime
    from .state import _save_knowledge
    now = datetime.now().isoformat()
    knowledge = _load_knowledge(session_dir)
    for nid in node_ids:
        knowledge["edges"].append({
            "source": nid,
            "target": principle_id,
            "type": "exemplifies",
            "created": now,
        })
    _save_knowledge(session_dir, knowledge)

    return {
        "action": "created",
        "principle_id": principle_id,
        "instance_count": len(cluster_nodes),
        "summary": result["summary"],
    }


def detect_principle(cluster_summaries: list[str], model: str) -> dict | None:
    """LLM call: do these facts converge on a principle?
    Returns {"summary": str, "abstraction_level": int} or None."""
    from .llm import chat

    bullet_list = "\n".join(f"- {s}" for s in cluster_summaries)
    messages = [
        {"role": "system", "content": (
            "You distill general principles from specific observations.\n"
            "Respond ONLY with a JSON object."
        )},
        {"role": "user", "content": (
            "These observations from different contexts point at the same insight:\n"
            f"{bullet_list}\n\n"
            "Rules:\n"
            "- Extract ONE general principle that explains all observations\n"
            "- Self-contained, no pronouns, no context-specific details\n"
            "- Actionable — someone could apply it without knowing the original contexts\n"
            "- abstraction_level: 2 if broadly applicable, 3 if universal\n\n"
            'Response format: {"summary": "...", "abstraction_level": 2}\n'
            'If no common principle: {"summary": null, "abstraction_level": null}'
        )},
    ]

    try:
        raw = chat(messages, model, phase="pattern", log_meta={"fact_count": len(cluster_summaries)})
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            return None
        if not parsed.get("summary"):
            return None
        return {
            "summary": parsed["summary"],
            "abstraction_level": parsed.get("abstraction_level", 2),
        }
    except Exception:
        return None
