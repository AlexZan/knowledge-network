"""Unit tests for embedding module (no real API calls — all mocked)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from oi.embed import (
    cosine_similarity,
    get_embedding,
    load_embeddings,
    save_embeddings,
    embed_node,
    ensure_embeddings,
    semantic_search,
)


# === Helpers ===

def _node(node_id, summary="test", node_type="fact", status="active"):
    return {
        "id": node_id,
        "type": node_type,
        "summary": summary,
        "status": status,
    }


def _mock_embedding(text, model=None):
    """Deterministic mock: hash text to a fake vector."""
    h = hash(text) % 1000
    return [h / 1000, (h + 100) / 1000, (h + 200) / 1000]


def _mock_embedding_response(input_texts):
    """Build a mock litellm embedding response."""
    resp = MagicMock()
    resp.data = [{"embedding": _mock_embedding(t)} for t in input_texts]
    return resp


# === TestCosineSimilarity ===

class TestCosineSimilarity:
    def test_identical_vectors(self):
        assert cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_similar_vectors(self):
        score = cosine_similarity([1, 1, 0], [1, 0.9, 0])
        assert score > 0.99

    def test_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_mismatched_length(self):
        assert cosine_similarity([1, 0], [1, 0, 0]) == 0.0

    def test_zero_vector(self):
        assert cosine_similarity([0, 0], [1, 1]) == 0.0


# === TestGetEmbedding ===

class TestGetEmbedding:
    def test_returns_vector(self):
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.1, 0.2, 0.3]}]
        with patch("oi.embed.embedding", return_value=mock_resp):
            vec = get_embedding("test text")
        assert vec == [0.1, 0.2, 0.3]

    def test_returns_none_on_error(self):
        with patch("oi.embed.embedding", side_effect=RuntimeError("no key")):
            vec = get_embedding("test text")
        assert vec is None

    def test_uses_configured_model(self):
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.1]}]
        with patch("oi.embed.embedding", return_value=mock_resp) as mock_emb:
            get_embedding("test", model="custom/model-v2")
        mock_emb.assert_called_once_with(model="custom/model-v2", input=["test"])


# === TestStorage ===

class TestStorage:
    def test_load_nonexistent_returns_empty(self, tmp_path):
        data = load_embeddings(tmp_path)
        assert data == {"model": "", "vectors": {}}

    def test_save_and_load_roundtrip(self, tmp_path):
        data = {"model": "test-model", "vectors": {"fact-001": [0.1, 0.2]}}
        save_embeddings(tmp_path, data)
        loaded = load_embeddings(tmp_path)
        assert loaded["model"] == "test-model"
        assert loaded["vectors"]["fact-001"] == [0.1, 0.2]

    def test_load_corrupt_file_returns_empty(self, tmp_path):
        (tmp_path / "embeddings.json").write_text("not json{{{")
        data = load_embeddings(tmp_path)
        assert data == {"model": "", "vectors": {}}


# === TestEmbedNode ===

class TestEmbedNode:
    def test_embeds_summary(self):
        node = _node("fact-001", "JWT tokens expire after one hour")
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.5, 0.6]}]
        with patch("oi.embed.embedding", return_value=mock_resp):
            vec = embed_node(node)
        assert vec == [0.5, 0.6]

    def test_empty_summary_returns_none(self):
        node = _node("fact-001", "")
        vec = embed_node(node)
        assert vec is None


# === TestEnsureEmbeddings ===

class TestEnsureEmbeddings:
    def test_embeds_missing_nodes(self, tmp_path):
        knowledge = {"nodes": [_node("fact-001", "test summary")], "edges": []}
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.1, 0.2]}]
        with patch("oi.embed.embedding", return_value=mock_resp):
            data = ensure_embeddings(tmp_path, knowledge, model="test-model")
        assert "fact-001" in data["vectors"]
        assert data["model"] == "test-model"

    def test_skips_already_embedded(self, tmp_path):
        existing = {"model": "test-model", "vectors": {"fact-001": [0.1, 0.2]}}
        save_embeddings(tmp_path, existing)
        knowledge = {"nodes": [_node("fact-001", "test")], "edges": []}
        with patch("oi.embed.embedding") as mock_emb:
            data = ensure_embeddings(tmp_path, knowledge, model="test-model")
        mock_emb.assert_not_called()
        assert data["vectors"]["fact-001"] == [0.1, 0.2]

    def test_reembeds_on_model_change(self, tmp_path):
        existing = {"model": "old-model", "vectors": {"fact-001": [0.1, 0.2]}}
        save_embeddings(tmp_path, existing)
        knowledge = {"nodes": [_node("fact-001", "test")], "edges": []}
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.9, 0.8]}]
        with patch("oi.embed.embedding", return_value=mock_resp):
            data = ensure_embeddings(tmp_path, knowledge, model="new-model")
        assert data["model"] == "new-model"
        assert data["vectors"]["fact-001"] == [0.9, 0.8]

    def test_removes_stale_embeddings(self, tmp_path):
        existing = {
            "model": "test-model",
            "vectors": {"fact-001": [0.1], "deleted-node": [0.9]},
        }
        save_embeddings(tmp_path, existing)
        knowledge = {"nodes": [_node("fact-001", "test")], "edges": []}
        with patch("oi.embed.embedding"):
            data = ensure_embeddings(tmp_path, knowledge, model="test-model")
        assert "deleted-node" not in data["vectors"]

    def test_skips_superseded_nodes(self, tmp_path):
        knowledge = {
            "nodes": [
                _node("fact-001", "old", status="superseded"),
                _node("fact-002", "new"),
            ],
            "edges": [],
        }
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.5]}]
        with patch("oi.embed.embedding", return_value=mock_resp):
            data = ensure_embeddings(tmp_path, knowledge, model="test-model")
        assert "fact-001" not in data["vectors"]
        assert "fact-002" in data["vectors"]


# === TestSemanticSearch ===

class TestSemanticSearch:
    def test_finds_similar_nodes(self, tmp_path):
        knowledge = {
            "nodes": [
                _node("fact-001", "JWT tokens expire"),
                _node("fact-002", "Weather is sunny"),
            ],
            "edges": [],
        }
        # Pre-populate embeddings
        emb_data = {
            "model": "test-model",
            "vectors": {
                "fact-001": [1.0, 0.0, 0.0],
                "fact-002": [0.0, 1.0, 0.0],
            },
        }
        save_embeddings(tmp_path, emb_data)

        # Query embedding close to fact-001
        with patch("oi.embed.get_embedding", return_value=[0.95, 0.05, 0.0]):
            results = semantic_search("JWT auth", tmp_path, knowledge, model="test-model")

        assert len(results) >= 1
        assert results[0]["node_id"] == "fact-001"
        assert results[0]["score"] > 0.9

    def test_returns_empty_on_embedding_failure(self, tmp_path):
        knowledge = {"nodes": [_node("fact-001", "test")], "edges": []}
        with patch("oi.embed.get_embedding", return_value=None):
            results = semantic_search("query", tmp_path, knowledge)
        assert results == []

    def test_respects_min_score(self, tmp_path):
        knowledge = {
            "nodes": [_node("fact-001", "test"), _node("fact-002", "other")],
            "edges": [],
        }
        emb_data = {
            "model": "test-model",
            "vectors": {
                "fact-001": [1.0, 0.0],
                "fact-002": [0.0, 1.0],
            },
        }
        save_embeddings(tmp_path, emb_data)

        # Query orthogonal to fact-002
        with patch("oi.embed.get_embedding", return_value=[1.0, 0.0]):
            results = semantic_search("q", tmp_path, knowledge, model="test-model", min_score=0.5)

        result_ids = {r["node_id"] for r in results}
        assert "fact-001" in result_ids
        assert "fact-002" not in result_ids

    def test_respects_top_k(self, tmp_path):
        nodes = [_node(f"fact-{i:03d}", f"text {i}") for i in range(1, 6)]
        knowledge = {"nodes": nodes, "edges": []}
        emb_data = {
            "model": "test-model",
            "vectors": {n["id"]: [0.9, 0.1] for n in nodes},
        }
        save_embeddings(tmp_path, emb_data)

        with patch("oi.embed.get_embedding", return_value=[0.9, 0.1]):
            results = semantic_search("q", tmp_path, knowledge, model="test-model", top_k=2)

        assert len(results) <= 2


# === Integration: query_knowledge with embeddings ===

class TestQueryKnowledgeWithEmbeddings:
    def test_semantic_seeds_merge_with_keyword_seeds(self, tmp_path):
        """Semantic search adds seeds that keyword matching misses."""
        from oi.knowledge import query_knowledge
        from oi.state import _save_knowledge

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        knowledge = {
            "nodes": [
                _node("fact-001", "Service-oriented architecture uses SOAP"),
                _node("fact-002", "Microservices communicate via REST APIs"),
            ],
            "edges": [],
        }
        _save_knowledge(session_dir, knowledge)

        # Pre-populate embeddings where both are similar to "SOA"
        emb_data = {
            "model": "test-model",
            "vectors": {
                "fact-001": [0.9, 0.1, 0.0],
                "fact-002": [0.8, 0.2, 0.0],
            },
        }
        save_embeddings(session_dir, emb_data)

        # Mock: "SOA" query embedding is close to both nodes
        with patch("oi.embed.get_embedding", return_value=[0.85, 0.15, 0.0]):
            result = json.loads(query_knowledge(session_dir, "SOA"))

        # fact-002 has no keyword overlap with "SOA" but semantic match should find it
        result_ids = [r["node_id"] for r in result["results"]]
        assert "fact-001" in result_ids

    def test_embedding_failure_falls_back_to_keywords(self, tmp_path):
        """If embedding fails, query still works via keywords."""
        from oi.knowledge import query_knowledge
        from oi.state import _save_knowledge

        session_dir = tmp_path / "session"
        session_dir.mkdir()

        knowledge = {
            "nodes": [_node("fact-001", "JWT tokens expire after one hour")],
            "edges": [],
        }
        _save_knowledge(session_dir, knowledge)

        with patch("oi.embed.get_embedding", return_value=None):
            result = json.loads(query_knowledge(session_dir, "JWT tokens"))

        assert len(result["results"]) == 1
        assert result["results"][0]["node_id"] == "fact-001"
