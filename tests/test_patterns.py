"""Unit tests for pattern detection pipeline."""

import json
import pytest
from unittest.mock import patch, MagicMock

from oi.patterns import (
    detect_patterns, _build_clusters, _find_existing_principle,
    _update_existing_principle, _generate_principle, detect_principle,
)
from oi.knowledge import add_knowledge
from oi.state import _load_knowledge, _save_knowledge


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


def _setup_graph(session_dir, nodes, edges=None):
    """Helper: write a knowledge graph directly."""
    session_dir.mkdir(parents=True, exist_ok=True)
    _save_knowledge(session_dir, {"nodes": nodes, "edges": edges or []})


def _node(nid, source=None, ntype="fact", summary=None, status="active", **extra):
    n = {
        "id": nid, "type": ntype,
        "summary": summary or f"Node {nid}",
        "status": status, "source": source,
    }
    n.update(extra)
    return n


def _edge(source, target, edge_type="supports"):
    return {"source": source, "target": target, "type": edge_type, "created": "t"}


# === _build_clusters ===

class TestBuildClusters:
    def test_finds_support_connected(self):
        """3 nodes linked by supports from 2 sources → 1 cluster."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-b"),
            ],
            "edges": [
                _edge("fact-002", "fact-001"),
                _edge("fact-003", "fact-001"),
            ],
        }
        clusters = _build_clusters(["fact-001"], knowledge)
        assert len(clusters) == 1
        assert len(clusters[0]["node_ids"]) == 3
        assert len(clusters[0]["sources"]) == 2

    def test_ignores_small_clusters(self):
        """2 nodes → no clusters (below MIN_CLUSTER_SIZE)."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
            ],
            "edges": [_edge("fact-002", "fact-001")],
        }
        clusters = _build_clusters(["fact-001"], knowledge)
        assert len(clusters) == 0

    def test_requires_multiple_sources(self):
        """3 nodes same source → no clusters."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-a"),
                _node("fact-003", source="effort-a"),
            ],
            "edges": [
                _edge("fact-002", "fact-001"),
                _edge("fact-003", "fact-001"),
            ],
        }
        clusters = _build_clusters(["fact-001"], knowledge)
        assert len(clusters) == 0

    def test_deduplicates_clusters(self):
        """Two new_ids in same cluster → 1 cluster, not 2."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c"),
            ],
            "edges": [
                _edge("fact-001", "fact-002"),
                _edge("fact-003", "fact-002"),
            ],
        }
        # Both fact-001 and fact-002 are new, both in the same cluster
        clusters = _build_clusters(["fact-001", "fact-002"], knowledge)
        assert len(clusters) == 1

    def test_1hop_only(self):
        """A→B→C: cluster for A has B but not C (1-hop only)."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
                _node("fact-003", source="effort-c"),
            ],
            "edges": [
                _edge("fact-001", "fact-002"),
                _edge("fact-002", "fact-003"),
            ],
        }
        clusters = _build_clusters(["fact-001"], knowledge)
        # Cluster for fact-001 = {fact-001, fact-002} (1-hop from fact-001)
        # Only 2 nodes → below MIN_CLUSTER_SIZE → no clusters
        assert len(clusters) == 0


# === _find_existing_principle ===

class TestFindExistingPrinciple:
    def test_returns_existing_principle_id(self):
        """Cluster member has exemplifies edge → returns principle ID."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("principle-001", source="system", ntype="principle"),
            ],
            "edges": [_edge("fact-001", "principle-001", "exemplifies")],
        }
        result = _find_existing_principle({"fact-001", "fact-002"}, knowledge)
        assert result == "principle-001"

    def test_returns_none_when_no_principle(self):
        """No exemplifies edges → None."""
        knowledge = {
            "nodes": [
                _node("fact-001", source="effort-a"),
                _node("fact-002", source="effort-b"),
            ],
            "edges": [_edge("fact-001", "fact-002", "supports")],
        }
        result = _find_existing_principle({"fact-001", "fact-002"}, knowledge)
        assert result is None


# === detect_principle (LLM) ===

class TestDetectPrinciple:
    def test_returns_summary(self):
        """Mock chat returns valid JSON → returns summary dict."""
        mock_response = '{"summary": "Always test incrementally", "abstraction_level": 2}'
        with patch("oi.llm.chat", return_value=mock_response):
            result = detect_principle(["obs1", "obs2", "obs3"], "test-model")
        assert result is not None
        assert result["summary"] == "Always test incrementally"
        assert result["abstraction_level"] == 2

    def test_returns_none_on_null_summary(self):
        """Mock returns {"summary": null} → None."""
        mock_response = '{"summary": null, "abstraction_level": null}'
        with patch("oi.llm.chat", return_value=mock_response):
            result = detect_principle(["obs1", "obs2"], "test-model")
        assert result is None

    def test_returns_none_on_error(self):
        """Mock raises exception → None."""
        with patch("oi.llm.chat", side_effect=Exception("LLM error")):
            result = detect_principle(["obs1", "obs2"], "test-model")
        assert result is None


# === _generate_principle ===

class TestGeneratePrinciple:
    def test_creates_node_and_edges(self, session_dir):
        """Mock LLM → principle node + exemplifies edges created."""
        _setup_graph(session_dir, [
            _node("fact-001", source="effort-a"),
            _node("fact-002", source="effort-b"),
            _node("fact-003", source="effort-c"),
        ], [
            _edge("fact-001", "fact-002"),
            _edge("fact-003", "fact-002"),
        ])

        cluster_nodes = [
            _node("fact-001", source="effort-a"),
            _node("fact-002", source="effort-b"),
            _node("fact-003", source="effort-c"),
        ]

        mock_result = {"summary": "Test incrementally", "abstraction_level": 2}
        with patch("oi.patterns.detect_principle", return_value=mock_result):
            result = _generate_principle(session_dir, cluster_nodes, "test-model")

        assert result["action"] == "created"
        assert result["principle_id"] == "principle-001"
        assert result["instance_count"] == 3
        assert result["summary"] == "Test incrementally"

        # Verify exemplifies edges exist
        knowledge = _load_knowledge(session_dir)
        exemplifies = [e for e in knowledge["edges"] if e["type"] == "exemplifies"]
        assert len(exemplifies) == 3

    def test_skips_on_llm_failure(self, session_dir):
        """Mock returns None → action=skipped."""
        _setup_graph(session_dir, [
            _node("fact-001", source="effort-a"),
        ])

        with patch("oi.patterns.detect_principle", return_value=None):
            result = _generate_principle(session_dir, [_node("fact-001")], "test-model")

        assert result["action"] == "skipped"


# === _update_existing_principle ===

class TestUpdateExistingPrinciple:
    def test_bumps_instance_count(self, session_dir):
        """Existing principle gains new exemplifier, instance_count bumps."""
        _setup_graph(session_dir, [
            _node("principle-001", source="system", ntype="principle", instance_count=3),
            _node("fact-001", source="effort-a"),
            _node("fact-004", source="effort-d"),
        ], [
            _edge("fact-001", "principle-001", "exemplifies"),
        ])

        result = _update_existing_principle(session_dir, "principle-001", ["fact-004"])
        assert result["action"] == "updated"
        assert result["instance_count"] == 4  # 3 + 1

        knowledge = _load_knowledge(session_dir)
        exemplifies = [e for e in knowledge["edges"] if e["type"] == "exemplifies"]
        assert len(exemplifies) == 2  # original + new


# === detect_patterns (full pipeline) ===

class TestDetectPatterns:
    def test_full_pipeline_creates_principle(self, session_dir):
        """3 linked nodes from 2 sources, mock LLM → principle created."""
        _setup_graph(session_dir, [
            _node("fact-001", source="effort-a"),
            _node("fact-002", source="effort-b"),
            _node("fact-003", source="effort-b"),
        ], [
            _edge("fact-002", "fact-001"),
            _edge("fact-003", "fact-001"),
        ])

        mock_result = {"summary": "Always validate inputs", "abstraction_level": 2}
        with patch("oi.patterns.detect_principle", return_value=mock_result):
            results = detect_patterns(session_dir, ["fact-001"], "test-model")

        assert len(results) == 1
        assert results[0]["action"] == "created"
        assert results[0]["summary"] == "Always validate inputs"

    def test_returns_empty_on_no_convergence(self, session_dir):
        """Isolated nodes → [] (no clusters formed)."""
        _setup_graph(session_dir, [
            _node("fact-001", source="effort-a"),
            _node("fact-002", source="effort-b"),
        ])

        results = detect_patterns(session_dir, ["fact-001", "fact-002"], "test-model")
        assert results == []

    def test_best_effort_on_error(self, session_dir):
        """Exception during processing → [] (no crash)."""
        # Non-existent session_dir triggers error in _load_knowledge
        # Actually _load_knowledge returns default on missing file, so let's mock it
        with patch("oi.patterns._load_knowledge", side_effect=Exception("boom")):
            results = detect_patterns(session_dir, ["fact-001"], "test-model")
        assert results == []
