"""Node linking: find related knowledge nodes and classify relationships.

Two-stage pipeline:
1. Candidate retrieval via keyword overlap (Jaccard similarity)
2. LLM classification of each pair as supports/contradicts/none
"""

import json

from .decay import extract_keywords
from .llm import chat
from .schemas import get_linkable_edge_types
from .search import graph_walk


def find_candidates(new_node: dict, graph: dict, max_candidates: int = 8) -> list[dict]:
    """Find existing nodes that might relate to the new node.

    Uses keyword overlap (Jaccard similarity) for seed matching,
    then graph walk expansion to discover neighborhood candidates.
    Returns list of candidates sorted by score descending.
    """
    new_keywords = extract_keywords(new_node.get("summary", ""))
    if not new_keywords:
        return []

    # Phase 1: Keyword seed matching
    seeds = []
    for node in graph.get("nodes", []):
        if node["id"] == new_node["id"]:
            continue
        if node.get("status") != "active":
            continue

        node_keywords = extract_keywords(node.get("summary", ""))
        if not node_keywords:
            continue

        intersection = new_keywords & node_keywords
        if not intersection:
            continue
        # Short keyword sets: containment ratio avoids Jaccard penalty
        if len(new_keywords) <= 2:
            score = len(intersection) / len(new_keywords)
        else:
            union = new_keywords | node_keywords
            score = len(intersection) / len(union) if union else 0.0

        if score > 0.1:
            seeds.append({"node_id": node["id"], "score": score})

    if not seeds:
        return []

    # Phase 2: Graph walk expansion
    walked = graph_walk(seeds, graph)

    # Build candidates from walk results
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", []) if n.get("status") == "active"}
    candidates = []
    for entry in walked:
        if entry["node_id"] == new_node["id"]:
            continue
        node = nodes_by_id.get(entry["node_id"])
        if node:
            candidates.append({"node": node, "score": entry["score"]})

    return candidates[:max_candidates]


def link_nodes(new_node: dict, candidate: dict, model: str) -> dict:
    """Compare two nodes and classify their relationship via LLM.

    Returns {"edge_type": "supports"|"contradicts"|"none", "reasoning": "..."}
    Returns {"edge_type": "none", "reasoning": "parse_error"} on any failure.
    """
    try:
        prompt = (
            "Compare these two knowledge nodes and classify their relationship.\n\n"
            f"Node A (new): [{new_node.get('type', '')}] {new_node.get('summary', '')}\n"
            f"Node B (existing): [{candidate.get('type', '')}] {candidate.get('summary', '')}\n\n"
            "Follow these steps:\n"
            "1. Identify the core claim in Node A\n"
            "2. Identify the core claim in Node B\n"
            "3. Are they about the same topic, domain, or system? (e.g. two facts about the same API, library, architecture, or concept count as related) If NO → output \"none\"\n"
            "4. If related: does Node A reinforce, add detail to, provide evidence for, specify an aspect of, or elaborate on Node B? If YES → output \"supports\"\n"
            "5. If related: does Node A disagree with, contradict, or replace Node B? If YES → output \"contradicts\"\n\n"
            "Respond with ONLY a JSON object:\n"
            '{"edge_type": "supports"|"contradicts"|"none", "reasoning": "one sentence"}'
        )

        messages = [
            {"role": "system", "content": "You classify relationships between knowledge nodes. Respond ONLY with JSON."},
            {"role": "user", "content": prompt},
        ]

        raw = chat(messages, model, temperature=0)
        text = raw.strip()

        # Strip markdown fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        result = json.loads(text)

        valid_responses = set(get_linkable_edge_types()) | {"none"}
        if result.get("edge_type") not in valid_responses:
            return {"edge_type": "none", "reasoning": "parse_error"}

        return {
            "edge_type": result["edge_type"],
            "reasoning": result.get("reasoning", ""),
        }
    except Exception:
        return {"edge_type": "none", "reasoning": "parse_error"}


def batch_link_nodes(new_node: dict, candidates: list[dict], model: str) -> list[dict]:
    """Classify relationships between new_node and all candidates in one LLM call.

    Returns list of {target_id, edge_type, reasoning} for each candidate.
    Falls back to per-pair link_nodes on parse failure.
    """
    if not candidates:
        return []
    if len(candidates) == 1:
        result = link_nodes(new_node, candidates[0]["node"], model)
        result["target_id"] = candidates[0]["node"]["id"]
        return [result]

    try:
        candidate_lines = []
        for i, c in enumerate(candidates):
            node = c["node"]
            candidate_lines.append(
                f"  {i+1}. [{node.get('type', '')}] (id: {node['id']}) {node.get('summary', '')}"
            )

        prompt = (
            "Classify the relationship between Node A and each candidate node.\n\n"
            f"Node A (new): [{new_node.get('type', '')}] {new_node.get('summary', '')}\n\n"
            "Candidates:\n"
            + "\n".join(candidate_lines) + "\n\n"
            "For each candidate, follow these steps:\n"
            "1. Are they about the same topic, domain, or system? If NO → \"none\"\n"
            "2. If related: does Node A reinforce, add detail to, provide evidence for, specify an aspect of, or elaborate on the candidate? If YES → \"supports\"\n"
            "3. If related: does Node A disagree with, contradict, or replace the candidate? If YES → \"contradicts\"\n\n"
            "Respond with ONLY a JSON array, one object per candidate in order:\n"
            '[{"edge_type": "supports"|"contradicts"|"none", "reasoning": "one sentence"}, ...]'
        )

        messages = [
            {"role": "system", "content": "You classify relationships between knowledge nodes. Respond ONLY with JSON."},
            {"role": "user", "content": prompt},
        ]

        raw = chat(messages, model, temperature=0)
        text = raw.strip()

        # Strip markdown fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        results = json.loads(text)
        if not isinstance(results, list) or len(results) != len(candidates):
            raise ValueError("batch response length mismatch")

        valid_responses = set(get_linkable_edge_types()) | {"none"}
        parsed = []
        for i, r in enumerate(results):
            edge_type = r.get("edge_type", "none")
            if edge_type not in valid_responses:
                edge_type = "none"
            parsed.append({
                "target_id": candidates[i]["node"]["id"],
                "edge_type": edge_type,
                "reasoning": r.get("reasoning", ""),
            })
        return parsed

    except Exception:
        # Fallback: per-pair classification
        results = []
        for c in candidates:
            result = link_nodes(new_node, c["node"], model)
            result["target_id"] = c["node"]["id"]
            results.append(result)
        return results


def run_linking(new_node: dict, graph: dict, model: str, max_candidates: int = 8) -> list[dict]:
    """Run the full linking pipeline: find candidates then classify all at once.

    Returns list of edges (excluding "none"):
    [{"target_id": str, "edge_type": str, "reasoning": str}, ...]
    """
    candidates = find_candidates(new_node, graph, max_candidates)
    results = batch_link_nodes(new_node, candidates, model)
    return [r for r in results if r["edge_type"] != "none"]
