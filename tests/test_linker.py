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
    auto_link_same_group,
    LinkingResult,
    _voice_caps_contradicts,
    _build_link_prompt_single,
    _get_provenance_group,
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
        def mock_chat(messages, model, temperature=0, **kwargs):
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
        def mock_chat(messages, model, temperature=0, **kwargs):
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

        def mock_find(node, graph, max_candidates=8, exclude_same_group=False):
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


# === TestVoiceCapsContradicts (regression guard, Decision 019) ===


class TestVoiceCapsContradicts:
    def test_two_reported_nodes_capped(self):
        a = {"voice": "reported"}
        b = {"voice": "reported"}
        assert _voice_caps_contradicts(a, b) is True

    def test_two_described_nodes_capped(self):
        a = {"voice": "described"}
        b = {"voice": "described"}
        assert _voice_caps_contradicts(a, b) is True

    def test_reported_vs_described_capped(self):
        a = {"voice": "reported"}
        b = {"voice": "described"}
        assert _voice_caps_contradicts(a, b) is True

    def test_first_person_vs_reported_not_capped(self):
        a = {"voice": "first_person"}
        b = {"voice": "reported"}
        assert _voice_caps_contradicts(a, b) is False

    def test_two_first_person_not_capped(self):
        a = {"voice": "first_person"}
        b = {"voice": "first_person"}
        assert _voice_caps_contradicts(a, b) is False

    def test_missing_voice_defaults_first_person(self):
        a = {}
        b = {"voice": "reported"}
        assert _voice_caps_contradicts(a, b) is False


# === TestAbstractionLevel ===


class TestAbstractionLevel:
    def test_abstraction_level_surfaced_in_single_prompt(self):
        """Nodes with abstraction_level get it shown in the prompt."""
        a = _node("fact-001", "High-level principle")
        a["abstraction_level"] = 1
        b = _node("fact-002", "Implementation detail")
        b["abstraction_level"] = 3
        prompt = _build_link_prompt_single(a, b)
        assert "abstraction_level=1" in prompt
        assert "abstraction_level=3" in prompt

    def test_no_abstraction_level_no_note(self):
        """Nodes without abstraction_level produce no abstraction note."""
        a = _node("fact-001", "Claim A")
        b = _node("fact-002", "Claim B")
        prompt = _build_link_prompt_single(a, b)
        assert "abstraction_level" not in prompt

    def test_one_node_has_abstraction_level(self):
        """Only one node having abstraction_level still surfaces it."""
        a = _node("fact-001", "Claim A")
        a["abstraction_level"] = 2
        b = _node("fact-002", "Claim B")
        prompt = _build_link_prompt_single(a, b)
        assert "Node A abstraction_level=2" in prompt
        assert "Node B abstraction_level" not in prompt

    def test_abstraction_level_in_batch_prompt(self):
        """batch_link_nodes includes abstraction_level tags in candidate lines."""
        new = _node("fact-003", "JWT tokens must be refreshed before expiry")
        new["abstraction_level"] = 1
        c1 = _node("fact-001", "API uses JWT tokens for authentication")
        c1["abstraction_level"] = 3
        c2 = _node("fact-002", "JWT uses RS256")
        candidates = [
            {"node": c1, "score": 0.5},
            {"node": c2, "score": 0.3},
        ]

        mock_response = '[{"edge_type": "related_to", "reasoning": "r1"}, {"edge_type": "supports", "reasoning": "r2"}]'
        with patch("oi.linker.chat", return_value=mock_response) as mock_chat:
            batch_link_nodes(new, candidates, "test-model")

        prompt = mock_chat.call_args[0][0][1]["content"]
        assert "abstraction_level=1" in prompt  # Node A
        assert "abstraction_level=3" in prompt  # candidate 1
        assert "[abstraction_level=" not in prompt or "abstraction_level" in prompt  # candidate 2 has no tag


class TestSourceQuoteInLinker:
    """Tests for source_quote context in linker prompts."""

    def test_source_quote_in_single_prompt(self):
        """Single-pair prompt includes source quotes when available."""
        a = _node("fact-001", "Collapse requires compatible modeling")
        a["source_quote"] = "I think collapse only happens when the observer has a compatible model"
        b = _node("fact-002", "Decoherence explains apparent collapse")
        b["source_quote"] = "Standard physics says decoherence accounts for what looks like collapse"
        prompt = _build_link_prompt_single(a, b)
        assert "compatible model" in prompt
        assert "decoherence accounts" in prompt
        assert "Source quote" in prompt

    def test_no_source_quote_no_extra_text(self):
        """Nodes without source_quote don't add quote lines."""
        a = _node("fact-001", "Claim A")
        b = _node("fact-002", "Claim B")
        prompt = _build_link_prompt_single(a, b)
        assert "Source quote" not in prompt
        assert "Quote" not in prompt

    def test_one_node_has_quote(self):
        """Only one node having source_quote still surfaces it."""
        a = _node("fact-001", "Claim A")
        a["source_quote"] = "The exact text from the user"
        b = _node("fact-002", "Claim B")
        prompt = _build_link_prompt_single(a, b)
        assert "exact text from the user" in prompt
        # Only one quote line should appear
        assert prompt.count("Source quote") == 1

    def test_source_quote_in_batch_prompt(self):
        """batch_link_nodes includes source quotes in candidate lines and Node A."""
        new = _node("fact-003", "Collapse is entropy-driven")
        new["source_quote"] = "I believe the collapse process is fundamentally about entropy"
        c1 = _node("fact-001", "Entropy increases during measurement")
        c1["source_quote"] = "Each measurement step adds entropy to the system"
        c2 = _node("fact-002", "Quantum states are fragile")
        # c2 has no source_quote
        candidates = [
            {"node": c1, "score": 0.5},
            {"node": c2, "score": 0.3},
        ]

        mock_response = '[{"edge_type": "supports", "reasoning": "r1"}, {"edge_type": "related_to", "reasoning": "r2"}]'
        with patch("oi.linker.chat", return_value=mock_response) as mock_chat:
            batch_link_nodes(new, candidates, "test-model")

        prompt = mock_chat.call_args[0][0][1]["content"]
        # Node A quote
        assert "fundamentally about entropy" in prompt
        # Candidate 1 quote
        assert "Each measurement step" in prompt
        # Candidate 2 has no quote — shouldn't have Quote line for it
        assert "Quantum states are fragile" in prompt  # summary is there
        # Instruction about using quotes
        assert "source quotes" in prompt.lower() or "quote" in prompt.lower()

    def test_source_quote_instruction_in_single_prompt(self):
        """Single prompt includes instruction about using source quotes."""
        a = _node("fact-001", "Claim A")
        a["source_quote"] = "Some quote"
        b = _node("fact-002", "Claim B")
        prompt = _build_link_prompt_single(a, b)
        assert "misleading" in prompt.lower() or "context" in prompt.lower()


# === TestGetProvenanceGroup ===


class TestGetProvenanceGroup:
    def test_chatgpt_conversation(self):
        node = _node("f1", "X")
        node["provenance_uri"] = "chatgpt://physics-theory/conv-abc#turn-0"
        assert _get_provenance_group(node) == "chatgpt://physics-theory/conv-abc"

    def test_chatgpt_different_turns_same_group(self):
        a = _node("f1", "X")
        a["provenance_uri"] = "chatgpt://physics-theory/conv-abc#turn-0"
        b = _node("f2", "Y")
        b["provenance_uri"] = "chatgpt://physics-theory/conv-abc#turn-3"
        assert _get_provenance_group(a) == _get_provenance_group(b)

    def test_different_conversations(self):
        a = _node("f1", "X")
        a["provenance_uri"] = "chatgpt://physics-theory/conv-abc#turn-0"
        b = _node("f2", "Y")
        b["provenance_uri"] = "chatgpt://physics-theory/conv-xyz#turn-0"
        assert _get_provenance_group(a) != _get_provenance_group(b)

    def test_document_source(self):
        node = _node("f1", "X")
        node["provenance_uri"] = "doc://project-sources/paper.pdf#sec-3"
        assert _get_provenance_group(node) == "doc://project-sources/paper.pdf"

    def test_no_provenance(self):
        node = _node("f1", "X")
        assert _get_provenance_group(node) == ""

    def test_no_fragment(self):
        node = _node("f1", "X")
        node["provenance_uri"] = "chatgpt://src/conv-abc"
        assert _get_provenance_group(node) == "chatgpt://src/conv-abc"


# === TestAutoLinkSameGroup ===


class TestAutoLinkSameGroup:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    def test_creates_related_to_edges(self, session_dir):
        """Nodes from the same conversation get related_to edges."""
        from oi.state import _save_knowledge, _load_knowledge

        nodes = [
            {**_node("f1", "Collapse is entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-0"},
            {**_node("f2", "Mass resists entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-1"},
            {**_node("f3", "Time emerges from collapse"), "provenance_uri": "chatgpt://s/conv-a#turn-2"},
        ]
        _save_knowledge(session_dir, {"nodes": nodes, "edges": []})

        result = auto_link_same_group(["f1", "f2", "f3"], session_dir)

        assert result.edges_created == 3  # f1-f2, f1-f3, f2-f3
        kg = _load_knowledge(session_dir)
        assert len(kg["edges"]) == 3
        assert all(e["type"] == "related_to" for e in kg["edges"])

    def test_skips_cross_group(self, session_dir):
        """Nodes from different conversations don't get auto-linked."""
        from oi.state import _save_knowledge, _load_knowledge

        nodes = [
            {**_node("f1", "Collapse is entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-0"},
            {**_node("f2", "Mass resists entropy"), "provenance_uri": "chatgpt://s/conv-b#turn-0"},
        ]
        _save_knowledge(session_dir, {"nodes": nodes, "edges": []})

        result = auto_link_same_group(["f1", "f2"], session_dir)

        assert result.edges_created == 0

    def test_deduplicates_existing_edges(self, session_dir):
        """Doesn't create edges that already exist."""
        from oi.state import _save_knowledge, _load_knowledge

        nodes = [
            {**_node("f1", "Collapse is entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-0"},
            {**_node("f2", "Mass resists entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-1"},
        ]
        _save_knowledge(session_dir, {"nodes": nodes, "edges": [
            {"source": "f1", "target": "f2", "type": "related_to"},
        ]})

        result = auto_link_same_group(["f1", "f2"], session_dir)

        assert result.edges_created == 0
        kg = _load_knowledge(session_dir)
        assert len(kg["edges"]) == 1  # original only

    def test_mixed_groups(self, session_dir):
        """Only same-group pairs are linked."""
        from oi.state import _save_knowledge, _load_knowledge

        nodes = [
            {**_node("f1", "Collapse is entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-0"},
            {**_node("f2", "Mass resists entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-1"},
            {**_node("f3", "Dark energy expands"), "provenance_uri": "chatgpt://s/conv-b#turn-0"},
            {**_node("f4", "Gravity is closure"), "provenance_uri": "chatgpt://s/conv-b#turn-1"},
        ]
        _save_knowledge(session_dir, {"nodes": nodes, "edges": []})

        result = auto_link_same_group(["f1", "f2", "f3", "f4"], session_dir)

        assert result.edges_created == 2  # f1-f2 and f3-f4
        kg = _load_knowledge(session_dir)
        pairs = {frozenset({e["source"], e["target"]}) for e in kg["edges"]}
        assert frozenset({"f1", "f2"}) in pairs
        assert frozenset({"f3", "f4"}) in pairs
        assert frozenset({"f1", "f3"}) not in pairs

    def test_skips_unlinkable_types(self, session_dir):
        """Non-linkable node types are excluded."""
        from oi.state import _save_knowledge

        nodes = [
            {**_node("f1", "Collapse is entropy", node_type="fact"), "provenance_uri": "chatgpt://s/conv-a#turn-0"},
            {**_node("p1", "Prefers dark mode", node_type="preference"), "provenance_uri": "chatgpt://s/conv-a#turn-1"},
        ]
        _save_knowledge(session_dir, {"nodes": nodes, "edges": []})

        result = auto_link_same_group(["f1", "p1"], session_dir)

        # preference nodes are not linkable, so no edge
        assert result.edges_created == 0


# === TestFindCandidatesExcludeSameGroup ===


class TestFindCandidatesExcludeSameGroup:
    def test_excludes_same_group_candidates(self):
        """With exclude_same_group=True, same-conversation nodes are filtered."""
        a = {**_node("f1", "Collapse creates entropy and structure"), "provenance_uri": "chatgpt://s/conv-a#turn-0"}
        b = {**_node("f2", "Collapse creates time and entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-1"}
        c = {**_node("f3", "Collapse creates entropy in all systems"), "provenance_uri": "chatgpt://s/conv-b#turn-0"}
        graph = _graph(a, b, c)

        cands_with = find_candidates(a, graph, exclude_same_group=False)
        cands_without = find_candidates(a, graph, exclude_same_group=True)

        cand_ids_with = {c["node"]["id"] for c in cands_with}
        cand_ids_without = {c["node"]["id"] for c in cands_without}

        assert "f2" in cand_ids_with
        assert "f2" not in cand_ids_without
        assert "f3" in cand_ids_without

    def test_default_includes_same_group(self):
        """Default behavior (exclude_same_group=False) includes all candidates."""
        a = {**_node("f1", "Collapse creates entropy and structure"), "provenance_uri": "chatgpt://s/conv-a#turn-0"}
        b = {**_node("f2", "Collapse creates time and entropy"), "provenance_uri": "chatgpt://s/conv-a#turn-1"}
        graph = _graph(a, b)

        cands = find_candidates(a, graph)
        assert any(c["node"]["id"] == "f2" for c in cands)
