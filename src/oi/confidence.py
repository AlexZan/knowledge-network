"""Confidence from topology: PageRank-style propagation from graph structure.

Pure functions — no persistence. Confidence is computed on-the-fly.

Algorithm:
- Standard PageRank over the full edge graph (supports, contradicts, exemplifies)
- `depth=N`    → run exactly N iterations (whitepaper baseline)
- `depth=None` → run until convergence (max_delta < epsilon, full truth potential)
- Scores are normalized by N so an average node contributes 1.0 to weighted counts
  (preserves existing level thresholds: >= 1 for medium, >= 2 for high)

Edge weights (topology-based, no LLM judgment):
- Embedding dissimilarity: high cosine similarity = paraphrase = low weight
- Source independence: same author < different author < different source type
- Combined: weight = dissimilarity_factor * source_factor
- Fallback: 1.0 if no reasoning, 0.5 if reasoning absent (legacy behavior when
  embeddings are unavailable)

Level rules (first match wins, over weighted float counts):
- contested: weighted_contradicts >= 1.0 AND >= weighted_supports
- high: independent_sources >= 3 AND weighted_supports >= 2.0
- medium: weighted_supports >= 1.0 OR independent_sources >= 2
- low: everything else

independent_sources: unique `source` values across the node + its inbound supporters.
"""

import time

from .schemas import get_logical_edge_types


# --- Topology-based edge weight ---

# Cosine similarity above this is considered a paraphrase (near-zero weight)
_COSINE_PARAPHRASE = 0.95
# Below this, content is different enough for full dissimilarity credit
_COSINE_NOVEL = 0.70

# Source independence tiers
_SOURCE_SAME_CONVERSATION = 0.2   # same provenance group
_SOURCE_SAME_AUTHOR = 0.5        # different group, same source
_SOURCE_DIFFERENT = 1.0           # different source entirely


def _compute_edge_weight(
    source_node: dict,
    target_node: dict,
    embeddings: dict | None,
    has_reasoning: bool,
) -> float:
    """Compute edge weight from topology: embedding dissimilarity + source independence.

    Returns a weight between 0.0 and 1.0. Falls back to legacy reasoning-based
    weight (1.0/0.5) when embeddings are unavailable.
    """
    vectors = embeddings.get("vectors", {}) if embeddings else {}
    src_vec = vectors.get(source_node.get("id"))
    tgt_vec = vectors.get(target_node.get("id"))

    # If embeddings are unavailable, fall back to legacy behavior
    if not src_vec or not tgt_vec:
        return 1.0 if has_reasoning else 0.5

    from .embed import cosine_similarity

    # 1. Embedding dissimilarity: linear ramp from 0 at _COSINE_PARAPHRASE to 1 at _COSINE_NOVEL
    cos = cosine_similarity(src_vec, tgt_vec)
    if cos >= _COSINE_PARAPHRASE:
        dissimilarity = 0.0
    elif cos <= _COSINE_NOVEL:
        dissimilarity = 1.0
    else:
        dissimilarity = (_COSINE_PARAPHRASE - cos) / (_COSINE_PARAPHRASE - _COSINE_NOVEL)

    # 2. Source independence
    src_prov = source_node.get("provenance_uri", "")
    tgt_prov = target_node.get("provenance_uri", "")
    src_source = source_node.get("source", "")
    tgt_source = target_node.get("source", "")

    # Strip fragment to get group key
    src_group = src_prov.split("#")[0] if src_prov else ""
    tgt_group = tgt_prov.split("#")[0] if tgt_prov else ""

    if src_group and tgt_group and src_group == tgt_group:
        source_factor = _SOURCE_SAME_CONVERSATION
    elif src_source and tgt_source and src_source == tgt_source:
        source_factor = _SOURCE_SAME_AUTHOR
    else:
        source_factor = _SOURCE_DIFFERENT

    return dissimilarity * source_factor


def compute_all_confidences(
    graph: dict,
    depth: int | None = None,
    damping: float = 0.85,
    epsilon: float = 1e-6,
    max_iter: int = 100,
    embeddings: dict | None = None,
) -> dict:
    """Compute PageRank-weighted confidence for all active nodes.

    Args:
        graph: Knowledge graph dict with 'nodes' and 'edges'.
        depth: Number of iterations. None = run until convergence.
        damping: PageRank damping factor (default 0.85).
        epsilon: Convergence threshold (only used when depth=None).
        max_iter: Hard cap on iterations when depth=None.
        embeddings: Optional {"model": str, "vectors": {node_id: [float]}}.
            When provided, edge weights use topology-based computation
            (embedding dissimilarity + source independence). When None,
            falls back to legacy reasoning-based weight (1.0/0.5).

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
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    logical_types = set(get_logical_edge_types())
    edges = graph.get("edges", [])

    # Build adjacency index once — O(E), logical edges only
    # Each inbound entry: (source_id, edge_type, edge_weight)
    inbound: dict[str, list[tuple[str, str, float]]] = {nid: [] for nid in node_ids}
    outbound_count: dict[str, float] = {nid: 0.0 for nid in node_ids}

    for edge in edges:
        if edge.get("type") not in logical_types:
            continue
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in node_id_set and tgt in node_id_set:
            has_reasoning = bool(edge.get("reasoning"))
            weight = _compute_edge_weight(
                nodes_by_id[src], nodes_by_id[tgt], embeddings, has_reasoning)
            inbound[tgt].append((src, edge["type"], weight))
            outbound_count[src] += weight

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
            for src, _, weight in inbound[nid]:
                out = outbound_count[src]
                rank += damping * (scores[src] * weight) / (out if out > 0 else 1)
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
    result = {}

    for nid in node_ids:
        node = nodes_by_id[nid]
        weighted_supports = 0.0
        weighted_contradicts = 0.0
        supporter_ids: list[str] = []

        for src, etype, weight in inbound[nid]:
            contribution = (scores[src] / baseline) * weight
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
    embeddings: dict | None = None,
) -> dict:
    """Compute confidence for a single node. Delegates to compute_all_confidences.

    Returns {"level", "score", "inbound_supports", "inbound_contradicts",
             "independent_sources", "iterations", "runtime_ms"}.
    Returns level="low" with zeroes if node not found or inactive.
    """
    all_conf = compute_all_confidences(graph, depth=depth, damping=damping, embeddings=embeddings)
    return all_conf.get(node_id, {
        "level": "low",
        "score": 0.0,
        "inbound_supports": 0.0,
        "inbound_contradicts": 0.0,
        "independent_sources": 0,
        "iterations": 0,
        "runtime_ms": 0.0,
    })


def compute_salience(graph: dict) -> dict[str, float]:
    """Compute salience for all active nodes based on related_to edge count.

    Salience measures how central a concept is — nodes with many semantic
    connections (related_to edges) are more salient. Unlike confidence
    (which uses logical edges like supports/contradicts), salience uses
    only related_to edges (bidirectional).

    Returns:
        {node_id: salience_score} where scores are normalized 0.0–1.0.
    """
    active_nodes = [n for n in graph.get("nodes", []) if n.get("status") == "active"]
    node_ids = {n["id"] for n in active_nodes}

    if not node_ids:
        return {}

    # Count related_to edges per node (both directions)
    related_count: dict[str, int] = {nid: 0 for nid in node_ids}
    for edge in graph.get("edges", []):
        if edge.get("type") != "related_to":
            continue
        src, tgt = edge.get("source", ""), edge.get("target", "")
        if src in node_ids:
            related_count[src] += 1
        if tgt in node_ids:
            related_count[tgt] += 1

    max_count = max(related_count.values()) if related_count else 0
    if max_count == 0:
        return {nid: 0.0 for nid in node_ids}

    return {nid: count / max_count for nid, count in related_count.items()}


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
