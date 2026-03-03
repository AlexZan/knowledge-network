"""Unit tests for linker module (no LLM needed — mock chat calls)."""

import json
import pytest
import yaml
from unittest.mock import patch

from oi.linker import (
    find_candidates,
    link_nodes,
    batch_link_nodes,
    run_linking,
    link_new_nodes,
    LinkingResult,
)


# === Test fixtures ===

def _node(node_id, summary, node_type="fact", status="active"):
    return {
        "id": node_id,
        "type": node_type,
        "summary": summary,
        "status": status,
        "source": None,
        "created": "2024-01-01T00:00:00",
        "updated": "2024-01-01T00:00:00",
    }


def _graph(*nodes):
    return {"nodes": list(nodes), "edges": []}


# === TestFindCandidates ===

class TestFindCandidates:
    def test_finds_related_by_keyword_overlap(self):
        """'JWT tokens expire' matches node with 'JWT' keyword."""
        existing = _node("fact-001", "API uses JWT tokens for authentication")
        new = _node("fact-002", "JWT tokens expire after one hour")
        graph = _graph(existing, new)

        candidates = find_candidates(new, graph)
        assert len(candidates) == 1
        assert candidates[0]["node"]["id"] == "fact-001"
        assert candidates[0]["score"] > 0.1

    def test_returns_empty_for_unrelated(self):
        """'Weather is sunny' matches nothing about JWT."""
        existing = _node("fact-001", "API uses JWT tokens for authentication")
        new = _node("fact-002", "Weather is sunny today in the park")
        graph = _graph(existing, new)

        candidates = find_candidates(new, graph)
        assert candidates == []

    def test_excludes_self(self):
        """New node's own ID is excluded from candidates."""
        node = _node("fact-001", "JWT tokens are used for authentication")
        graph = _graph(node)

        candidates = find_candidates(node, graph)
        assert candidates == []

    def test_excludes_inactive_nodes(self):
        """Nodes with status=inactive are skipped."""
        inactive = _node("fact-001", "JWT tokens expire after one hour", status="inactive")
        new = _node("fact-002", "JWT tokens are used for authentication")
        graph = _graph(inactive, new)

        candidates = find_candidates(new, graph)
        assert candidates == []

    def test_sorts_by_score_descending(self):
        """Higher Jaccard similarity scores come first."""
        high_match = _node("fact-001", "JWT tokens expire after one hour of inactivity")
        low_match = _node("fact-002", "Database connections use tokens for pooling")
        new = _node("fact-003", "JWT tokens must be refreshed before expiration")
        graph = _graph(high_match, low_match, new)

        candidates = find_candidates(new, graph)
        assert len(candidates) >= 1
        # First candidate should have higher score
        if len(candidates) >= 2:
            assert candidates[0]["score"] >= candidates[1]["score"]

    def test_respects_max_candidates(self):
        """max_candidates=2 limits output to 2."""
        nodes = [_node(f"fact-{i:03d}", f"JWT token configuration option {i}") for i in range(1, 6)]
        new = _node("fact-010", "JWT token configuration settings")
        graph = _graph(*nodes, new)

        candidates = find_candidates(new, graph, max_candidates=2)
        assert len(candidates) <= 2

    def test_empty_graph(self):
        """0 active nodes → empty candidates."""
        new = _node("fact-001", "JWT tokens expire")
        graph = _graph(new)  # only self

        candidates = find_candidates(new, graph)
        assert candidates == []

    def test_single_keyword_below_threshold(self):
        """Very low Jaccard overlap is filtered out (score <= 0.1)."""
        # Nodes share only 1 keyword out of many unique keywords
        existing = _node("fact-001", "The large brown fox jumped over the lazy dog quickly yesterday morning")
        new = _node("fact-002", "Server configuration requires SSL certificates for production deployment pipeline")
        graph = _graph(existing, new)

        candidates = find_candidates(new, graph)
        assert candidates == []

    def test_empty_summary_returns_empty(self):
        """No keywords from empty summary → empty candidates."""
        existing = _node("fact-001", "JWT tokens expire")
        new = _node("fact-002", "")
        graph = _graph(existing, new)

        candidates = find_candidates(new, graph)
        assert candidates == []


# === TestLinkNodes ===

class TestLinkNodes:
    def test_parses_supports_response(self):
        """Valid 'supports' JSON response is parsed correctly."""
        new = _node("fact-002", "JWT uses RS256 signing algorithm")
        candidate = _node("fact-001", "API uses JWT for authentication")

        mock_response = '{"edge_type": "supports", "reasoning": "Both discuss JWT usage"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "supports"
        assert result["reasoning"] == "Both discuss JWT usage"

    def test_parses_contradicts_response(self):
        """Valid 'contradicts' JSON response is parsed correctly."""
        new = _node("decision-002", "Use session cookies for auth")
        candidate = _node("decision-001", "Use JWT tokens for auth")

        mock_response = '{"edge_type": "contradicts", "reasoning": "Conflicting auth strategies"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "contradicts"
        assert result["reasoning"] == "Conflicting auth strategies"

    def test_parses_none_response(self):
        """Valid 'none' JSON response is parsed correctly."""
        new = _node("fact-002", "Weather is sunny")
        candidate = _node("fact-001", "API uses JWT")

        mock_response = '{"edge_type": "none", "reasoning": "Unrelated topics"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "none"

    def test_strips_markdown_fences(self):
        """JSON wrapped in markdown fences is parsed correctly."""
        new = _node("fact-002", "JWT uses RS256")
        candidate = _node("fact-001", "API uses JWT")

        mock_response = '```json\n{"edge_type": "supports", "reasoning": "Related JWT facts"}\n```'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "supports"

    def test_returns_none_on_bad_json(self):
        """Non-JSON response returns none with parse_error."""
        new = _node("fact-002", "JWT uses RS256")
        candidate = _node("fact-001", "API uses JWT")

        with patch("oi.linker.chat", return_value="I think they are related"):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "none"
        assert result["reasoning"] == "parse_error"

    def test_returns_none_on_exception(self):
        """LLM raising exception returns none with parse_error."""
        new = _node("fact-002", "JWT uses RS256")
        candidate = _node("fact-001", "API uses JWT")

        with patch("oi.linker.chat", side_effect=RuntimeError("API error")):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "none"
        assert result["reasoning"] == "parse_error"

    def test_returns_none_on_invalid_edge_type(self):
        """Invalid edge_type value returns none with parse_error."""
        new = _node("fact-002", "JWT uses RS256")
        candidate = _node("fact-001", "API uses JWT")

        mock_response = '{"edge_type": "related", "reasoning": "They are related"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_nodes(new, candidate, "test-model")

        assert result["edge_type"] == "none"
        assert result["reasoning"] == "parse_error"


# === TestBatchLinkNodes ===

class TestBatchLinkNodes:
    def test_single_candidate_uses_link_nodes(self):
        """1 candidate falls back to per-pair link_nodes."""
        new = _node("fact-002", "JWT tokens expire after one hour")
        candidates = [{"node": _node("fact-001", "API uses JWT tokens for auth"), "score": 0.5}]

        mock_response = '{"edge_type": "supports", "reasoning": "Related"}'
        with patch("oi.linker.chat", return_value=mock_response):
            results = batch_link_nodes(new, candidates, "test-model")

        assert len(results) == 1
        assert results[0]["edge_type"] == "supports"
        assert results[0]["target_id"] == "fact-001"

    def test_batch_classifies_multiple_candidates(self):
        """Multiple candidates classified in one LLM call."""
        new = _node("fact-003", "JWT tokens must be refreshed before expiry")
        candidates = [
            {"node": _node("fact-001", "API uses JWT tokens for authentication"), "score": 0.5},
            {"node": _node("decision-001", "Use session cookies instead of JWT"), "score": 0.3},
        ]

        mock_response = '[{"edge_type": "supports", "reasoning": "Both about JWT"}, {"edge_type": "contradicts", "reasoning": "JWT vs cookies"}]'
        with patch("oi.linker.chat", return_value=mock_response):
            results = batch_link_nodes(new, candidates, "test-model")

        assert len(results) == 2
        assert results[0]["target_id"] == "fact-001"
        assert results[0]["edge_type"] == "supports"
        assert results[1]["target_id"] == "decision-001"
        assert results[1]["edge_type"] == "contradicts"

    def test_batch_strips_markdown_fences(self):
        """Batch response wrapped in markdown fences is parsed."""
        new = _node("fact-002", "JWT tokens expire")
        candidates = [
            {"node": _node("fact-001", "API uses JWT tokens"), "score": 0.5},
            {"node": _node("fact-003", "JWT uses RS256"), "score": 0.3},
        ]

        mock_response = '```json\n[{"edge_type": "supports", "reasoning": "r1"}, {"edge_type": "none", "reasoning": "r2"}]\n```'
        with patch("oi.linker.chat", return_value=mock_response):
            results = batch_link_nodes(new, candidates, "test-model")

        assert len(results) == 2
        assert results[0]["edge_type"] == "supports"
        assert results[1]["edge_type"] == "none"

    def test_batch_fallback_on_length_mismatch(self):
        """Wrong number of results falls back to per-pair calls."""
        new = _node("fact-002", "JWT tokens expire")
        candidates = [
            {"node": _node("fact-001", "API uses JWT tokens"), "score": 0.5},
            {"node": _node("fact-003", "JWT uses RS256"), "score": 0.3},
        ]

        # First call returns wrong-length array (triggers fallback),
        # subsequent calls return per-pair results
        call_count = [0]
        def mock_chat(messages, model, temperature=0):
            call_count[0] += 1
            if call_count[0] == 1:
                return '[{"edge_type": "supports", "reasoning": "only one"}]'
            return '{"edge_type": "supports", "reasoning": "fallback"}'

        with patch("oi.linker.chat", side_effect=mock_chat):
            results = batch_link_nodes(new, candidates, "test-model")

        assert len(results) == 2
        # Fallback made 2 more per-pair calls (total 3)
        assert call_count[0] == 3

    def test_batch_fallback_on_exception(self):
        """LLM exception falls back to per-pair calls."""
        new = _node("fact-002", "JWT tokens expire")
        candidates = [
            {"node": _node("fact-001", "API uses JWT tokens"), "score": 0.5},
            {"node": _node("fact-003", "JWT uses RS256"), "score": 0.3},
        ]

        call_count = [0]
        def mock_chat(messages, model, temperature=0):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("API error")
            return '{"edge_type": "none", "reasoning": "unrelated"}'

        with patch("oi.linker.chat", side_effect=mock_chat):
            results = batch_link_nodes(new, candidates, "test-model")

        assert len(results) == 2
        assert call_count[0] == 3

    def test_empty_candidates_returns_empty(self):
        """0 candidates → empty results, no LLM call."""
        new = _node("fact-001", "JWT tokens expire")
        with patch("oi.linker.chat") as mock_chat:
            results = batch_link_nodes(new, [], "test-model")
        assert results == []
        mock_chat.assert_not_called()

    def test_batch_invalid_edge_type_becomes_none(self):
        """Invalid edge_type in batch response is converted to none."""
        new = _node("fact-002", "JWT tokens expire")
        candidates = [
            {"node": _node("fact-001", "API uses JWT tokens"), "score": 0.5},
            {"node": _node("fact-003", "JWT uses RS256"), "score": 0.3},
        ]

        mock_response = '[{"edge_type": "related", "reasoning": "r1"}, {"edge_type": "supports", "reasoning": "r2"}]'
        with patch("oi.linker.chat", return_value=mock_response):
            results = batch_link_nodes(new, candidates, "test-model")

        assert results[0]["edge_type"] == "none"  # invalid → none
        assert results[1]["edge_type"] == "supports"


# === TestRunLinking ===

class TestRunLinking:
    def test_full_pipeline_creates_edges(self):
        """Candidates found and classified → edges returned."""
        existing = _node("fact-001", "API uses JWT tokens for authentication")
        new = _node("fact-002", "JWT tokens expire after one hour")
        graph = _graph(existing, new)

        mock_response = '{"edge_type": "supports", "reasoning": "Related JWT facts"}'
        with patch("oi.linker.chat", return_value=mock_response):
            edges = run_linking(new, graph, "test-model")

        assert len(edges) == 1
        assert edges[0]["target_id"] == "fact-001"
        assert edges[0]["edge_type"] == "supports"
        assert edges[0]["reasoning"] == "Related JWT facts"

    def test_filters_out_none_edges(self):
        """Edges with type 'none' are excluded from results."""
        existing = _node("fact-001", "API uses JWT tokens for authentication")
        new = _node("fact-002", "JWT tokens expire after one hour")
        graph = _graph(existing, new)

        mock_response = '{"edge_type": "none", "reasoning": "Unrelated"}'
        with patch("oi.linker.chat", return_value=mock_response):
            edges = run_linking(new, graph, "test-model")

        assert edges == []

    def test_empty_candidates_returns_empty(self):
        """No candidates found → no edges, no LLM calls."""
        new = _node("fact-001", "Weather is sunny today")
        graph = _graph(new)  # only self

        with patch("oi.linker.chat") as mock_chat:
            edges = run_linking(new, graph, "test-model")

        assert edges == []
        mock_chat.assert_not_called()


# === TestLinkNewNodes (Slice 13c) ===


def _write_graph(session_dir, nodes, edges=None):
    """Write a knowledge.yaml file with given nodes and edges."""
    graph = {"nodes": nodes, "edges": edges or []}
    path = session_dir / "knowledge.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(graph, f, default_flow_style=False)


def _read_graph(session_dir):
    """Read knowledge.yaml back."""
    path = session_dir / "knowledge.yaml"
    return yaml.safe_load(path.read_text())


class TestLinkNewNodes:
    def test_links_two_related_nodes(self, tmp_path):
        """Two related nodes get an edge created."""
        n1 = _node("fact-001", "API uses JWT tokens for authentication")
        n2 = _node("fact-002", "JWT tokens expire after one hour")
        _write_graph(tmp_path, [n1, n2])

        mock_response = '{"edge_type": "supports", "reasoning": "Related JWT facts"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_new_nodes(["fact-002"], tmp_path, model="test-model")

        assert result.edges_created == 1
        assert result.nodes_processed == 1
        graph = _read_graph(tmp_path)
        assert len(graph["edges"]) == 1
        assert graph["edges"][0]["type"] == "supports"

    def test_deduplicates_symmetric_pairs(self, tmp_path):
        """A→B and B→A produce only 1 edge, not 2."""
        n1 = _node("fact-001", "API uses JWT tokens for authentication")
        n2 = _node("fact-002", "JWT tokens expire after one hour")
        _write_graph(tmp_path, [n1, n2])

        mock_response = '{"edge_type": "supports", "reasoning": "Related JWT facts"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_new_nodes(
                ["fact-001", "fact-002"], tmp_path, model="test-model"
            )

        assert result.edges_created == 1
        graph = _read_graph(tmp_path)
        assert len(graph["edges"]) == 1

    def test_contradictions_flag_both_nodes(self, tmp_path):
        """Contradiction edges set has_contradiction on both nodes."""
        n1 = _node("decision-001", "Use JWT tokens for auth")
        n2 = _node("decision-002", "Use session cookies for auth instead of JWT")
        _write_graph(tmp_path, [n1, n2])

        mock_response = '{"edge_type": "contradicts", "reasoning": "Conflicting auth"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_new_nodes(["decision-002"], tmp_path, model="test-model")

        assert result.contradictions_found == 1
        graph = _read_graph(tmp_path)
        nodes_by_id = {n["id"]: n for n in graph["nodes"]}
        assert nodes_by_id["decision-001"].get("has_contradiction") is True
        assert nodes_by_id["decision-002"].get("has_contradiction") is True

    def test_skips_none_edges(self, tmp_path):
        """'none' classifications don't create edges."""
        n1 = _node("fact-001", "API uses JWT tokens for authentication")
        n2 = _node("fact-002", "JWT tokens expire after one hour")
        _write_graph(tmp_path, [n1, n2])

        mock_response = '{"edge_type": "none", "reasoning": "Unrelated"}'
        with patch("oi.linker.chat", return_value=mock_response):
            result = link_new_nodes(["fact-002"], tmp_path, model="test-model")

        assert result.edges_created == 0
        graph = _read_graph(tmp_path)
        assert len(graph["edges"]) == 0

    def test_progress_callback(self, tmp_path):
        """progress_fn is called for each node."""
        n1 = _node("fact-001", "API uses JWT tokens for authentication")
        n2 = _node("fact-002", "JWT tokens expire after one hour")
        _write_graph(tmp_path, [n1, n2])

        calls = []
        def track(current, total, node_id):
            calls.append((current, total, node_id))

        mock_response = '{"edge_type": "none", "reasoning": "Unrelated"}'
        with patch("oi.linker.chat", return_value=mock_response):
            link_new_nodes(
                ["fact-001", "fact-002"], tmp_path, model="test-model",
                progress_fn=track,
            )

        assert len(calls) == 2
        assert calls[0] == (1, 2, "fact-001")
        assert calls[1] == (2, 2, "fact-002")

    def test_per_node_errors_dont_stop_others(self, tmp_path):
        """An error on one node doesn't prevent processing the next."""
        n1 = _node("fact-001", "API uses JWT tokens for authentication")
        n2 = _node("fact-002", "JWT tokens expire after one hour")
        n3 = _node("fact-003", "JWT token refresh uses rotation pattern")
        _write_graph(tmp_path, [n1, n2, n3])

        call_count = [0]
        original_find = find_candidates

        def mock_find(node, graph, max_candidates=8):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Simulated error")
            return original_find(node, graph, max_candidates)

        mock_response = '{"edge_type": "supports", "reasoning": "Related"}'
        with patch("oi.linker.find_candidates", side_effect=mock_find), \
             patch("oi.linker.chat", return_value=mock_response):
            result = link_new_nodes(
                ["fact-002", "fact-003"], tmp_path, model="test-model"
            )

        assert len(result.errors) == 1
        assert "fact-002" in result.errors[0]
        # fact-003 should still have been processed
        assert result.nodes_processed == 2

    def test_empty_node_ids_is_noop(self, tmp_path):
        """Empty node list returns zero-value result, no file I/O."""
        result = link_new_nodes([], tmp_path, model="test-model")
        assert result == LinkingResult()
        assert not (tmp_path / "knowledge.yaml").exists()

    def test_result_structure(self, tmp_path):
        """LinkingResult has all expected fields with correct types."""
        n1 = _node("fact-001", "Weather is sunny today")
        _write_graph(tmp_path, [n1])

        # No candidates will be found (only 1 node, no keyword match)
        result = link_new_nodes(["fact-001"], tmp_path, model="test-model")

        assert isinstance(result, LinkingResult)
        assert isinstance(result.edges_created, int)
        assert isinstance(result.contradictions_found, int)
        assert isinstance(result.nodes_processed, int)
        assert isinstance(result.nodes_skipped, int)
        assert isinstance(result.errors, list)
        assert result.nodes_skipped == 1  # no candidates found
