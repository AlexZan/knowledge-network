"""Conflict resolution: analyze contradictions, classify severity, resolve.

Three public functions:
- generate_conflict_report: scan graph for contradictions, classify by priority
- resolve_conflict: supersede the loser, clean up edges/flags
- auto_resolve: batch-resolve all auto_resolvable conflicts

Priority classification uses topology (support counts) as authority.
Decision 015: subjective conflicts need user sign-off; factual conflicts
with overwhelming support can be auto-resolved.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .confidence import compute_confidence, compute_all_confidences
from .state import _load_knowledge, _save_knowledge


# --- Data models ---

class ConflictSide(BaseModel):
    node_id: str
    node_type: str
    summary: str
    confidence: dict


class ConflictPair(BaseModel):
    node_a: ConflictSide
    node_b: ConflictSide
    reasoning: str
    priority: Literal["auto_resolvable", "strong_recommendation", "ambiguous"]
    recommended_winner: str | None
    is_subjective: bool


class ConflictReport(BaseModel):
    total_contradictions: int
    auto_resolvable: int
    strong_recommendations: int
    ambiguous: int
    conflicts: list[ConflictPair]
    depth: int | None = None
    damping: float = 0.85
    iterations: int = 0
    runtime_ms: float = 0.0


# --- Internal helpers ---

SUBJECTIVE_TYPES = {"decision", "preference"}


def _classify_conflict(
    sup_a: int,
    sup_b: int,
    is_subjective: bool,
    id_a: str,
    id_b: str,
) -> tuple[Literal["auto_resolvable", "strong_recommendation", "ambiguous"], str | None]:
    """Classify a contradiction pair by priority. Returns (priority, recommended_winner)."""
    # Determine winner/loser by support count
    if sup_a == sup_b:
        return "ambiguous", None

    if sup_a > sup_b:
        winner_id, winner_sup, loser_sup = id_a, sup_a, sup_b
    else:
        winner_id, winner_sup, loser_sup = id_b, sup_b, sup_a

    # Avoid div-by-zero: treat 0 supports as 1 for ratio
    effective_loser = max(loser_sup, 1)
    ratio = winner_sup / effective_loser

    if is_subjective:
        # Subjective: never auto_resolvable
        if ratio >= 3:
            return "strong_recommendation", winner_id
        return "ambiguous", winner_id
    else:
        # Factual: can be auto_resolvable
        if ratio >= 5:
            return "auto_resolvable", winner_id
        if ratio >= 2:
            return "strong_recommendation", winner_id
        return "ambiguous", winner_id


# --- Public API ---

def generate_conflict_report(
    session_dir: Path,
    node_ids: list[str] | None = None,
    depth: int | None = None,
    damping: float = 0.85,
) -> ConflictReport:
    """Analyze all contradictions in the graph. Returns a structured report."""
    knowledge = _load_knowledge(session_dir)
    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}
    edges = knowledge.get("edges", [])

    # Compute weighted confidence once for the whole graph
    all_conf = compute_all_confidences(knowledge, depth=depth, damping=damping)
    _iters = next(iter(all_conf.values()), {}).get("iterations", 0) if all_conf else 0
    _runtime = next(iter(all_conf.values()), {}).get("runtime_ms", 0.0) if all_conf else 0.0

    # Find all contradicts edges (deduplicate pairs)
    seen_pairs: set[tuple[str, str]] = set()
    conflicts: list[ConflictPair] = []

    for edge in edges:
        if edge["type"] != "contradicts":
            continue

        a_id, b_id = edge["source"], edge["target"]

        # Filter by node_ids if provided
        if node_ids is not None:
            if a_id not in node_ids and b_id not in node_ids:
                continue

        # Deduplicate: normalize pair order
        pair_key = (min(a_id, b_id), max(a_id, b_id))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        node_a = nodes_by_id.get(a_id)
        node_b = nodes_by_id.get(b_id)
        if not node_a or not node_b:
            continue

        # Skip superseded nodes
        if node_a.get("status") == "superseded" or node_b.get("status") == "superseded":
            continue

        type_a = node_a.get("type", "fact")
        type_b = node_b.get("type", "fact")
        is_subjective = type_a in SUBJECTIVE_TYPES or type_b in SUBJECTIVE_TYPES

        conf_a = all_conf.get(a_id, {"level": "low", "inbound_supports": 0.0, "inbound_contradicts": 0.0, "independent_sources": 0})
        conf_b = all_conf.get(b_id, {"level": "low", "inbound_supports": 0.0, "inbound_contradicts": 0.0, "independent_sources": 0})
        sup_a = conf_a["inbound_supports"]
        sup_b = conf_b["inbound_supports"]

        priority, recommended_winner = _classify_conflict(
            sup_a, sup_b, is_subjective, a_id, b_id
        )

        conflicts.append(ConflictPair(
            node_a=ConflictSide(
                node_id=a_id,
                node_type=type_a,
                summary=node_a.get("summary", ""),
                confidence=conf_a,
            ),
            node_b=ConflictSide(
                node_id=b_id,
                node_type=type_b,
                summary=node_b.get("summary", ""),
                confidence=conf_b,
            ),
            reasoning=edge.get("reasoning", ""),
            priority=priority,
            recommended_winner=recommended_winner,
            is_subjective=is_subjective,
        ))

    return ConflictReport(
        total_contradictions=len(conflicts),
        auto_resolvable=sum(1 for c in conflicts if c.priority == "auto_resolvable"),
        strong_recommendations=sum(1 for c in conflicts if c.priority == "strong_recommendation"),
        ambiguous=sum(1 for c in conflicts if c.priority == "ambiguous"),
        conflicts=conflicts,
        depth=depth,
        damping=damping,
        iterations=_iters,
        runtime_ms=_runtime,
    )


def resolve_conflict(
    session_dir: Path,
    winning_id: str,
    losing_id: str,
    reason: str,
) -> dict:
    """Supersede the loser, clean up edges/flags. Returns result dict."""
    knowledge = _load_knowledge(session_dir)
    nodes_by_id = {n["id"]: n for n in knowledge.get("nodes", [])}
    now = datetime.now().isoformat()

    winner = nodes_by_id.get(winning_id)
    loser = nodes_by_id.get(losing_id)
    if not winner:
        raise ValueError(f"Node not found: {winning_id}")
    if not loser:
        raise ValueError(f"Node not found: {losing_id}")

    # 1. Mark loser superseded
    loser["status"] = "superseded"
    loser["superseded_by"] = winning_id
    loser["updated"] = now

    # 2. Add supersedes edge (winner → loser)
    knowledge["edges"].append({
        "source": winning_id,
        "target": losing_id,
        "type": "supersedes",
        "reasoning": reason,
        "created": now,
    })

    # 3. Remove all contradicts edges between the pair
    remaining_edges = []
    for edge in knowledge["edges"]:
        if edge["type"] == "contradicts":
            if (edge["source"] == winning_id and edge["target"] == losing_id) or \
               (edge["source"] == losing_id and edge["target"] == winning_id):
                continue
        remaining_edges.append(edge)
    knowledge["edges"] = remaining_edges

    # 4. Clean has_contradiction on loser (always — it's superseded)
    loser.pop("has_contradiction", None)

    # 5. Clean has_contradiction on winner only if no remaining contradicts edges
    still_contested = any(
        e["type"] == "contradicts" and
        (e["source"] == winning_id or e["target"] == winning_id)
        for e in knowledge["edges"]
    )
    if not still_contested:
        winner.pop("has_contradiction", None)

    _save_knowledge(session_dir, knowledge)

    return {
        "status": "resolved",
        "winner": winning_id,
        "loser": losing_id,
        "reason": reason,
    }


def auto_resolve(
    session_dir: Path,
    report: ConflictReport | None = None,
) -> list[dict]:
    """Batch-resolve all auto_resolvable conflicts. Returns list of results."""
    if report is None:
        report = generate_conflict_report(session_dir)

    results = []
    for conflict in report.conflicts:
        if conflict.priority != "auto_resolvable":
            continue
        if conflict.recommended_winner is None:
            continue

        winner_id = conflict.recommended_winner
        loser_id = (
            conflict.node_b.node_id
            if winner_id == conflict.node_a.node_id
            else conflict.node_a.node_id
        )

        try:
            result = resolve_conflict(
                session_dir,
                winning_id=winner_id,
                losing_id=loser_id,
                reason=f"Auto-resolved: overwhelming topological support ({conflict.node_a.node_id} vs {conflict.node_b.node_id})",
            )
            results.append(result)
        except (ValueError, KeyError) as exc:
            results.append({
                "status": "error",
                "winner": winner_id,
                "loser": loser_id,
                "error": str(exc),
            })

    return results
