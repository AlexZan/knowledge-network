"""Tests for concept node clustering and synthesis (Phase 3, Decision 020)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from oi.cluster import find_clusters, synthesize_concepts
from oi.embed import save_embeddings


def _node(nid, ntype="fact", source=None, status="active"):
    return {
        "id": nid, "type": ntype, "summary": f"Summary for {nid}",
        "status": status, "source": source,
        "created": "2026-01-01T00:00:00", "updated": "2026-01-01T00:00:00",
    }


def _graph(nodes, edges=None):
    return {"nodes": nodes, "edges": edges or []}


def _setup_embeddings(session_dir, vectors, model="test-model"):
    """Write embeddings to session_dir/embeddings.json."""
    session_dir.mkdir(parents=True, exist_ok=True)
    save_embeddings(session_dir, {"model": model, "vectors": vectors})


class TestFindClusters:
    """Tests for find_clusters()."""

    def test_clusters_similar_nodes(self, tmp_path):
        """Nodes with high cosine similarity cluster together."""
        knowledge = _graph([
            _node("fact-001"),
            _node("fact-002"),
            _node("fact-003"),
        ])
        # fact-001 and fact-002 are very similar, fact-003 is different
        _setup_embeddings(tmp_path, {
            "fact-001": [1.0, 0.0, 0.0],
            "fact-002": [0.99, 0.1, 0.0],  # very similar to fact-001
            "fact-003": [0.0, 0.0, 1.0],   # orthogonal
        })

        clusters = find_clusters(tmp_path, knowledge, threshold=0.85)
        assert len(clusters) == 1
        assert set(clusters[0]) == {"fact-001", "fact-002"}

    def test_single_member_clusters_excluded(self, tmp_path):
        """Clusters with only 1 member are excluded."""
        knowledge = _graph([
            _node("fact-001"),
            _node("fact-002"),
            _node("fact-003"),
        ])
        # All nodes are orthogonal
        _setup_embeddings(tmp_path, {
            "fact-001": [1.0, 0.0, 0.0],
            "fact-002": [0.0, 1.0, 0.0],
            "fact-003": [0.0, 0.0, 1.0],
        })

        clusters = find_clusters(tmp_path, knowledge, threshold=0.85)
        assert clusters == []

    def test_only_fact_nodes_clustered(self, tmp_path):
        """Non-fact nodes are excluded from clustering."""
        knowledge = _graph([
            _node("fact-001", ntype="fact"),
            _node("preference-001", ntype="preference"),
            _node("decision-001", ntype="decision"),
        ])
        # All identical embeddings — would cluster if types weren't filtered
        _setup_embeddings(tmp_path, {
            "fact-001": [1.0, 0.0, 0.0],
            "preference-001": [1.0, 0.0, 0.0],
            "decision-001": [1.0, 0.0, 0.0],
        })

        clusters = find_clusters(tmp_path, knowledge, threshold=0.85)
        assert clusters == []  # fact-001 alone can't form a cluster

    def test_inactive_nodes_excluded(self, tmp_path):
        """Inactive nodes are excluded from clustering."""
        knowledge = _graph([
            _node("fact-001"),
            _node("fact-002", status="superseded"),
        ])
        _setup_embeddings(tmp_path, {
            "fact-001": [1.0, 0.0, 0.0],
            "fact-002": [1.0, 0.0, 0.0],
        })

        clusters = find_clusters(tmp_path, knowledge, threshold=0.85)
        assert clusters == []

    def test_sorted_by_size_descending(self, tmp_path):
        """Clusters are sorted by size, largest first."""
        knowledge = _graph([
            _node("fact-001"),
            _node("fact-002"),
            _node("fact-003"),
            _node("fact-004"),
            _node("fact-005"),
        ])
        _setup_embeddings(tmp_path, {
            "fact-001": [1.0, 0.0, 0.0],
            "fact-002": [0.99, 0.05, 0.0],
            "fact-003": [0.98, 0.1, 0.0],
            "fact-004": [0.0, 1.0, 0.0],
            "fact-005": [0.0, 0.99, 0.05],
        })

        clusters = find_clusters(tmp_path, knowledge, threshold=0.85)
        assert len(clusters) == 2
        assert len(clusters[0]) >= len(clusters[1])

    def test_no_embeddings_returns_empty(self, tmp_path):
        """No embeddings file → empty clusters."""
        knowledge = _graph([_node("fact-001"), _node("fact-002")])
        tmp_path.mkdir(parents=True, exist_ok=True)

        clusters = find_clusters(tmp_path, knowledge)
        assert clusters == []


class TestSynthesizeConcepts:
    """Tests for synthesize_concepts()."""

    def _setup_knowledge(self, tmp_path, nodes, edges=None):
        """Write a knowledge graph to the session dir."""
        from oi.state import _save_knowledge
        tmp_path.mkdir(parents=True, exist_ok=True)
        knowledge = _graph(nodes, edges)
        _save_knowledge(tmp_path, knowledge)
        return knowledge

    @patch("oi.cluster.chat")
    def test_creates_principle_nodes(self, mock_chat, tmp_path):
        """Synthesis creates principle nodes with exemplifies edges."""
        mock_chat.return_value = "Canonical concept: nodes cluster by similarity"

        nodes = [_node("fact-001"), _node("fact-002")]
        knowledge = self._setup_knowledge(tmp_path, nodes)

        clusters = [["fact-001", "fact-002"]]
        results = synthesize_concepts(clusters, tmp_path, knowledge)

        assert len(results) == 1
        assert results[0]["concept_node_id"].startswith("principle-")
        assert set(results[0]["member_ids"]) == {"fact-001", "fact-002"}
        assert "concept" in results[0]["summary"].lower() or results[0]["summary"]

    @patch("oi.cluster.chat")
    def test_exemplifies_edges_created(self, mock_chat, tmp_path):
        """Each cluster member gets an exemplifies edge to the concept node."""
        mock_chat.return_value = "Canonical concept statement"

        nodes = [_node("fact-001"), _node("fact-002"), _node("fact-003")]
        knowledge = self._setup_knowledge(tmp_path, nodes)

        clusters = [["fact-001", "fact-002", "fact-003"]]
        results = synthesize_concepts(clusters, tmp_path, knowledge)

        # Load graph and check edges
        from oi.state import _load_knowledge
        kg = _load_knowledge(tmp_path)
        concept_id = results[0]["concept_node_id"]

        exemplifies_edges = [
            e for e in kg["edges"]
            if e["type"] == "exemplifies" and e["target"] == concept_id
        ]
        assert len(exemplifies_edges) == 3
        sources = {e["source"] for e in exemplifies_edges}
        assert sources == {"fact-001", "fact-002", "fact-003"}

    @patch("oi.cluster.chat")
    def test_instance_count_set(self, mock_chat, tmp_path):
        """Principle node has instance_count matching cluster size."""
        mock_chat.return_value = "Canonical concept"

        nodes = [_node("fact-001"), _node("fact-002")]
        knowledge = self._setup_knowledge(tmp_path, nodes)

        clusters = [["fact-001", "fact-002"]]
        results = synthesize_concepts(clusters, tmp_path, knowledge)

        from oi.state import _load_knowledge
        kg = _load_knowledge(tmp_path)
        concept = next(n for n in kg["nodes"] if n["id"] == results[0]["concept_node_id"])
        assert concept.get("instance_count") == 2

    @patch("oi.cluster.chat")
    def test_llm_failure_skips_cluster(self, mock_chat, tmp_path):
        """If LLM call fails, that cluster is skipped gracefully."""
        mock_chat.side_effect = Exception("LLM error")

        nodes = [_node("fact-001"), _node("fact-002")]
        knowledge = self._setup_knowledge(tmp_path, nodes)

        clusters = [["fact-001", "fact-002"]]
        results = synthesize_concepts(clusters, tmp_path, knowledge)

        assert results == []

    @patch("oi.cluster.chat")
    def test_multiple_clusters(self, mock_chat, tmp_path):
        """Multiple clusters each get their own concept node."""
        mock_chat.side_effect = ["Concept A", "Concept B"]

        nodes = [_node("fact-001"), _node("fact-002"), _node("fact-003"), _node("fact-004")]
        knowledge = self._setup_knowledge(tmp_path, nodes)

        clusters = [["fact-001", "fact-002"], ["fact-003", "fact-004"]]
        results = synthesize_concepts(clusters, tmp_path, knowledge)

        assert len(results) == 2
        assert results[0]["concept_node_id"] != results[1]["concept_node_id"]
