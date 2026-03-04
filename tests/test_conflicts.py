"""Tests for conflict resolution: report generation, resolution, auto-resolve.

All tests are graph-based — zero LLM calls.
"""

import pytest
from pathlib import Path

from oi.conflicts import (
    generate_conflict_report,
    resolve_conflict,
    auto_resolve,
    _classify_conflict,
)
from oi.state import _load_knowledge, _save_knowledge


# --- Helpers ---

def _make_node(nid, ntype="fact", status="active", **extra):
    node = {"id": nid, "type": ntype, "status": status, "summary": f"Summary for {nid}"}
    node.update(extra)
    return node


def _make_edge(src, tgt, etype, **extra):
    edge = {"source": src, "target": tgt, "type": etype}
    edge.update(extra)
    return edge


def _setup_graph(tmp_path, nodes, edges):
    """Write a knowledge.yaml with given nodes and edges, return session_dir."""
    knowledge = {"nodes": nodes, "edges": edges}
    _save_knowledge(tmp_path, knowledge)
    return tmp_path


# === Report generation tests (8) ===

class TestClassifyConflict:
    """Tests for _classify_conflict priority logic."""

    def test_facts_3x_winner_strong_recommendation(self):
        """Two facts, winner has 3x supports → strong_recommendation."""
        priority, winner = _classify_conflict(3, 1, False, "a", "b")
        assert priority == "strong_recommendation"
        assert winner == "a"

    def test_facts_5x_winner_auto_resolvable(self):
        """Two facts, winner has ≥5x supports → auto_resolvable."""
        priority, winner = _classify_conflict(5, 1, False, "a", "b")
        assert priority == "auto_resolvable"
        assert winner == "a"

    def test_decisions_10x_winner_not_auto(self):
        """Two decisions (subjective), 10x winner → strong_recommendation, NOT auto."""
        priority, winner = _classify_conflict(10, 1, True, "a", "b")
        assert priority == "strong_recommendation"
        assert winner == "a"
        # Key assertion: subjective conflicts are never auto_resolvable
        assert priority != "auto_resolvable"

    def test_equal_support_ambiguous(self):
        """Equal supports → ambiguous, no winner."""
        priority, winner = _classify_conflict(3, 3, False, "a", "b")
        assert priority == "ambiguous"
        assert winner is None


class TestGenerateConflictReport:

    def test_filter_by_node_ids(self, tmp_path):
        """Report filters to only conflicts involving specified node_ids."""
        nodes = [
            _make_node("fact-001"),
            _make_node("fact-002"),
            _make_node("fact-003"),
            _make_node("fact-004"),
        ]
        edges = [
            _make_edge("fact-001", "fact-002", "contradicts", reasoning="They disagree"),
            _make_edge("fact-003", "fact-004", "contradicts", reasoning="Also disagree"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        report = generate_conflict_report(tmp_path, node_ids=["fact-001", "fact-002"])
        assert report.total_contradictions == 1
        assert report.conflicts[0].node_a.node_id == "fact-001"

    def test_empty_graph_empty_report(self, tmp_path):
        """Empty graph → empty report with zero counts."""
        _setup_graph(tmp_path, [], [])

        report = generate_conflict_report(tmp_path)
        assert report.total_contradictions == 0
        assert report.auto_resolvable == 0
        assert report.strong_recommendations == 0
        assert report.ambiguous == 0
        assert report.conflicts == []

    def test_stats_match_counts(self, tmp_path):
        """Report stats (auto/strong/ambiguous) match actual conflict counts."""
        nodes = [
            _make_node("fact-001"),
            _make_node("fact-002"),
            _make_node("fact-003"),
            _make_node("fact-004"),
            _make_node("fact-005"),
            _make_node("fact-006"),
            # supporter nodes must exist for PageRank to count them
            *[_make_node(f"s{i}") for i in range(1, 12)],
        ]
        edges = [
            # Pair 1: 5 vs 0 supports → auto_resolvable
            _make_edge("fact-001", "fact-002", "contradicts"),
            _make_edge("s1", "fact-001", "supports"),
            _make_edge("s2", "fact-001", "supports"),
            _make_edge("s3", "fact-001", "supports"),
            _make_edge("s4", "fact-001", "supports"),
            _make_edge("s5", "fact-001", "supports"),
            # Pair 2: 3 vs 1 supports → strong_recommendation
            _make_edge("fact-003", "fact-004", "contradicts"),
            _make_edge("s6", "fact-003", "supports"),
            _make_edge("s7", "fact-003", "supports"),
            _make_edge("s8", "fact-003", "supports"),
            _make_edge("s9", "fact-004", "supports"),
            # Pair 3: equal → ambiguous
            _make_edge("fact-005", "fact-006", "contradicts"),
            _make_edge("s10", "fact-005", "supports"),
            _make_edge("s11", "fact-006", "supports"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        report = generate_conflict_report(tmp_path)
        assert report.total_contradictions == 3
        assert report.auto_resolvable == 1
        assert report.strong_recommendations == 1
        assert report.ambiguous == 1

    def test_decision_vs_fact_is_subjective(self, tmp_path):
        """A decision vs a fact → is_subjective=True."""
        nodes = [
            _make_node("decision-001", ntype="decision"),
            _make_node("fact-001"),
        ]
        edges = [
            _make_edge("decision-001", "fact-001", "contradicts", reasoning="Conflict"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        report = generate_conflict_report(tmp_path)
        assert report.total_contradictions == 1
        assert report.conflicts[0].is_subjective is True


# === Resolution tests (4) ===

class TestResolveConflict:

    def test_creates_supersedes_edge_and_marks_loser(self, tmp_path):
        """resolve_conflict creates supersedes edge and marks loser superseded."""
        nodes = [
            _make_node("fact-001", has_contradiction=True),
            _make_node("fact-002", has_contradiction=True),
        ]
        edges = [
            _make_edge("fact-001", "fact-002", "contradicts"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        result = resolve_conflict(tmp_path, "fact-001", "fact-002", "fact-001 has more support")
        assert result["status"] == "resolved"
        assert result["winner"] == "fact-001"

        # Verify graph state
        knowledge = _load_knowledge(tmp_path)
        loser = next(n for n in knowledge["nodes"] if n["id"] == "fact-002")
        assert loser["status"] == "superseded"
        assert loser["superseded_by"] == "fact-001"

        # Verify supersedes edge exists
        sup_edges = [e for e in knowledge["edges"] if e["type"] == "supersedes"]
        assert len(sup_edges) == 1
        assert sup_edges[0]["source"] == "fact-001"
        assert sup_edges[0]["target"] == "fact-002"

    def test_removes_contradicts_edge(self, tmp_path):
        """resolve_conflict removes the contradicts edge between the pair."""
        nodes = [
            _make_node("fact-001", has_contradiction=True),
            _make_node("fact-002", has_contradiction=True),
        ]
        edges = [
            _make_edge("fact-001", "fact-002", "contradicts"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        resolve_conflict(tmp_path, "fact-001", "fact-002", "resolved")

        knowledge = _load_knowledge(tmp_path)
        contradicts = [e for e in knowledge["edges"] if e["type"] == "contradicts"]
        assert len(contradicts) == 0

    def test_cleans_has_contradiction_when_no_remaining(self, tmp_path):
        """Winner's has_contradiction is cleaned when no remaining contradicts edges."""
        nodes = [
            _make_node("fact-001", has_contradiction=True),
            _make_node("fact-002", has_contradiction=True),
        ]
        edges = [
            _make_edge("fact-001", "fact-002", "contradicts"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        resolve_conflict(tmp_path, "fact-001", "fact-002", "resolved")

        knowledge = _load_knowledge(tmp_path)
        winner = next(n for n in knowledge["nodes"] if n["id"] == "fact-001")
        assert "has_contradiction" not in winner

        loser = next(n for n in knowledge["nodes"] if n["id"] == "fact-002")
        assert "has_contradiction" not in loser

    def test_raises_valueerror_for_missing_node(self, tmp_path):
        """resolve_conflict raises ValueError when a node is not found."""
        nodes = [_make_node("fact-001")]
        _setup_graph(tmp_path, nodes, [])

        with pytest.raises(ValueError, match="Node not found: fact-999"):
            resolve_conflict(tmp_path, "fact-001", "fact-999", "doesn't exist")


# === Auto-resolve tests (2) ===

class TestAutoResolve:

    def test_only_resolves_auto_resolvable(self, tmp_path):
        """auto_resolve only resolves auto_resolvable conflicts, skips others."""
        nodes = [
            _make_node("fact-001", has_contradiction=True),
            _make_node("fact-002", has_contradiction=True),
            _make_node("fact-003", has_contradiction=True),
            _make_node("fact-004", has_contradiction=True),
            # supporter nodes must exist for PageRank to count them
            *[_make_node(f"s{i}") for i in range(1, 8)],
        ]
        edges = [
            # Pair 1: 5 vs 0 → auto_resolvable
            _make_edge("fact-001", "fact-002", "contradicts"),
            _make_edge("s1", "fact-001", "supports"),
            _make_edge("s2", "fact-001", "supports"),
            _make_edge("s3", "fact-001", "supports"),
            _make_edge("s4", "fact-001", "supports"),
            _make_edge("s5", "fact-001", "supports"),
            # Pair 2: equal → ambiguous (should NOT be resolved)
            _make_edge("fact-003", "fact-004", "contradicts"),
            _make_edge("s6", "fact-003", "supports"),
            _make_edge("s7", "fact-004", "supports"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        results = auto_resolve(tmp_path)
        assert len(results) == 1
        assert results[0]["status"] == "resolved"
        assert results[0]["winner"] == "fact-001"
        assert results[0]["loser"] == "fact-002"

        # Verify ambiguous pair was NOT resolved
        knowledge = _load_knowledge(tmp_path)
        fact_003 = next(n for n in knowledge["nodes"] if n["id"] == "fact-003")
        assert fact_003["status"] == "active"
        fact_004 = next(n for n in knowledge["nodes"] if n["id"] == "fact-004")
        assert fact_004["status"] == "active"

    def test_no_auto_resolvable_returns_empty(self, tmp_path):
        """When no auto_resolvable conflicts exist, returns empty list."""
        nodes = [
            _make_node("fact-001", has_contradiction=True),
            _make_node("fact-002", has_contradiction=True),
        ]
        edges = [
            # Equal supports → ambiguous
            _make_edge("fact-001", "fact-002", "contradicts"),
            _make_edge("s1", "fact-001", "supports"),
            _make_edge("s2", "fact-002", "supports"),
        ]
        _setup_graph(tmp_path, nodes, edges)

        results = auto_resolve(tmp_path)
        assert results == []
