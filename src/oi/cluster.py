"""Concept node synthesis from embedding clusters.

Finds near-duplicate nodes via cosine similarity on embeddings,
then synthesizes canonical concept (principle) nodes from clusters.
"""

from __future__ import annotations

from pathlib import Path

from .embed import load_embeddings, cosine_similarity
from .llm import chat, DEFAULT_MODEL


def find_clusters(
    session_dir: Path,
    knowledge: dict,
    threshold: float = 0.90,
) -> list[list[str]]:
    """Find clusters of semantically similar fact nodes via embedding similarity.

    Args:
        session_dir: Path to session directory (for loading embeddings).
        knowledge: Knowledge graph dict with 'nodes' and 'edges'.
        threshold: Cosine similarity threshold for clustering (default 0.85).

    Returns:
        List of clusters (each cluster = list of node IDs), sorted by size descending.
        Only clusters with >= 2 members are returned.
        Only 'fact' nodes are clustered.
    """
    emb_data = load_embeddings(session_dir)
    vectors = emb_data.get("vectors", {})

    # Filter to active fact nodes that have embeddings
    active_facts = {
        n["id"] for n in knowledge.get("nodes", [])
        if n.get("status") == "active" and n.get("type") == "fact"
    }
    candidates = {nid: vec for nid, vec in vectors.items() if nid in active_facts}

    if len(candidates) < 2:
        return []

    # Greedy clustering: assign each unassigned node to the first cluster it fits
    node_ids = list(candidates.keys())
    assigned: set[str] = set()
    clusters: list[list[str]] = []

    for i, nid in enumerate(node_ids):
        if nid in assigned:
            continue

        cluster = [nid]
        assigned.add(nid)

        for j in range(i + 1, len(node_ids)):
            other = node_ids[j]
            if other in assigned:
                continue
            sim = cosine_similarity(candidates[nid], candidates[other])
            if sim >= threshold:
                cluster.append(other)
                assigned.add(other)

        if len(cluster) >= 2:
            clusters.append(cluster)

    # Sort by size descending
    clusters.sort(key=len, reverse=True)
    return clusters


def synthesize_concepts(
    clusters: list[list[str]],
    session_dir: Path,
    knowledge: dict,
    model: str = None,
) -> list[dict]:
    """Synthesize principle nodes from clusters of similar fact nodes.

    For each cluster, calls the LLM to produce a canonical concept statement,
    creates a principle node, and links cluster members via exemplifies edges.

    Args:
        clusters: List of clusters from find_clusters().
        session_dir: Path to session directory.
        knowledge: Knowledge graph dict.
        model: LLM model for synthesis. Uses default if None.

    Returns:
        List of {concept_node_id, member_ids, summary} dicts.
    """
    from .knowledge import add_knowledge

    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}
    results = []

    for cluster in clusters:
        # Gather summaries of cluster members
        summaries = []
        for nid in cluster:
            node = nodes_by_id.get(nid)
            if node:
                summaries.append(f"- [{nid}]: {node.get('summary', '')}")

        if len(summaries) < 2:
            continue

        # LLM synthesis
        messages = [
            {
                "role": "system",
                "content": (
                    "You synthesize a single canonical concept statement from "
                    "related claims. Respond with ONLY the concept statement "
                    "(one sentence, no explanation)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"These {len(summaries)} claims express the same or very similar idea. "
                    f"Synthesize a single canonical concept statement:\n\n"
                    + "\n".join(summaries)
                ),
            },
        ]

        try:
            concept_summary = chat(
                messages,
                model=model or DEFAULT_MODEL,
                phase="synthesize",
                log_meta={"cluster_size": len(cluster)},
            ).strip()
        except Exception:
            continue

        if not concept_summary:
            continue

        # Create principle node
        result_json = add_knowledge(
            session_dir,
            node_type="principle",
            summary=concept_summary,
            source="cluster-synthesis",
            instance_count=len(cluster),
            skip_linking=True,
            skip_embed=False,
        )

        import json
        result = json.loads(result_json)
        if "error" in result:
            continue

        concept_id = result["node_id"]

        # Add exemplifies edges from each member to the concept
        from .state import _load_knowledge, _save_knowledge
        from datetime import datetime

        kg = _load_knowledge(session_dir)
        now = datetime.now().isoformat()
        for member_id in cluster:
            kg["edges"].append({
                "source": member_id,
                "target": concept_id,
                "type": "exemplifies",
                "reasoning": f"Cluster member (similarity >= threshold)",
                "created": now,
            })
        _save_knowledge(session_dir, kg)

        results.append({
            "concept_node_id": concept_id,
            "member_ids": cluster,
            "summary": concept_summary,
        })

    return results
