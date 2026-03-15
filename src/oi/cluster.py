"""Concept node synthesis from embedding clusters.

Finds near-duplicate nodes via cosine similarity on embeddings,
then synthesizes canonical concept (principle) nodes from clusters.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
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
        threshold: Cosine similarity threshold for clustering (default 0.90).

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


def _sanitize_llm_output(text: str) -> str:
    """Strip null bytes and control characters from LLM output."""
    return text.replace("\x00", "").strip()


def synthesize_concepts(
    clusters: list[list[str]],
    session_dir: Path,
    knowledge: dict,
    model: str = None,
    progress_fn=None,
) -> list[dict]:
    """Synthesize principle nodes from clusters of similar fact nodes.

    For each cluster, calls the LLM to produce a canonical concept statement,
    then batch-writes all nodes and exemplifies edges in a single YAML save.

    Args:
        clusters: List of clusters from find_clusters().
        session_dir: Path to session directory.
        knowledge: Knowledge graph dict.
        model: LLM model for synthesis. Uses default if None.
        progress_fn: Optional callback(current, total, concept_summary).

    Returns:
        List of {concept_node_id, member_ids, summary} dicts.
    """
    from .state import _load_knowledge, _save_knowledge

    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}
    results = []
    total = len(clusters)
    consecutive_errors = 0

    # Phase 1: LLM calls (fast, streaming progress)
    for idx, cluster in enumerate(clusters):
        summaries = []
        for nid in cluster:
            node = nodes_by_id.get(nid)
            if node:
                summaries.append(f"- [{nid}]: {node.get('summary', '')}")

        if len(summaries) < 2:
            continue

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
            raw = chat(
                messages,
                model=model or DEFAULT_MODEL,
                phase="synthesize",
                log_meta={"cluster_size": len(cluster)},
            )
            concept_summary = _sanitize_llm_output(raw)
        except Exception as e:
            consecutive_errors += 1
            if progress_fn:
                progress_fn(idx + 1, total, f"ERROR: {e}")
            else:
                print(f"  [{idx+1}/{total}] ERROR: {e}", file=sys.stderr, flush=True)
            if consecutive_errors >= 5:
                if progress_fn:
                    progress_fn(idx + 1, total, "ABORT: 5 consecutive errors")
                else:
                    print(f"  ABORT: {consecutive_errors} consecutive errors", file=sys.stderr, flush=True)
                break
            continue

        if not concept_summary:
            consecutive_errors += 1
            continue

        consecutive_errors = 0

        results.append({
            "member_ids": cluster,
            "summary": concept_summary,
        })

        if progress_fn:
            progress_fn(idx + 1, total, concept_summary[:60])
        else:
            print(f"  [{idx+1}/{total}] ({len(cluster)} members): {concept_summary[:60]}", flush=True)

    # Phase 2: Single batch write (one YAML load/save)
    if results:
        if not progress_fn:
            print(f"  Writing {len(results)} principle nodes...", flush=True)

        kg = _load_knowledge(session_dir)
        now = datetime.now().isoformat()

        # Count existing principle nodes for ID generation
        existing_count = sum(1 for n in kg["nodes"] if n["id"].startswith("principle-"))

        for i, item in enumerate(results):
            concept_id = f"principle-{existing_count + i + 1:03d}"
            item["concept_node_id"] = concept_id

            kg["nodes"].append({
                "id": concept_id,
                "type": "principle",
                "summary": item["summary"],
                "raw_file": None,
                "status": "active",
                "source": "cluster-synthesis",
                "instance_count": len(item["member_ids"]),
                "created": now,
                "updated": now,
            })

            for member_id in item["member_ids"]:
                kg["edges"].append({
                    "source": member_id,
                    "target": concept_id,
                    "type": "exemplifies",
                    "reasoning": "Cluster member (similarity >= threshold)",
                    "created": now,
                })

        _save_knowledge(session_dir, kg)

        if not progress_fn:
            print(f"  Done.", flush=True)

    return results
