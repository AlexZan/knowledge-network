"""Confidence from topology: compute confidence levels from graph structure.

Pure functions — no persistence. Confidence is computed on-the-fly from edge counts.

Level rules (first match wins):
- contested: inbound_contradicts >= 1 AND inbound_contradicts >= inbound_supports
- high: independent_sources >= 3 AND inbound_supports >= 2
- medium: inbound_supports >= 1 OR independent_sources >= 2
- low: everything else (default for new nodes)

independent_sources: unique `source` values across the node itself + all its inbound supporters.
"""


def compute_confidence(node_id: str, graph: dict) -> dict:
    """Compute confidence level for a single node from graph topology.

    Returns {"level", "inbound_supports", "inbound_contradicts", "independent_sources"}
    Returns level="low" with zeroes if node not found.
    """
    nodes_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    node = nodes_by_id.get(node_id)
    if not node or node.get("status") != "active":
        return {
            "level": "low",
            "inbound_supports": 0,
            "inbound_contradicts": 0,
            "independent_sources": 0,
        }

    edges = graph.get("edges", [])

    # Count inbound edges (target == node_id)
    inbound_supports = 0
    inbound_contradicts = 0
    supporter_ids = []
    for edge in edges:
        if edge["target"] == node_id:
            if edge["type"] == "supports":
                inbound_supports += 1
                supporter_ids.append(edge["source"])
            elif edge["type"] == "exemplifies":
                inbound_supports += 1
                supporter_ids.append(edge["source"])
            elif edge["type"] == "contradicts":
                inbound_contradicts += 1

    # Count independent sources: unique source values from node + active supporters
    sources = set()
    node_source = node.get("source")
    if node_source:
        sources.add(node_source)

    for sid in supporter_ids:
        supporter = nodes_by_id.get(sid)
        if supporter and supporter.get("status") == "active":
            supporter_source = supporter.get("source")
            if supporter_source:
                sources.add(supporter_source)

    independent_sources = len(sources)

    # Apply rules: first match wins
    if inbound_contradicts >= 1 and inbound_contradicts >= inbound_supports:
        level = "contested"
    elif independent_sources >= 3 and inbound_supports >= 2:
        level = "high"
    elif inbound_supports >= 1 or independent_sources >= 2:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "inbound_supports": inbound_supports,
        "inbound_contradicts": inbound_contradicts,
        "independent_sources": independent_sources,
    }


def confidence_annotation(conf: dict) -> str:
    """Format a confidence annotation for display. Returns empty string for low."""
    level = conf.get("level", "low")
    if level == "contested":
        n = conf.get("inbound_contradicts", 0)
        return f"(contested - {n} contradiction{'s' if n != 1 else ''})"
    elif level == "high":
        n = conf.get("independent_sources", 0)
        return f"(high confidence, {n} sources)"
    elif level == "medium":
        n = conf.get("independent_sources", 0)
        return f"(medium confidence, {n} source{'s' if n != 1 else ''})"
    return ""


def compute_all_confidences(graph: dict) -> dict:
    """Compute confidence for all active nodes.

    Returns {node_id: confidence_dict} for each active node.
    """
    result = {}
    for node in graph.get("nodes", []):
        if node.get("status") == "active":
            result[node["id"]] = compute_confidence(node["id"], graph)
    return result
