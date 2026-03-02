"""Unit tests for graph walk search module."""

import json
import pytest
from unittest.mock import patch

from oi.search import graph_walk, _build_adjacency


# === Helpers ===

def _node(node_id, summary="", node_type="fact", status="active"):
    return {
        "id": node_id,
        "type": node_type,
        "summary": summary,
        "status": status,
        "source": None,
        "created": "2024-01-01T00:00:00",
        "updated": "2024-01-01T00:00:00",
    }


def _edge(source, target, edge_type="supports"):
    return {"source": source, "target": target, "type": edge_type, "created": "2024-01-01T00:00:00"}


def _graph(nodes, edges=None):
    return {"nodes": nodes, "edges": edges or []}


# === TestBuildAdjacency ===

class TestBuildAdjacency:
    def test_bidirectional_supports(self):
        """supports edge creates entries in both directions."""
        knowledge = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", "supports")],
        )
        adj = _build_adjacency(knowledge)
        assert ("b", "supports") in adj["a"]
        assert ("a", "supports") in adj["b"]

    def test_supersedes_walks_toward_newer_only(self):
        """supersedes edge: old→new is walkable, new→old is not."""
        knowledge = _graph(
            [_node("new-001"), _node("old-001", status="active")],
            [_edge("new-001", "old-001", "supersedes")],
        )
        adj = _build_adjacency(knowledge)
        # From old, can reach new (toward newer)
        assert ("new-001", "supersedes") in adj.get("old-001", [])
        # From new, cannot reach old (toward older)
        new_neighbors = [nid for nid, _ in adj.get("new-001", [])]
        assert "old-001" not in new_neighbors

    def test_empty_edges(self):
        """No edges → empty adjacency."""
        knowledge = _graph([_node("a")], [])
        adj = _build_adjacency(knowledge)
        assert adj == {}

    def test_multiple_edge_types(self):
        """Different edge types between same nodes are all represented."""
        knowledge = _graph(
            [_node("a"), _node("b")],
            [
                _edge("a", "b", "supports"),
                _edge("a", "b", "because_of"),
            ],
        )
        adj = _build_adjacency(knowledge)
        a_neighbors = adj["a"]
        assert ("b", "supports") in a_neighbors
        assert ("b", "because_of") in a_neighbors


# === TestGraphWalk ===

class TestGraphWalk:
    def test_single_seed_no_edges_returns_seed(self):
        """With no edges, graph walk returns just the seed."""
        knowledge = _graph([_node("a"), _node("b")], [])
        seeds = [{"node_id": "a", "score": 0.8}]
        result = graph_walk(seeds, knowledge)
        assert len(result) == 1
        assert result[0]["node_id"] == "a"
        assert result[0]["score"] == 0.8

    def test_empty_seeds_returns_empty(self):
        """No seeds → no results."""
        knowledge = _graph([_node("a")])
        result = graph_walk([], knowledge)
        assert result == []

    def test_1_hop_expansion(self):
        """Seed at A, edge A→B, B is discovered at 1 hop with decay."""
        knowledge = _graph(
            [_node("a"), _node("b")],
            [_edge("a", "b", "supports")],
        )
        seeds = [{"node_id": "a", "score": 1.0}]
        result = graph_walk(seeds, knowledge, hop_1_decay=0.7, hop_2_decay=0.4)

        scores = {r["node_id"]: r["score"] for r in result}
        assert scores["a"] == 1.0
        assert scores["b"] == pytest.approx(0.7)

    def test_2_hop_expansion(self):
        """Seed at A, A→B→C, C is discovered at 2 hops with hop_2 decay."""
        knowledge = _graph(
            [_node("a"), _node("b"), _node("c")],
            [
                _edge("a", "b", "supports"),
                _edge("b", "c", "supports"),
            ],
        )
        seeds = [{"node_id": "a", "score": 1.0}]
        result = graph_walk(seeds, knowledge, hop_1_decay=0.7, hop_2_decay=0.4)

        scores = {r["node_id"]: r["score"] for r in result}
        assert scores["a"] == 1.0
        assert scores["b"] == pytest.approx(0.7)
        assert scores["c"] == pytest.approx(0.4)

    def test_convergence_multiple_paths_add_scores(self):
        """Node reachable via two independent seeds scores higher."""
        # A─→C and B─→C; both A and B are seeds
        knowledge = _graph(
            [_node("a"), _node("b"), _node("c")],
            [
                _edge("a", "c", "supports"),
                _edge("b", "c", "supports"),
            ],
        )
        seeds = [
            {"node_id": "a", "score": 0.6},
            {"node_id": "b", "score": 0.4},
        ]
        result = graph_walk(seeds, knowledge, hop_1_decay=0.7)

        scores = {r["node_id"]: r["score"] for r in result}
        # C reached from A (0.6*0.7=0.42) and from B (0.4*0.7=0.28) → 0.70
        assert scores["c"] == pytest.approx(0.7)

    def test_skip_superseded_nodes(self):
        """Superseded nodes are not included in walk results."""
        knowledge = _graph(
            [_node("a"), _node("old", status="superseded"), _node("c")],
            [
                _edge("a", "old", "supports"),
                _edge("old", "c", "supports"),
            ],
        )
        seeds = [{"node_id": "a", "score": 1.0}]
        result = graph_walk(seeds, knowledge)

        result_ids = {r["node_id"] for r in result}
        assert "old" not in result_ids

    def test_supersedes_edge_walks_toward_newer(self):
        """Walking from old node via supersedes edge reaches the newer node."""
        knowledge = _graph(
            [_node("new-v2"), _node("old-v1")],
            [_edge("new-v2", "old-v1", "supersedes")],
        )
        seeds = [{"node_id": "old-v1", "score": 0.5}]
        result = graph_walk(seeds, knowledge, hop_1_decay=0.7)

        scores = {r["node_id"]: r["score"] for r in result}
        assert "new-v2" in scores
        assert scores["new-v2"] == pytest.approx(0.35)

    def test_supersedes_edge_does_not_walk_toward_older(self):
        """Walking from new node via supersedes edge does NOT reach older node."""
        knowledge = _graph(
            [_node("new-v2"), _node("old-v1")],
            [_edge("new-v2", "old-v1", "supersedes")],
        )
        seeds = [{"node_id": "new-v2", "score": 0.5}]
        result = graph_walk(seeds, knowledge, hop_1_decay=0.7)

        result_ids = {r["node_id"] for r in result}
        assert "old-v1" not in result_ids

    def test_cycle_handling(self):
        """A→B→A cycle doesn't cause infinite loop."""
        knowledge = _graph(
            [_node("a"), _node("b")],
            [
                _edge("a", "b", "supports"),
                _edge("b", "a", "supports"),
            ],
        )
        seeds = [{"node_id": "a", "score": 1.0}]
        result = graph_walk(seeds, knowledge)
        # Should complete without hanging; B is discovered, A is seed (not re-walked)
        scores = {r["node_id"]: r["score"] for r in result}
        assert "a" in scores
        assert "b" in scores

    def test_results_sorted_by_score_descending(self):
        """Results are sorted highest score first."""
        knowledge = _graph(
            [_node("a"), _node("b"), _node("c")],
            [
                _edge("a", "b", "supports"),
                _edge("a", "c", "supports"),
            ],
        )
        # Two seeds: a (high) and b (low). C only reached from a.
        seeds = [
            {"node_id": "a", "score": 1.0},
            {"node_id": "b", "score": 0.1},
        ]
        result = graph_walk(seeds, knowledge)
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_max_hops_1_limits_expansion(self):
        """max_hops=1 does not discover 2-hop nodes."""
        knowledge = _graph(
            [_node("a"), _node("b"), _node("c")],
            [
                _edge("a", "b", "supports"),
                _edge("b", "c", "supports"),
            ],
        )
        seeds = [{"node_id": "a", "score": 1.0}]
        result = graph_walk(seeds, knowledge, max_hops=1)

        result_ids = {r["node_id"] for r in result}
        assert "b" in result_ids
        assert "c" not in result_ids

    def test_spec_example(self):
        """Reproduce the worked example from the 12a spec."""
        knowledge = _graph(
            [
                _node("fact-001", "REST APIs use JSON"),
                _node("decision-003", "Use REST for integrations", "decision"),
                _node("fact-004", "JSON is human-readable"),
                _node("fact-002", "SOAP uses XML"),
            ],
            [
                _edge("fact-001", "decision-003", "supports"),
                _edge("fact-001", "fact-004", "supports"),
                _edge("fact-002", "decision-003", "contradicts"),
            ],
        )
        seeds = [
            {"node_id": "fact-001", "score": 0.5},
            {"node_id": "fact-004", "score": 0.3},
        ]
        result = graph_walk(seeds, knowledge, hop_1_decay=0.7, hop_2_decay=0.4)

        scores = {r["node_id"]: r["score"] for r in result}

        # fact-001: 0.5 (keyword) + 0.21 (1-hop walk from fact-004) = 0.71
        assert scores["fact-001"] == pytest.approx(0.71)
        # fact-004: 0.3 (keyword) + 0.35 (1-hop walk from fact-001) = 0.65
        assert scores["fact-004"] == pytest.approx(0.65)
        # decision-003: 0.35 (1-hop from fact-001) + 0.12 (2-hop from fact-004 via fact-001) = 0.47
        assert scores["decision-003"] == pytest.approx(0.47)
        # fact-002: 0.20 (2-hop from fact-001 via decision-003)
        assert scores["fact-002"] == pytest.approx(0.20)


# === Integration: query_knowledge with graph walk ===

@patch("oi.embed.get_embedding", return_value=None)
class TestQueryKnowledgeWithWalk:
    def test_walk_discovers_neighborhood_matches(self, _mock_embed, tmp_path):
        """query_knowledge finds nodes connected by edges, not just keyword matches."""
        from oi.knowledge import query_knowledge
        from oi.state import _save_knowledge

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        knowledge = {
            "nodes": [
                _node("fact-001", "REST APIs use JSON format"),
                _node("decision-001", "Use REST for all integrations", "decision"),
                _node("fact-002", "GraphQL reduces over-fetching"),
            ],
            "edges": [
                _edge("fact-001", "decision-001", "supports"),
            ],
        }
        _save_knowledge(session_dir, knowledge)

        result = json.loads(query_knowledge(session_dir, "JSON format"))
        result_ids = [r["node_id"] for r in result["results"]]

        # fact-001 matches by keyword
        assert "fact-001" in result_ids
        # decision-001 discovered via 1-hop walk from fact-001
        assert "decision-001" in result_ids
        # fact-002 has no keyword match and no edge connection
        assert "fact-002" not in result_ids


class TestLinkerWithWalk:
    def test_find_candidates_discovers_walk_neighbors(self):
        """find_candidates surfaces nodes reachable by graph walk, not just keyword overlap."""
        from oi.linker import find_candidates

        # Node C has no keyword overlap with new_node, but is connected to B which does
        new_node = _node("fact-new", "JWT tokens expire after one hour")
        b = _node("fact-001", "API uses JWT tokens for authentication")
        c = _node("decision-001", "Use OAuth2 for all services", "decision")

        knowledge = _graph(
            [new_node, b, c],
            [_edge("fact-001", "decision-001", "supports")],
        )

        candidates = find_candidates(new_node, knowledge)
        candidate_ids = [c["node"]["id"] for c in candidates]

        # B matches by keyword
        assert "fact-001" in candidate_ids
        # C discovered via walk from B
        assert "decision-001" in candidate_ids
