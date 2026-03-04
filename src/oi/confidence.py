"""Confidence from topology: PageRank-style propagation from graph structure.

Pure functions — no persistence. Confidence is computed on-the-fly.

Algorithm:
- Standard PageRank over the full edge graph (supports, contradicts, exemplifies)
- `depth=N`    → run exactly N iterations (whitepaper baseline)
- `depth=None` → run until convergence (max_delta < epsilon, full truth potential)
- Scores are normalized by N so an average node contributes 1.0 to weighted counts
  (preserves existing level thresholds: >= 1 for medium, >= 2 for high)

Level rules (first match wins, over weighted float counts):
- contested: weighted_contradicts >= 1.0 AND >= weighted_supports
- high: independent_sources >= 3 AND weighted_supports >= 2.0
- medium: weighted_supports >= 1.0 OR independent_sources >= 2
- low: everything else

independent_sources: unique `source` values across the node + its inbound supporters.
"""

import time


def compute_all_confidences(
    graph: dict,
    depth: int | None = None,
    damping: float = 0.85,
    epsilon: float = 1e-6,
    max_iter: int = 100,
) -> dict:
    """Compute PageRank-weighted confidence for all active nodes.

    Args:
        graph: Knowledge graph dict with 'nodes' and 'edges'.
        depth: Number of iterations. None = run until convergence.
        damping: PageRank damping factor (default 0.85).
        epsilon: Convergence threshold (only used when depth=None).
        max_iter: Hard cap on iterations when depth=None.

    Returns:
        {node_id: {"level", "score", "inbound_supports", "inbound_contradicts",
                   "independent_sources", "iterations", "runtime_ms"}}
    """
    t0 = time.monotonic()

    active_nodes = [n for n in graph.get("nodes", []) if n.get("status") == "active"]
    node_ids = [n["id"] for n in active_nodes]
    N = len(node_ids)

    if N == 0:
        return {}

    node_id_set = set(node_ids)
    edges = graph.get("edges", [])

    # Build adjacency index once — O(E)
    inbound: dict[str, list[tuple[str, str]]] = {nid: [] for nid in node_ids}
    outbound_count: dict[str, int] = {nid: 0 for nid in node_ids}

    for edge in edges:
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in node_id_set and tgt in node_id_set:
            inbound[tgt].append((src, edge["type"]))
            outbound_count[src] += 1

    # PageRank initialisation
    scores: dict[str, float] = {nid: 1.0 / N for nid in node_ids}
    teleport = (1.0 - damping) / N

    limit = depth if depth is not None else max_iter
    actual_iters = 0

    for _ in range(limit):
        actual_iters += 1
        new_scores: dict[str, float] = {}
        for nid in node_ids:
            rank = teleport
            for src, _ in inbound[nid]:
                out = outbound_count[src]
                rank += damping * scores[src] / (out if out > 0 else 1)
            new_scores[nid] = rank

        if depth is None:
            delta = max(abs(new_scores[nid] - scores[nid]) for nid in node_ids)
            scores = new_scores
            if delta < epsilon:
                break
        else:
            scores = new_scores

    runtime_ms = (time.monotonic() - t0) * 1000

    # Normalization base: score of a node with no inbound edges at convergence.
    # Using this means an average/isolated node always contributes exactly 1.0,
    # and well-cited nodes contribute proportionally more. Graph-size independent.
    baseline = teleport  # == (1 - damping) / N

    # Compute weighted confidence per node
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    result = {}

    for nid in node_ids:
        node = nodes_by_id[nid]
        weighted_supports = 0.0
        weighted_contradicts = 0.0
        supporter_ids: list[str] = []

        for src, etype in inbound[nid]:
            contribution = scores[src] / baseline
            if etype in ("supports", "exemplifies"):
                weighted_supports += contribution
                supporter_ids.append(src)
            elif etype == "contradicts":
                weighted_contradicts += contribution

        # Independent sources: unique source values from node + active supporters
        sources: set[str] = set()
        if node.get("source"):
            sources.add(node["source"])
        for sid in supporter_ids:
            supporter = nodes_by_id.get(sid)
            if supporter and supporter.get("status") == "active" and supporter.get("source"):
                sources.add(supporter["source"])
        independent_sources = len(sources)

        # Level rules (first match wins)
        if weighted_contradicts >= 1.0 and weighted_contradicts >= weighted_supports:
            level = "contested"
        elif independent_sources >= 3 and weighted_supports >= 2.0:
            level = "high"
        elif weighted_supports >= 1.0 or independent_sources >= 2:
            level = "medium"
        else:
            level = "low"

        result[nid] = {
            "level": level,
            "score": scores[nid],
            "inbound_supports": weighted_supports,
            "inbound_contradicts": weighted_contradicts,
            "independent_sources": independent_sources,
            "iterations": actual_iters,
            "runtime_ms": runtime_ms,
        }

    return result


def compute_confidence(
    node_id: str,
    graph: dict,
    depth: int | None = None,
    damping: float = 0.85,
) -> dict:
    """Compute confidence for a single node. Delegates to compute_all_confidences.

    Returns {"level", "score", "inbound_supports", "inbound_contradicts",
             "independent_sources", "iterations", "runtime_ms"}.
    Returns level="low" with zeroes if node not found or inactive.
    """
    all_conf = compute_all_confidences(graph, depth=depth, damping=damping)
    return all_conf.get(node_id, {
        "level": "low",
        "score": 0.0,
        "inbound_supports": 0.0,
        "inbound_contradicts": 0.0,
        "independent_sources": 0,
        "iterations": 0,
        "runtime_ms": 0.0,
    })


def confidence_annotation(conf: dict) -> str:
    """Format a confidence annotation for display. Returns empty string for low."""
    level = conf.get("level", "low")
    if level == "contested":
        n = conf.get("inbound_contradicts", 0)
        # n may now be float
        n_int = int(round(n)) if isinstance(n, float) else n
        return f"(contested - {n_int} contradiction{'s' if n_int != 1 else ''})"
    elif level == "high":
        n = conf.get("independent_sources", 0)
        return f"(high confidence, {n} sources)"
    elif level == "medium":
        n = conf.get("independent_sources", 0)
        return f"(medium confidence, {n} source{'s' if n != 1 else ''})"
    return ""
