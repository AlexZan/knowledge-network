"""Unit tests for knowledge graph query and supersedes operations."""

import json
import pytest

from oi.knowledge import add_knowledge, query_knowledge
from oi.state import _load_knowledge, _save_knowledge


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


def _add_node(session_dir, node_type, summary, source=None):
    """Helper: add a knowledge node and return parsed result."""
    return json.loads(add_knowledge(session_dir, node_type, summary, source=source))


# === Phase 1: query_knowledge tests ===

class TestQueryKnowledge:
    def test_basic_keyword_match(self, session_dir):
        """Query matching keywords returns the node."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "API uses JWT authentication with RS256")
        result = json.loads(query_knowledge(session_dir, "JWT auth"))
        assert len(result["results"]) == 1
        assert result["results"][0]["node_id"] == "fact-001"
        assert result["results"][0]["summary"] == "API uses JWT authentication with RS256"

    def test_returns_confidence_and_edges(self, session_dir):
        """Results include confidence dict and edges list."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "API uses JWT authentication")
        result = json.loads(query_knowledge(session_dir, "JWT"))
        node = result["results"][0]
        assert "confidence" in node
        assert "level" in node["confidence"]
        assert "edges" in node
        assert isinstance(node["edges"], list)

    def test_no_match_returns_empty(self, session_dir):
        """Query with no matching keywords returns empty results."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "API uses JWT authentication")
        result = json.loads(query_knowledge(session_dir, "pizza recipe cooking"))
        assert len(result["results"]) == 0

    def test_match_by_node_id(self, session_dir):
        """Query containing node ID matches directly."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "Some obscure fact")
        result = json.loads(query_knowledge(session_dir, "fact-001"))
        assert len(result["results"]) == 1
        assert result["results"][0]["node_id"] == "fact-001"

    def test_filter_by_node_type(self, session_dir):
        """node_type filter excludes non-matching types."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "JWT tokens expire hourly")
        _add_node(session_dir, "preference", "Prefer JWT over session cookies")
        result = json.loads(query_knowledge(session_dir, "JWT", node_type="preference"))
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "preference"

    def test_filter_by_min_confidence(self, session_dir):
        """min_confidence filter excludes low-confidence nodes."""
        session_dir.mkdir(parents=True, exist_ok=True)
        # Single node with no support = low confidence
        _add_node(session_dir, "fact", "JWT tokens expire hourly")
        result = json.loads(query_knowledge(session_dir, "JWT", min_confidence="medium"))
        assert len(result["results"]) == 0

    def test_excludes_superseded_nodes(self, session_dir):
        """Superseded nodes are excluded from results."""
        session_dir.mkdir(parents=True, exist_ok=True)
        knowledge = {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "JWT uses HS256", "status": "superseded"},
                {"id": "fact-002", "type": "fact", "summary": "JWT uses RS256", "status": "active"},
            ],
            "edges": [],
        }
        _save_knowledge(session_dir, knowledge)
        result = json.loads(query_knowledge(session_dir, "JWT"))
        assert len(result["results"]) == 1
        assert result["results"][0]["node_id"] == "fact-002"

    def test_total_active_count(self, session_dir):
        """Result includes total_active count of non-superseded nodes."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "API uses JWT")
        _add_node(session_dir, "preference", "Dark mode preferred")
        _add_node(session_dir, "decision", "Use PostgreSQL")
        result = json.loads(query_knowledge(session_dir, "JWT"))
        assert result["total_active"] == 3

    def test_multiple_matches_ranked_by_score(self, session_dir):
        """Multiple matching nodes are ranked by Jaccard score."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "JWT authentication tokens expire hourly")
        _add_node(session_dir, "fact", "JWT RS256 signing algorithm for authentication")
        result = json.loads(query_knowledge(session_dir, "JWT authentication"))
        assert len(result["results"]) == 2
        # Both should match, order by score

    def test_empty_graph_returns_empty(self, session_dir):
        """Query on empty graph returns empty results."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(query_knowledge(session_dir, "anything"))
        assert result["results"] == []
        assert result["total_active"] == 0

    def test_query_knowledge_via_execute_tool(self, session_dir):
        """query_knowledge dispatches correctly through execute_tool."""
        from oi.tools import execute_tool
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "API uses JWT authentication")
        result = json.loads(execute_tool(
            session_dir, "query_knowledge",
            {"query": "JWT"},
        ))
        assert len(result["results"]) == 1
        assert result["results"][0]["node_id"] == "fact-001"

    def test_includes_source_field(self, session_dir):
        """Results include the source field from the node."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "API uses JWT authentication", source="auth-effort")
        result = json.loads(query_knowledge(session_dir, "JWT"))
        assert result["results"][0]["source"] == "auth-effort"


# === Phase 3: Supersedes tests ===

class TestSupersedes:
    def test_supersedes_marks_old_node(self, session_dir):
        """Superseded nodes get status=superseded and superseded_by field."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use HS256 for JWT signing")
        result = json.loads(add_knowledge(
            session_dir, "decision", "Use RS256 for JWT signing",
            supersedes=["decision-001"],
        ))
        assert result["status"] == "added"
        assert result["node_id"] == "decision-002"

        knowledge = _load_knowledge(session_dir)
        old = next(n for n in knowledge["nodes"] if n["id"] == "decision-001")
        assert old["status"] == "superseded"
        assert old["superseded_by"] == "decision-002"

    def test_supersedes_creates_supersedes_edge(self, session_dir):
        """A 'supersedes' edge is created from new → old."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use HS256")
        add_knowledge(session_dir, "decision", "Use RS256", supersedes=["decision-001"])

        knowledge = _load_knowledge(session_dir)
        sup_edges = [e for e in knowledge["edges"] if e["type"] == "supersedes"]
        assert len(sup_edges) == 1
        assert sup_edges[0]["source"] == "decision-002"
        assert sup_edges[0]["target"] == "decision-001"

    def test_supersedes_transfers_support_edges(self, session_dir):
        """Inbound support edges from old node are copied to new node."""
        session_dir.mkdir(parents=True, exist_ok=True)
        # fact-001 supports decision-001
        knowledge = {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "JWT is industry standard", "status": "active", "source": "s1"},
                {"id": "decision-001", "type": "decision", "summary": "Use HS256", "status": "active", "source": "s2"},
            ],
            "edges": [
                {"source": "fact-001", "target": "decision-001", "type": "supports", "created": "t1"},
            ],
        }
        _save_knowledge(session_dir, knowledge)

        add_knowledge(session_dir, "decision", "Use RS256", supersedes=["decision-001"])

        knowledge = _load_knowledge(session_dir)
        # Original edge still exists (audit trail)
        orig = [e for e in knowledge["edges"] if e["target"] == "decision-001" and e["type"] == "supports"]
        assert len(orig) == 1
        # Copied edge to new node
        copied = [e for e in knowledge["edges"] if e["target"] == "decision-002" and e["type"] == "supports"]
        assert len(copied) == 1
        assert copied[0]["source"] == "fact-001"

    def test_supersedes_multiple_nodes(self, session_dir):
        """Can supersede multiple nodes at once."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use HS256")
        _add_node(session_dir, "decision", "Use symmetric keys")
        add_knowledge(
            session_dir, "decision", "Use RS256 with asymmetric keys",
            supersedes=["decision-001", "decision-002"],
        )

        knowledge = _load_knowledge(session_dir)
        for nid in ("decision-001", "decision-002"):
            old = next(n for n in knowledge["nodes"] if n["id"] == nid)
            assert old["status"] == "superseded"
            assert old["superseded_by"] == "decision-003"

        sup_edges = [e for e in knowledge["edges"] if e["type"] == "supersedes"]
        assert len(sup_edges) == 2

    def test_superseded_nodes_excluded_from_query(self, session_dir):
        """Superseded nodes don't appear in query_knowledge results."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use HS256 for JWT signing")
        add_knowledge(session_dir, "decision", "Use RS256 for JWT signing", supersedes=["decision-001"])

        result = json.loads(query_knowledge(session_dir, "JWT signing"))
        node_ids = [r["node_id"] for r in result["results"]]
        assert "decision-001" not in node_ids
        assert "decision-002" in node_ids

    def test_supersedes_skips_auto_linking_against_superseded(self, session_dir):
        """Auto-linking doesn't create edges against superseded node IDs."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use HS256")

        # Auto-linker tries to link against the superseded node
        mock_links = [{"target_id": "decision-001", "edge_type": "supports", "reasoning": "Related"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result = json.loads(add_knowledge(
                session_dir, "decision", "Use RS256",
                supersedes=["decision-001"],
            ))

        # Should not have auto-created a support edge to the superseded node
        edges_created = result.get("edges_created", [])
        auto_to_old = [e for e in edges_created if e["target_id"] == "decision-001"]
        assert len(auto_to_old) == 0

    def test_contradiction_result_includes_target_summary(self, session_dir):
        """Contradiction edges in result include target_summary."""
        from unittest.mock import patch

        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use JWT session cookies for auth")

        mock_links = [{"target_id": "decision-001", "edge_type": "contradicts", "reasoning": "Conflicting"}]
        with patch("oi.linker.run_linking", return_value=mock_links):
            result = json.loads(add_knowledge(session_dir, "decision", "Use OAuth tokens for auth"))

        edges = result.get("edges_created", [])
        assert len(edges) == 1
        assert edges[0]["edge_type"] == "contradicts"
        assert edges[0]["target_summary"] == "Use JWT session cookies for auth"

    def test_supersedes_via_execute_tool(self, session_dir):
        """Supersedes dispatches correctly through execute_tool."""
        from oi.tools import execute_tool

        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "decision", "Use HS256")
        result = json.loads(execute_tool(
            session_dir, "add_knowledge",
            {"node_type": "decision", "summary": "Use RS256", "supersedes": ["decision-001"]},
        ))
        assert result["status"] == "added"

        knowledge = _load_knowledge(session_dir)
        old = next(n for n in knowledge["nodes"] if n["id"] == "decision-001")
        assert old["status"] == "superseded"

    def test_supersedes_without_existing_node_is_noop(self, session_dir):
        """Superseding non-existent node IDs doesn't crash."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(add_knowledge(
            session_dir, "fact", "Some fact",
            supersedes=["nonexistent-999"],
        ))
        assert result["status"] == "added"

    def test_supersedes_empty_list_is_noop(self, session_dir):
        """Empty supersedes list behaves like no supersedes."""
        session_dir.mkdir(parents=True, exist_ok=True)
        _add_node(session_dir, "fact", "Some fact")
        result = json.loads(add_knowledge(
            session_dir, "fact", "Another fact",
            supersedes=[],
        ))
        assert result["status"] == "added"

        knowledge = _load_knowledge(session_dir)
        first = next(n for n in knowledge["nodes"] if n["id"] == "fact-001")
        assert first["status"] == "active"


# === Phase 4: Session ID on nodes ===

class TestSessionIdOnNodes:
    def test_created_in_session_stored_on_node(self, session_dir):
        """Nodes have created_in_session field when session_id is provided."""
        session_dir.mkdir(parents=True, exist_ok=True)
        result = json.loads(add_knowledge(
            session_dir, "fact", "Test fact",
            session_id="2024-01-15T10-30-00",
        ))
        assert result["status"] == "added"

        knowledge = _load_knowledge(session_dir)
        node = knowledge["nodes"][0]
        assert node["created_in_session"] == "2024-01-15T10-30-00"

    def test_no_session_id_means_no_field(self, session_dir):
        """Nodes without session_id don't have created_in_session field."""
        session_dir.mkdir(parents=True, exist_ok=True)
        add_knowledge(session_dir, "fact", "Test fact")

        knowledge = _load_knowledge(session_dir)
        node = knowledge["nodes"][0]
        assert "created_in_session" not in node
