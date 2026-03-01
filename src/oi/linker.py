"""Node linking: find related knowledge nodes and classify relationships.

Two-stage pipeline:
1. Candidate retrieval via keyword overlap (Jaccard similarity)
2. LLM classification of each pair as supports/contradicts/none
"""

import json

from .decay import extract_keywords
from .llm import chat
from .schemas import get_linkable_edge_types


def find_candidates(new_node: dict, graph: dict, max_candidates: int = 5) -> list[dict]:
    """Find existing nodes that might relate to the new node.

    Uses keyword overlap (Jaccard similarity) between summaries.
    Returns list of candidates sorted by score descending.
    """
    new_keywords = extract_keywords(new_node.get("summary", ""))
    if not new_keywords:
        return []

    candidates = []
    for node in graph.get("nodes", []):
        if node["id"] == new_node["id"]:
            continue
        if node.get("status") != "active":
            continue

        node_keywords = extract_keywords(node.get("summary", ""))
        if not node_keywords:
            continue

        intersection = new_keywords & node_keywords
        union = new_keywords | node_keywords
        score = len(intersection) / len(union) if union else 0.0

        if score > 0.1:
            candidates.append({"node": node, "score": score})

    candidates.sort(key=lambda c: c["score"], reverse=True)
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
            "3. Are they about the same topic or domain? If NO → output \"none\"\n"
            "4. If same topic: does Node A reinforce, add detail to, provide evidence for, or elaborate on Node B? If YES → output \"supports\"\n"
            "5. If same topic: does Node A disagree with, contradict, or replace Node B? If YES → output \"contradicts\"\n\n"
            "Respond with ONLY a JSON object:\n"
            '{"edge_type": "supports"|"contradicts"|"none", "reasoning": "one sentence"}'
        )

        messages = [
            {"role": "system", "content": "You classify relationships between knowledge nodes. Respond ONLY with JSON."},
            {"role": "user", "content": prompt},
        ]

        raw = chat(messages, model)
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


def run_linking(new_node: dict, graph: dict, model: str, max_candidates: int = 5) -> list[dict]:
    """Run the full linking pipeline: find candidates then classify each pair.

    Returns list of edges (excluding "none"):
    [{"target_id": str, "edge_type": str, "reasoning": str}, ...]
    """
    candidates = find_candidates(new_node, graph, max_candidates)
    edges = []
    for c in candidates:
        result = link_nodes(new_node, c["node"], model)
        if result["edge_type"] != "none":
            edges.append({
                "target_id": c["node"]["id"],
                "edge_type": result["edge_type"],
                "reasoning": result["reasoning"],
            })
    return edges
