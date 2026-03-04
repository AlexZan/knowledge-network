"""Unit tests for confidence computation from graph topology."""

import pytest

from oi.confidence import compute_confidence, compute_all_confidences, compute_salience


def _graph(nodes, edges=None):
    """Build a minimal graph dict for testing."""
    return {"nodes": nodes, "edges": edges or []}


def _node(nid, source=None, status="active"):
    return {"id": nid, "type": "fact", "summary": f"Node {nid}", "status": status, "source": source}


def _edge(source, target, edge_type="supports", reasoning=""):
    e = {"source": source, "target": target, "type": edge_type}
    if reasoning:
        e["reasoning"] = reasoning
    return e


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
        """One inbound support with reasoning → medium."""
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-a")],
            [_edge("fact-002", "fact-001", reasoning="directly supports")],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "medium"
        assert result["inbound_supports"] == pytest.approx(1.0, abs=0.15)

    def test_medium_two_independent_sources(self):
        """Two independent sources with reasoning → medium."""
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-b")],
            [_edge("fact-002", "fact-001", reasoning="corroborates from different source")],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "medium"
        assert result["independent_sources"] == 2

    def test_high_three_sources_two_supports(self):
        """3 independent sources + 2 reasoned inbound supports → high."""
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c"),
            ],
            [
                _edge("fact-002", "fact-001", reasoning="evidence from b"),
                _edge("fact-003", "fact-001", reasoning="evidence from c"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "high"
        assert result["inbound_supports"] == pytest.approx(2.0, abs=0.2)
        assert result["independent_sources"] == 3

    def test_contested_one_contradiction(self):
        """One contradiction with reasoning, no supports → contested."""
        graph = _graph(
            [_node("fact-001", source="effort-a"), _node("fact-002", source="effort-b")],
            [_edge("fact-002", "fact-001", "contradicts", reasoning="directly contradicts")],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "contested"
        assert result["inbound_contradicts"] == pytest.approx(1.0, abs=0.15)

    def test_contested_equal(self):
        """Equal supports and contradicts (both reasoned) → contested."""
        graph = _graph(
            [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c"),
            ],
            [
                _edge("fact-002", "fact-001", "supports", reasoning="supports claim"),
                _edge("fact-003", "fact-001", "contradicts", reasoning="contradicts claim"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] == "contested"
        assert result["inbound_supports"] == pytest.approx(1.0, abs=0.15)
        assert result["inbound_contradicts"] == pytest.approx(1.0, abs=0.15)

    def test_not_contested_when_outweighed(self):
        """2 reasoned supports vs 1 reasoned contradiction → NOT contested.

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
                _edge("fact-002", "fact-001", "supports", reasoning="evidence 1"),
                _edge("fact-003", "fact-001", "supports", reasoning="evidence 2"),
                _edge("fact-004", "fact-001", "contradicts", reasoning="counter"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        assert result["level"] != "contested"
        assert result["level"] in ("medium", "high")

    def test_same_source_counts_as_one(self):
        """5 reasoned supporters from same effort → 1 independent source.

        supports=5, contradicts=0, sources=1 → medium (via support rule).
        Not high because independent_sources < 3.
        """
        nodes = [_node("fact-001", source="effort-a")]
        edges = []
        for i in range(2, 7):
            nodes.append(_node(f"fact-{i:03d}", source="effort-a"))
            edges.append(_edge(f"fact-{i:03d}", "fact-001", reasoning=f"evidence {i}"))
        graph = _graph(nodes, edges)
        result = compute_confidence("fact-001", graph)
        assert result["independent_sources"] == 1
        assert result["inbound_supports"] == pytest.approx(5.0, abs=0.5)
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
                _edge("fact-002", "fact-001", reasoning="active support"),
                _edge("fact-003", "fact-001", reasoning="inactive support"),
            ],
        )
        result = compute_confidence("fact-001", graph)
        # fact-003 is inactive — excluded from PageRank, so only fact-002 contributes
        assert result["inbound_supports"] == pytest.approx(1.0, abs=0.15)
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
            [_edge("fact-002", "fact-001", reasoning="supports with reasoning")],
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
        """Inbound exemplifies edge with reasoning counts as inbound_supports≈1."""
        graph = _graph(
            [_node("principle-001", source="system"), _node("fact-001", source="effort-a")],
            [_edge("fact-001", "principle-001", "exemplifies", reasoning="instance of principle")],
        )
        result = compute_confidence("principle-001", graph)
        assert result["inbound_supports"] == pytest.approx(1.0, abs=0.15)

    def test_exemplifies_sources_counted(self):
        """Exemplifying nodes from different sources increase independent_sources."""
        graph = _graph(
            [
                _node("principle-001", source="system"),
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
            ],
            [
                _edge("fact-001", "principle-001", "exemplifies", reasoning="instance a"),
                _edge("fact-002", "principle-001", "exemplifies", reasoning="instance b"),
            ],
        )
        result = compute_confidence("principle-001", graph)
        assert result["independent_sources"] == 3  # system + effort-a + effort-b

    def test_exemplifies_boosts_to_high(self):
        """Principle with 3+ sources and 2+ reasoned exemplifies → high confidence."""
        graph = _graph(
            [
                _node("principle-001", source="system"),
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
            ],
            [
                _edge("fact-001", "principle-001", "exemplifies", reasoning="instance a"),
                _edge("fact-002", "principle-001", "exemplifies", reasoning="instance b"),
            ],
        )
        result = compute_confidence("principle-001", graph)
        assert result["level"] == "high"
        assert result["inbound_supports"] == pytest.approx(2.0, abs=0.2)
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
        # hub has 5 inbound citations (all reasoned), hub then supports target
        nodes = [_node(f"cite{i}") for i in range(5)] + [_node("hub"), _node("target")]
        edges = ([_edge(f"cite{i}", "hub", reasoning=f"citation {i}") for i in range(5)]
                 + [_edge("hub", "target", reasoning="hub supports target")])
        graph = _graph(nodes, edges)
        result = compute_all_confidences(graph, depth=None)
        assert result["target"]["inbound_supports"] > 1.0

    def test_isolated_source_contributes_about_one(self):
        """A node with no inbound edges + reasoned edge contributes ≈ 1.0."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", reasoning="direct evidence")],
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


class TestReasoningWeight:
    """Tests for edge weight by reasoning quality (Phase 1)."""

    def test_reasoned_edge_contributes_more(self):
        """Edge with reasoning contributes ~1.0, without contributes ~0.5."""
        graph_with = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", reasoning="detailed evidence")],
        )
        graph_without = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b")],
        )
        r_with = compute_all_confidences(graph_with, depth=None)
        r_without = compute_all_confidences(graph_without, depth=None)
        assert r_with["b"]["inbound_supports"] > r_without["b"]["inbound_supports"]
        assert r_with["b"]["inbound_supports"] == pytest.approx(1.0, abs=0.15)
        assert r_without["b"]["inbound_supports"] == pytest.approx(0.5, abs=0.15)

    def test_unreasoned_edge_half_weight(self):
        """Edge without reasoning contributes exactly 0.5x of a reasoned edge."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b")],  # no reasoning
        )
        result = compute_all_confidences(graph, depth=None)
        assert result["b"]["inbound_supports"] == pytest.approx(0.5, abs=0.15)

    def test_mixed_edges_weighted_sum(self):
        """2 reasoned + 1 unreasoned edges → weighted_supports ≈ 2.5."""
        graph = _graph(
            [_node("a"), _node("b"), _node("c"), _node("target")],
            [
                _edge("a", "target", reasoning="evidence a"),
                _edge("b", "target", reasoning="evidence b"),
                _edge("c", "target"),  # no reasoning → 0.5x
            ],
        )
        result = compute_all_confidences(graph, depth=None)
        # 2 * 1.0 + 1 * 0.5 = 2.5 (approximately, PageRank adjustments apply)
        assert result["target"]["inbound_supports"] == pytest.approx(2.5, abs=0.3)

    def test_unreasoned_edge_below_medium_threshold(self):
        """Single unreasoned edge (0.5) doesn't reach medium threshold (1.0)."""
        graph = _graph(
            [_node("a", source="s1"), _node("b", source="s1")],
            [_edge("a", "b")],  # no reasoning
        )
        result = compute_confidence("b", graph)
        assert result["level"] == "low"  # 0.5 < 1.0 threshold

    def test_two_unreasoned_edges_reach_medium(self):
        """Two unreasoned edges (2 * 0.5 = 1.0) reach medium threshold."""
        graph = _graph(
            [_node("a", source="s1"), _node("b", source="s1"), _node("target", source="s1")],
            [_edge("a", "target"), _edge("b", "target")],
        )
        result = compute_confidence("target", graph)
        assert result["level"] == "medium"

    def test_empty_reasoning_treated_as_no_reasoning(self):
        """Empty string reasoning is treated as no reasoning (0.5x weight)."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", reasoning="")],
        )
        result = compute_all_confidences(graph, depth=None)
        assert result["b"]["inbound_supports"] == pytest.approx(0.5, abs=0.15)


class TestSalience:
    """Tests for salience metric (Phase 2)."""

    def test_more_related_to_edges_higher_salience(self):
        """Node with 3 related_to edges has higher salience than node with 1."""
        graph = _graph(
            [_node("a"), _node("b"), _node("c"), _node("d")],
            [
                _edge("a", "b", "related_to"),
                _edge("a", "c", "related_to"),
                _edge("a", "d", "related_to"),
                _edge("b", "c", "related_to"),
            ],
        )
        salience = compute_salience(graph)
        assert salience["a"] > salience["d"]  # a has 3, d has 1

    def test_related_to_bidirectional(self):
        """Both source and target get counted for related_to edges."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", "related_to")],
        )
        salience = compute_salience(graph)
        # Both a and b should have salience from the same edge
        assert salience["a"] == salience["b"]
        assert salience["a"] == 1.0  # max is 1, so normalized to 1.0

    def test_logical_edges_dont_affect_salience(self):
        """Supports/contradicts edges don't increase salience."""
        graph = _graph(
            [_node("a"), _node("b"), _node("c")],
            [
                _edge("a", "b", "supports", reasoning="evidence"),
                _edge("a", "c", "related_to"),
            ],
        )
        salience = compute_salience(graph)
        assert salience["b"] == 0.0  # only has supports edge, no related_to
        assert salience["c"] > 0.0   # has related_to edge

    def test_no_related_to_edges_zero_salience(self):
        """All nodes get 0.0 salience when no related_to edges exist."""
        graph = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", "supports")],
        )
        salience = compute_salience(graph)
        assert salience["a"] == 0.0
        assert salience["b"] == 0.0

    def test_normalization_range(self):
        """Salience scores are in 0.0–1.0 range."""
        graph = _graph(
            [_node("a"), _node("b"), _node("c"), _node("d")],
            [
                _edge("a", "b", "related_to"),
                _edge("a", "c", "related_to"),
                _edge("a", "d", "related_to"),
            ],
        )
        salience = compute_salience(graph)
        for score in salience.values():
            assert 0.0 <= score <= 1.0
        # a has max (3 edges), should be 1.0
        assert salience["a"] == 1.0

    def test_empty_graph(self):
        """Empty graph returns empty salience dict."""
        assert compute_salience({"nodes": [], "edges": []}) == {}
