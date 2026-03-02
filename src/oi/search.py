"""Graph walk search: expand keyword seed matches by traversing edges.

After finding initial seed matches via keyword similarity, walks the graph
1-2 hops outward. Score decays with distance; convergence (multiple paths
reaching the same node) boosts score via additive aggregation.
"""


def _build_adjacency(knowledge: dict) -> dict[str, list[tuple[str, str]]]:
    """Build bidirectional adjacency list from edges.

    Returns {node_id: [(neighbor_id, edge_type), ...]}.
    Supersedes edges only walk toward the newer node (source),
    not back to the old (target).
    """
    adj: dict[str, list[tuple[str, str]]] = {}
    for edge in knowledge.get("edges", []):
        src = edge["source"]
        tgt = edge["target"]
        etype = edge["type"]

        adj.setdefault(src, []).append((tgt, etype))

        # Bidirectional for all types except supersedes
        # For supersedes: src is newer, tgt is older.
        # Walking from old (tgt) → new (src) is allowed.
        # Walking from new (src) → old (tgt) is already added above.
        # But we only want old→new direction, so reverse edge goes tgt→src.
        # Actually: we want to walk TOWARD newer. src supersedes tgt means
        # src is newer. So from tgt we can reach src (walk toward newer).
        # From src we should NOT walk back to tgt (that's toward older).
        # The forward edge src→tgt was added above — we need to REMOVE that
        # for supersedes and only keep the reverse.
        if etype == "supersedes":
            # Remove the forward (new→old) we just added, add reverse (old→new)
            adj[src] = [(n, t) for n, t in adj[src] if not (n == tgt and t == etype)]
            adj.setdefault(tgt, []).append((src, etype))
        else:
            # Normal bidirectional
            adj.setdefault(tgt, []).append((src, etype))

    return adj


def graph_walk(
    seeds: list[dict],
    knowledge: dict,
    max_hops: int = 2,
    hop_1_decay: float = 0.7,
    hop_2_decay: float = 0.4,
) -> list[dict]:
    """Expand seed matches by walking graph edges.

    Args:
        seeds: [{node_id, score}] from keyword matching
        knowledge: full graph (nodes + edges)
        max_hops: how far to walk (1 or 2)
        hop_1_decay: score multiplier for 1-hop neighbors
        hop_2_decay: score multiplier for 2-hop neighbors

    Returns:
        [{node_id, score}] sorted by score descending.
        Includes original seeds with their scores.
    """
    if not seeds:
        return []

    adj = _build_adjacency(knowledge)

    # Collect superseded node IDs to skip
    superseded = {
        n["id"] for n in knowledge.get("nodes", [])
        if n.get("status") == "superseded"
    }

    # Seed scores: keyword matches
    keyword_scores: dict[str, float] = {}
    for s in seeds:
        keyword_scores[s["node_id"]] = s["score"]

    # Walk scores: accumulated from graph traversal
    walk_scores: dict[str, float] = {}

    decay_by_hop = {1: hop_1_decay, 2: hop_2_decay}

    for seed in seeds:
        seed_id = seed["node_id"]
        seed_score = seed["score"]

        # BFS by hop level
        visited = {seed_id}
        current_frontier = [seed_id]

        for hop in range(1, max_hops + 1):
            decay = decay_by_hop.get(hop, 0)
            if decay <= 0:
                break

            next_frontier = []
            for node_id in current_frontier:
                for neighbor_id, _edge_type in adj.get(node_id, []):
                    if neighbor_id in visited:
                        continue
                    if neighbor_id in superseded:
                        continue

                    visited.add(neighbor_id)
                    next_frontier.append(neighbor_id)

                    walk_contribution = seed_score * decay
                    walk_scores[neighbor_id] = walk_scores.get(neighbor_id, 0) + walk_contribution

            current_frontier = next_frontier

    # Aggregate: final_score = max(keyword_score, 0) + sum(walk_scores)
    all_node_ids = set(keyword_scores.keys()) | set(walk_scores.keys())
    results = []
    for nid in all_node_ids:
        kw = keyword_scores.get(nid, 0)
        wk = walk_scores.get(nid, 0)
        final = kw + wk
        results.append({"node_id": nid, "score": final})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
