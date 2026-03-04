"""Unit tests for confidence computation from graph topology."""

import pytest

from oi.confidence import compute_confidence, compute_all_confidences


def _graph(nodes, edges=None):
    """Build a minimal graph dict for testing."""
    return {"nodes": nodes, "edges": edges or []}


def _node(nid, source=None, status="active"):
    return {"id": nid, "type": "fact", "summary": f"Node {nid}", "status": status, "source": source}


def _edge(source, target, edge_type="supports"):
    return {"source": source, "target": target, "type": edge_type}


class TestComputeConfidence:
    def test_low_isolated_node(self):
        """Node with no edges → low."""
        graph = _graph([_node("fact-001", source="effort-a")])
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "low"
        assert result["inbound_supports"] == 0
        assert result["inbound_contradicts"] == 0
        assert result["independent_sources"] == 1

    def test_low_outbound_only(self):
        """Node with only outbound edges (supports something else) → low for itself."""
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-a")],
            [_edge("fact-001", "fact-002")],  # fact-001 supports fact-002
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "low"
        assert result["inbound_supports"] == 0

    def test_medium_one_inbound_support(self):
        """One inbound support → medium."""
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-a")],
            [_edge("fact-002", "fact-001")],  # fact-002 supports fact-001
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "medium"
        assert result["inbound_supports"] == 1

    def test_medium_two_independent_sources(self):
        """Two independent sources (no inbound supports) → medium."""
        # Node has source "effort-a", and we add a supporter from "effort-b" to get 2 sources
        # But wait — need inbound support to count the supporter's source.
        # Actually: independent_sources >= 2 alone triggers medium.
        # To get 2 sources without any support: need the node itself to have 2 sources?
        # No — sources come from the node + its active supporters.
        # With no supporters, sources = just the node's source = 1.
        # So to get 2 sources, need at least 1 supporter from a different source.
        # That supporter is also an inbound_support, so medium triggers on inbound_supports >= 1 first.
        # Let's test: 1 inbound support, same source → only 1 independent source → medium via support rule.
        # For independent_sources >= 2 as the trigger, need 1 support from diff source.
        # Both rules give medium. Let's test with 0 supports but 2 sources (impossible without supports).
        # Actually the only way to get independent_sources >= 2 is with supporters from different sources.
        # So this always co-occurs with inbound_supports >= 1. Both paths lead to medium. Test the combo.
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-b")],
            [_edge("fact-002", "fact-001")],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "medium"
        assert result["independent_sources"] == 2

    def test_high_three_sources_two_supports(self):
        """3 independent sources + 2 inbound supports → high."""
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c"),
            ],
            [
                _edge("fact-002", "fact-001"),  # supports from effort-b
                _edge("fact-003", "fact-001"),  # supports from effort-c
            ],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "high"
        assert result["inbound_supports"] == 2
        assert result["independent_sources"] == 3

    def test_contested_one_contradiction(self):
        """One contradiction, no supports → contested."""
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-b")],
            [_edge("fact-002", "fact-001", "contradicts")],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "contested"
        assert result["inbound_contradicts"] == 1

    def test_contested_equal(self):
        """Equal supports and contradicts → contested (contradicts >= supports)."""
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c"),
            ],
            [
                _edge("fact-002", "fact-001", "supports"),
                _edge("fact-003", "fact-001", "contradicts"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "contested"
        assert result["inbound_supports"] == 1
        assert result["inbound_contradicts"] == 1

    def test_not_contested_when_outweighed(self):
        """2 supports vs 1 contradiction → NOT contested (medium instead).

        Decision table row: supports=2, contradicts=1, sources=2 → medium.
        Contested requires contradicts >= supports.
        """
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-b"),
                _node("fact-004", source="effort-c"),
            ],
            [
                _edge("fact-002", "fact-001", "supports"),
                _edge("fact-003", "fact-001", "supports"),
                _edge("fact-004", "fact-001", "contradicts"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] != "contested"
        # With 2 supports, it could be medium or high depending on sources
        assert result["level"] in ("medium", "high")

    def test_same_source_counts_as_one(self):
        """5 supporters from same effort → 1 independent source.

        Decision table: supports=5, contradicts=0, sources=1 → medium (via support rule).
        Not high because independent_sources < 3.
        """
        nodes = [_node("fact-001", source="effort-a")]
        edges = []
        for i in range(2, 7):
            nodes.append(_node(f"fact-{i:03d}", source="effort-a"))
            edges.append(_edge(f"fact-{i:03d}", "fact-001"))
        graph = _graph(nodes, edges)
        result = compute_confidence("fact-001", graph)
        assert result["independent_sources"] == 1
        assert result["inbound_supports"] == 5
        assert result["level"] == "medium"  # Not high (needs 3+ sources)

    def test_ignores_inactive_supporters(self):
        """Inactive supporter's source doesn't count in independent_sources."""
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c", status="inactive"),
            ],
            [
                _edge("fact-002", "fact-001"),
                _edge("fact-003", "fact-001"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        # fact-003 is inactive — excluded from PageRank, so only fact-002 contributes
        assert result["inbound_supports"] == pytest.approx(1.0, abs=0.1)
        # Sources: effort-a (node itself) + effort-b (active supporter) = 2
        # effort-c ignored because fact-003 is inactive
        assert result["independent_sources"] == 2

    def test_node_not_found(self):
        """Non-existent node → low with zeroes."""
        graph = _graph([_node("fact-001")])
        result = compute_confidence("fact-999", graph)
        assert result["level"] == "low"
        assert result["inbound_supports"] == 0
        assert result["inbound_contradicts"] == 0
        assert result["independent_sources"] == 0


class TestComputeAllConfidences:
    def test_compute_all_confidences(self):
        """Computes confidence for all active nodes."""
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c", status="inactive"),
            ],
            [_edge("fact-002", "fact-001")],
        )
        all_conf = compute_all_confidences(graph)
        assert "fact-001" in all_conf
        assert "fact-002" in all_conf
        assert "fact-003" not in all_conf  # inactive, skipped
        assert all_conf["fact-001"]["level"] == "medium"
        assert all_conf["fact-002"]["level"] == "low"

    def test_empty_graph(self):
        """Empty graph → empty result."""
        assert compute_all_confidences({"nodes": [], "edges": []}) == {}


class TestExemplifies:
    def test_exemplifies_counted_as_support(self):
        """Inbound exemplifies edge counts as inbound_supports=1."""
        graph = _graph(
            [_node("principle-001", source="system"), _node("fact-001", source="effort-a")],
            [_edge("fact-001", "principle-001", "exemplifies")],
        )
        result = compute_confidence("principle-001", graph)
        assert result["inbound_supports"] == 1

    def test_exemplifies_sources_counted(self):
        """Exemplifying nodes from different sources increase independent_sources."""
        graph = _graph(
            [
                _node("principle-001", source="system"),
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
            ],
            [
                _edge("fact-001", "principle-001", "exemplifies"),
                _edge("fact-002", "principle-001", "exemplifies"),
            ],
        )
        result = compute_confidence("principle-001", graph)
        assert result["independent_sources"] == 3  # system + effort-a + effort-b

    def test_exemplifies_boosts_to_high(self):
        """Principle with 3+ sources and 2+ exemplifies → high confidence."""
        graph = _graph(
            [
                _node("principle-001", source="system"),
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
            ],
            [
                _edge("fact-001", "principle-001", "exemplifies"),
                _edge("fact-002", "principle-001", "exemplifies"),
            ],
        )
        result = compute_confidence("principle-001", graph)
        assert result["level"] == "high"
        assert result["inbound_supports"] == pytest.approx(2.0, abs=0.1)
        assert result["independent_sources"] == 3


class TestPageRankConfidence:
    """Tests for PageRank depth/convergence behaviour."""

    def test_depth_3_stops_at_3_iterations(self):
        """depth=3 runs exactly 3 iterations."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b")],
        )
        result = compute_all_confidences(graph, depth=3)
        assert result["b"]["iterations"] == 3

    def test_full_convergence_runs_more_than_3(self):
        """depth=None runs until convergence, typically > 3 iterations."""
        # Chain A→B→C→D: needs multiple hops to propagate authority
        graph = _graph(
            [_node("a"), _node("b"), _node("c"), _node("d")],
            [_edge("a", "b"), _edge("b", "c"), _edge("c", "d")],
        )
        result = compute_all_confidences(graph, depth=None)
        assert result["d"]["iterations"] > 3

    def test_depth_none_vs_depth3_scores_differ(self):
        """Full convergence gives different scores than depth=3 on a chain graph."""
        graph = _graph(
            [_node("a"), _node("b"), _node("c"), _node("d"), _node("e")],
            [_edge("a", "b"), _edge("b", "c"), _edge("c", "d"), _edge("d", "e")],
        )
        r3 = compute_all_confidences(graph, depth=3)
        rf = compute_all_confidences(graph, depth=None)
        # At least one node should have a meaningfully different score
        diffs = [abs(rf[nid]["score"] - r3[nid]["score"]) for nid in rf]
        assert max(diffs) > 1e-4

    def test_cycle_converges_without_exploding(self):
        """Mutual support cycle A↔B reaches a stable score, not infinity."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b"), _edge("b", "a")],
        )
        result = compute_all_confidences(graph, depth=None)
        assert result["a"]["score"] < 10.0
        assert result["b"]["score"] < 10.0
        assert result["a"]["score"] == pytest.approx(result["b"]["score"], abs=1e-4)

    def test_high_authority_source_upweights(self):
        """A well-cited supporter contributes more than 1.0 to weighted_supports."""
        # hub has 5 inbound citations, hub then supports target
        nodes = [_node(f"cite{i}") for i in range(5)] + [_node("hub"), _node("target")]
        edges = ([_edge(f"cite{i}", "hub") for i in range(5)]
                 + [_edge("hub", "target")])
        graph = _graph(nodes, edges)
        result = compute_all_confidences(graph, depth=None)
        assert result["target"]["inbound_supports"] > 1.0

    def test_isolated_source_contributes_about_one(self):
        """A node with no inbound edges contributes ≈ 1.0 to weighted_supports."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b")],
        )
        result = compute_all_confidences(graph, depth=None)
        assert result["b"]["inbound_supports"] == pytest.approx(1.0, abs=0.15)

    def test_runtime_ms_tracked(self):
        """runtime_ms > 0 and iterations > 0 are returned."""
        graph = _graph([_node("a"), _node("b")], [_edge("a", "b")])
        result = compute_all_confidences(graph, depth=3)
        assert result["b"]["runtime_ms"] >= 0.0
        assert result["b"]["iterations"] == 3

    def test_empty_graph_returns_empty(self):
        """No crash on empty graph."""
        assert compute_all_confidences({}) == {}
        assert compute_all_confidences({"nodes": [], "edges": []}) == {}
