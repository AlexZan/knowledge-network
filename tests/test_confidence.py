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
        # fact-003 is inactive, so its source doesn't count
        # But the edge still counts as inbound (we count edges, not just active supporter sources)
        assert result["inbound_supports"] == 2
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
