"""Knowledge graph operations: query, add, and link nodes.

add_knowledge is the primary entry point for creating nodes and auto-linking
them into the knowledge graph. query_knowledge searches the graph by keyword.
"""

import json
from pathlib import Path
from datetime import datetime

from .schemas import get_node_type_names
from .search import graph_walk
from .state import _load_knowledge, _save_knowledge


def query_knowledge(
    session_dir: Path,
    query: str,
    node_type: str = None,
    min_confidence: str = None,
    max_results: int = 10,
    sort_by: str = None,
) -> str:
    """Search the knowledge graph by keyword. Returns JSON with matching nodes.

    Args:
        sort_by: Optional sort order. "salience" sorts by related_to centrality,
                 "confidence" sorts by confidence level. None uses default walk order.
    """
    from .confidence import compute_confidence, compute_salience
    from .decay import extract_keywords

    knowledge = _load_knowledge(session_dir)
    active_nodes = [n for n in knowledge.get("nodes", []) if n.get("status") != "superseded"]

    query_kw = extract_keywords(query)
    query_lower = query.lower()

    # Phase 1: Keyword seed matching
    seeds = []
    for node in active_nodes:
        node_kw = extract_keywords(node.get("summary", ""))

        # Match by node ID directly
        if node["id"].lower() in query_lower:
            score = 1.0
        elif not query_kw or not node_kw:
            continue
        else:
            intersection = query_kw & node_kw
            if not intersection:
                continue
            # Short queries (1-2 keywords): use containment ratio
            # to avoid Jaccard penalizing asymmetric set sizes
            if len(query_kw) <= 2:
                score = len(intersection) / len(query_kw)
            else:
                # Jaccard similarity for longer queries
                union = query_kw | node_kw
                score = len(intersection) / len(union) if union else 0.0
            if score < 0.05:
                continue

        seeds.append({"node_id": node["id"], "score": score})

    # Phase 1b: Semantic seed matching (if embeddings available)
    try:
        from .embed import semantic_search
        sem_results = semantic_search(query, session_dir, knowledge)
        # Merge: semantic seeds add to existing keyword scores
        seed_scores = {s["node_id"]: s["score"] for s in seeds}
        for sr in sem_results:
            nid = sr["node_id"]
            if nid in seed_scores:
                # Boost keyword seed with semantic signal
                seed_scores[nid] = max(seed_scores[nid], sr["score"])
            else:
                seed_scores[nid] = sr["score"]
        seeds = [{"node_id": nid, "score": sc} for nid, sc in seed_scores.items()]
    except Exception:
        pass  # Embedding unavailable — keyword seeds only

    # Phase 2: Graph walk expansion
    walked = graph_walk(seeds, knowledge)

    # Build matches list from walk results
    nodes_by_id_lookup = {n["id"]: n for n in active_nodes}
    matches = []
    for entry in walked:
        node = nodes_by_id_lookup.get(entry["node_id"])
        if node:
            matches.append((node, entry["score"]))

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
        if node.get("reasoning"):
            entry["reasoning"] = node["reasoning"]
        if node.get("provenance_uri"):
            entry["provenance_uri"] = node["provenance_uri"]
        if stale_deps:
            entry["stale_dependencies"] = stale_deps

        results.append(entry)

    # Compute salience and add to results
    salience_scores = compute_salience(knowledge)
    for entry in results:
        entry["salience"] = salience_scores.get(entry["node_id"], 0.0)

    # Sort if requested
    if sort_by == "salience":
        results.sort(key=lambda r: r.get("salience", 0.0), reverse=True)
    elif sort_by == "confidence":
        level_order = {"contested": 0, "low": 1, "medium": 2, "high": 3}
        results.sort(
            key=lambda r: level_order.get(r.get("confidence", {}).get("level", "low"), 0),
            reverse=True,
        )

    total_active = len(active_nodes)
    if max_results and len(results) > max_results:
        results = results[:max_results]
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
    reasoning: str = None,
    provenance_uri: str = None,
    voice: str = None,
    authored_at: str = None,
    skip_linking: bool = False,
    skip_embed: bool = False,
) -> str:
    """Add a knowledge node to the knowledge graph. Returns JSON result."""
    from .llm import DEFAULT_MODEL
    from .confidence import compute_confidence

    valid_types = get_node_type_names()
    if node_type not in valid_types:
        return json.dumps({"error": f"Invalid node_type '{node_type}'. Must be one of: {', '.join(valid_types)}"})

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
    if reasoning:
        node["reasoning"] = reasoning
    if provenance_uri:
        node["provenance_uri"] = provenance_uri
    if voice and voice != "first_person":
        node["voice"] = voice
    if authored_at:
        node["authored_at"] = authored_at
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
    if not skip_linking:
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

    # Embed the new node (best-effort)
    if not skip_embed:
        try:
            from .embed import embed_node, load_embeddings, save_embeddings, DEFAULT_EMBED_MODEL
            vec = embed_node(node, DEFAULT_EMBED_MODEL)
            if vec:
                emb_data = load_embeddings(session_dir)
                if emb_data["model"] and emb_data["model"] != DEFAULT_EMBED_MODEL:
                    emb_data = {"model": DEFAULT_EMBED_MODEL, "vectors": {}}
                emb_data["model"] = DEFAULT_EMBED_MODEL
                emb_data["vectors"][node_id] = vec
                save_embeddings(session_dir, emb_data)
        except Exception:
            pass  # Embedding failure doesn't block node addition

    result = {"status": "added", "node_id": node_id, "node_type": node_type, "summary": summary}
    if reasoning:
        result["reasoning"] = reasoning
    if provenance_uri:
        result["provenance_uri"] = provenance_uri
    if auto_edges:
        result["edges_created"] = auto_edges

    # Compute confidence from current graph state
    conf = compute_confidence(node_id, knowledge)
    result["confidence"] = conf

    return json.dumps(result)


def remove_edge(
    session_dir: Path,
    source_id: str,
    target_id: str,
    edge_type: str = None,
) -> str:
    """Remove an edge from the knowledge graph. Returns JSON result."""
    knowledge = _load_knowledge(session_dir)

    original_count = len(knowledge["edges"])
    remaining = []
    removed = []
    for edge in knowledge["edges"]:
        if edge["source"] == source_id and edge["target"] == target_id:
            if edge_type is None or edge["type"] == edge_type:
                removed.append(edge)
                continue
        remaining.append(edge)

    if not removed:
        return json.dumps({"error": f"No edge found from {source_id} to {target_id}"
                           + (f" of type '{edge_type}'" if edge_type else "")})

    knowledge["edges"] = remaining

    # Clear has_contradiction flags if no contradicts edges remain
    for node in knowledge["nodes"]:
        if node["id"] in (source_id, target_id) and node.get("has_contradiction"):
            still_contested = any(
                e["type"] == "contradicts" and
                (e["source"] == node["id"] or e["target"] == node["id"])
                for e in remaining
            )
            if not still_contested:
                del node["has_contradiction"]

    _save_knowledge(session_dir, knowledge)

    return json.dumps({
        "status": "removed",
        "removed_count": len(removed),
        "edges_removed": [{"source": e["source"], "target": e["target"], "type": e["type"]} for e in removed],
    })


def reclassify_edge(
    session_dir: Path,
    source_id: str,
    target_id: str,
    old_type: str,
    new_type: str,
    reasoning: str,
    review_text: str = "",
    review_filename: str = "",
) -> str:
    """Reclassify an edge (e.g. contradicts → related_to) with review provenance.

    Saves a raw review excerpt to {session_dir}/reviews/{review_filename}
    and links it as provenance on the reclassified edge.

    Args:
        session_dir: Path to the session/knowledge directory.
        source_id: Source node ID of the edge.
        target_id: Target node ID of the edge.
        old_type: Current edge type to match (e.g. "contradicts").
        new_type: New edge type (e.g. "related_to").
        reasoning: Summary of why this reclassification was made.
        review_text: Raw chat excerpt for provenance (written to reviews/ dir).
        review_filename: Filename for the review excerpt. Auto-generated if empty.

    Returns:
        JSON string with result.
    """
    knowledge = _load_knowledge(session_dir)
    now = datetime.now().isoformat()

    # Find the edge (check both directions for undirected edge types)
    found = None
    for edge in knowledge["edges"]:
        if edge.get("type") != old_type:
            continue
        if (edge["source"] == source_id and edge["target"] == target_id) or \
           (edge["source"] == target_id and edge["target"] == source_id):
            found = edge
            break

    if not found:
        return json.dumps({"error": f"No {old_type} edge found between {source_id} and {target_id}"})

    # Save review provenance file
    provenance_uri = ""
    if review_text:
        reviews_dir = session_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        if not review_filename:
            review_filename = f"{source_id}-{target_id}.md"
        review_path = reviews_dir / review_filename
        review_path.write_text(review_text, encoding="utf-8")
        provenance_uri = f"review://{review_filename}"

    # Reclassify
    old_reasoning = found.get("reasoning", "")
    found["type"] = new_type
    found["reasoning"] = reasoning
    found["reviewed_at"] = now
    if provenance_uri:
        found["provenance_uri"] = provenance_uri

    # Clean has_contradiction flags if old_type was contradicts
    if old_type == "contradicts":
        for node in knowledge["nodes"]:
            if node["id"] in (source_id, target_id) and node.get("has_contradiction"):
                still_contested = any(
                    e["type"] == "contradicts" and
                    (e["source"] == node["id"] or e["target"] == node["id"])
                    for e in knowledge["edges"]
                )
                if not still_contested:
                    del node["has_contradiction"]

    _save_knowledge(session_dir, knowledge)

    return json.dumps({
        "status": "reclassified",
        "source": found["source"],
        "target": found["target"],
        "old_type": old_type,
        "new_type": new_type,
        "reasoning": reasoning,
        "provenance_uri": provenance_uri,
        "reviewed_at": now,
    })


def mark_reviewed(
    session_dir: Path,
    source_id: str,
    target_id: str,
    edge_type: str,
    review_status: str,
    notes: str = "",
    review_text: str = "",
    review_filename: str = "",
    effort: str = "",
) -> str:
    """Annotate an edge as reviewed without changing its type.

    Used when a human reviews a conflict but defers judgment or
    wants to record that they looked at it.

    Args:
        session_dir: Path to the session/knowledge directory.
        source_id: Source node ID of the edge.
        target_id: Target node ID of the edge.
        edge_type: Edge type to match (e.g. "contradicts").
        review_status: One of "deferred", "uncertain", "approved".
        notes: Brief notes on why this status was chosen.
        review_text: Raw chat excerpt for provenance.
        review_filename: Filename for the review excerpt.
        effort: Optional effort name tracking investigation of this edge.

    Returns:
        JSON string with result.
    """
    knowledge = _load_knowledge(session_dir)
    now = datetime.now().isoformat()

    # Find the edge (check both directions)
    found = None
    for edge in knowledge["edges"]:
        if edge.get("type") != edge_type:
            continue
        if (edge["source"] == source_id and edge["target"] == target_id) or \
           (edge["source"] == target_id and edge["target"] == source_id):
            found = edge
            break

    if not found:
        return json.dumps({"error": f"No {edge_type} edge found between {source_id} and {target_id}"})

    # Save review provenance file
    provenance_uri = ""
    if review_text:
        reviews_dir = session_dir / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        if not review_filename:
            review_filename = f"{source_id}-{target_id}-review.md"
        review_path = reviews_dir / review_filename
        review_path.write_text(review_text, encoding="utf-8")
        provenance_uri = f"review://{review_filename}"

    # Annotate edge
    found["reviewed_at"] = now
    found["review_status"] = review_status
    if notes:
        found["review_notes"] = notes
    if provenance_uri:
        found["provenance_uri"] = provenance_uri
    if effort:
        found["effort"] = effort

    _save_knowledge(session_dir, knowledge)

    return json.dumps({
        "status": "reviewed",
        "source": found["source"],
        "target": found["target"],
        "edge_type": edge_type,
        "review_status": review_status,
        "notes": notes,
        "provenance_uri": provenance_uri,
        "reviewed_at": now,
        "effort": effort,
    })
