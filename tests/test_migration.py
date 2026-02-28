"""Tests for manifest.yaml → knowledge.yaml migration."""

import json
import yaml
import pytest

from oi.state import (
    _migrate_manifest_to_knowledge, _load_efforts, _save_efforts,
    _load_knowledge, _save_knowledge,
)
from oi.tools import open_effort, close_effort, get_active_effort, get_all_open_efforts


@pytest.fixture
def session_dir(tmp_path):
    return tmp_path / "session"


class TestMigration:
    def test_migrate_efforts_to_knowledge(self, session_dir):
        """Migration converts manifest efforts into type='effort' knowledge nodes."""
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [
                {"id": "auth-bug", "status": "concluded", "summary": "Fixed auth."},
                {"id": "perf-fix", "status": "open", "active": True, "summary": None},
            ]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        _migrate_manifest_to_knowledge(session_dir)

        # manifest.yaml should be renamed to .bak
        assert not (session_dir / "manifest.yaml").exists()
        assert (session_dir / "manifest.yaml.bak").exists()

        # Efforts should be in knowledge.yaml as type='effort' nodes
        knowledge = _load_knowledge(session_dir)
        effort_nodes = [n for n in knowledge["nodes"] if n.get("type") == "effort"]
        assert len(effort_nodes) == 2
        ids = {n["id"] for n in effort_nodes}
        assert ids == {"auth-bug", "perf-fix"}

        # Check fields preserved
        auth = next(n for n in effort_nodes if n["id"] == "auth-bug")
        assert auth["status"] == "concluded"
        assert auth["summary"] == "Fixed auth."

        perf = next(n for n in effort_nodes if n["id"] == "perf-fix")
        assert perf["status"] == "open"
        assert perf["active"] is True

    def test_migrate_idempotent(self, session_dir):
        """Running migration twice doesn't duplicate nodes."""
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [{"id": "task-1", "status": "open", "summary": None}]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        _migrate_manifest_to_knowledge(session_dir)

        # Restore manifest to simulate re-run
        (session_dir / "manifest.yaml.bak").rename(session_dir / "manifest.yaml")

        _migrate_manifest_to_knowledge(session_dir)

        knowledge = _load_knowledge(session_dir)
        effort_nodes = [n for n in knowledge["nodes"] if n["id"] == "task-1"]
        assert len(effort_nodes) == 1  # No duplicate

    def test_migrate_empty_manifest(self, session_dir):
        """Empty manifest.yaml is backed up with no nodes added."""
        session_dir.mkdir(parents=True)
        (session_dir / "manifest.yaml").write_text("efforts: []\n")

        _migrate_manifest_to_knowledge(session_dir)

        assert not (session_dir / "manifest.yaml").exists()
        assert (session_dir / "manifest.yaml.bak").exists()

        knowledge = _load_knowledge(session_dir)
        assert knowledge["nodes"] == []

    def test_migrate_preserves_existing_knowledge_nodes(self, session_dir):
        """Migration doesn't clobber existing non-effort knowledge nodes."""
        session_dir.mkdir(parents=True)

        # Pre-existing knowledge
        knowledge = {
            "nodes": [
                {"id": "fact-1", "type": "fact", "status": "active", "summary": "Python is great."}
            ],
            "edges": [{"source": "fact-1", "target": "fact-1", "edge_type": "supports"}]
        }
        _save_knowledge(session_dir, knowledge)

        # Manifest with efforts
        manifest = {
            "efforts": [{"id": "my-effort", "status": "concluded", "summary": "Done."}]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        _migrate_manifest_to_knowledge(session_dir)

        knowledge = _load_knowledge(session_dir)
        assert len(knowledge["nodes"]) == 2
        assert any(n["id"] == "fact-1" and n["type"] == "fact" for n in knowledge["nodes"])
        assert any(n["id"] == "my-effort" and n["type"] == "effort" for n in knowledge["nodes"])
        # Edges preserved
        assert len(knowledge["edges"]) == 1

    def test_migrate_no_manifest_is_noop(self, session_dir):
        """No manifest.yaml → migration does nothing."""
        session_dir.mkdir(parents=True)
        _migrate_manifest_to_knowledge(session_dir)
        assert not (session_dir / "knowledge.yaml").exists()

    def test_auto_migration_on_load(self, session_dir):
        """_load_efforts auto-migrates manifest.yaml if it exists."""
        session_dir.mkdir(parents=True)
        manifest = {
            "efforts": [{"id": "auto-task", "status": "open", "summary": None}]
        }
        (session_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        efforts = _load_efforts(session_dir)
        assert len(efforts) == 1
        assert efforts[0]["id"] == "auto-task"

        # manifest.yaml should be gone
        assert not (session_dir / "manifest.yaml").exists()
        assert (session_dir / "manifest.yaml.bak").exists()


class TestEffortKnowledgeCoexistence:
    """Efforts and knowledge nodes coexist in the same knowledge.yaml."""

    def test_open_effort_alongside_knowledge(self, session_dir):
        """Opening an effort preserves existing knowledge nodes."""
        session_dir.mkdir(parents=True)
        knowledge = {
            "nodes": [
                {"id": "fact-1", "type": "fact", "status": "active", "summary": "A fact."}
            ],
            "edges": []
        }
        _save_knowledge(session_dir, knowledge)

        open_effort(session_dir, "my-work")

        knowledge = _load_knowledge(session_dir)
        types = {n["type"] for n in knowledge["nodes"]}
        assert "fact" in types
        assert "effort" in types
        assert len(knowledge["nodes"]) == 2

    def test_close_effort_preserves_knowledge(self, session_dir):
        """Closing an effort doesn't affect knowledge nodes."""
        session_dir.mkdir(parents=True)
        knowledge = {
            "nodes": [
                {"id": "pref-1", "type": "preference", "status": "active", "summary": "A preference."}
            ],
            "edges": []
        }
        _save_knowledge(session_dir, knowledge)

        open_effort(session_dir, "task-1")

        # Write raw log so close can summarize (needs enough messages)
        effort_file = session_dir / "efforts" / "task-1.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        lines = ""
        for i in range(5):
            lines += json.dumps({"role": "user", "content": f"Working on step {i} of the task", "ts": f"t{i*2}"}) + "\n"
            lines += json.dumps({"role": "assistant", "content": f"Completed step {i} successfully", "ts": f"t{i*2+1}"}) + "\n"
        effort_file.write_text(lines)

        from unittest.mock import patch
        with patch("oi.llm.summarize_effort", return_value="Task done."):
            with patch("oi.llm.extract_knowledge", return_value=[]):
                close_effort(session_dir)

        knowledge = _load_knowledge(session_dir)
        pref = next(n for n in knowledge["nodes"] if n["type"] == "preference")
        assert pref["id"] == "pref-1"
        assert pref["status"] == "active"

        effort = next(n for n in knowledge["nodes"] if n["type"] == "effort")
        assert effort["status"] == "concluded"
        assert effort["summary"] == "Task done."

    def test_round_trip_effort_lifecycle(self, session_dir):
        """Open → add knowledge → close → verify both types in knowledge.yaml."""
        session_dir.mkdir(parents=True)

        # Open effort
        open_effort(session_dir, "feature-x")

        # Add a knowledge node
        knowledge = _load_knowledge(session_dir)
        knowledge["nodes"].append({
            "id": "decision-1",
            "type": "decision",
            "status": "active",
            "summary": "Use React for the frontend.",
            "source": "feature-x",
        })
        _save_knowledge(session_dir, knowledge)

        # Write raw log for effort
        effort_file = session_dir / "efforts" / "feature-x.jsonl"
        effort_file.parent.mkdir(parents=True, exist_ok=True)
        effort_file.write_text(
            json.dumps({"role": "user", "content": "building feature x", "ts": "t1"}) + "\n"
        )

        # Close effort
        from unittest.mock import patch
        with patch("oi.llm.summarize_effort", return_value="Built feature X with React."):
            with patch("oi.llm.extract_knowledge", return_value=[]):
                close_effort(session_dir)

        # Verify both types in knowledge.yaml
        knowledge = _load_knowledge(session_dir)
        types = {n["type"] for n in knowledge["nodes"]}
        assert types == {"effort", "decision"}

        effort = next(n for n in knowledge["nodes"] if n["type"] == "effort")
        assert effort["status"] == "concluded"
        assert effort["summary"] == "Built feature X with React."

        decision = next(n for n in knowledge["nodes"] if n["type"] == "decision")
        assert decision["status"] == "active"
        assert decision["source"] == "feature-x"

    def test_save_efforts_preserves_non_effort_nodes(self, session_dir):
        """_save_efforts only replaces effort nodes, keeps everything else."""
        session_dir.mkdir(parents=True)
        knowledge = {
            "nodes": [
                {"id": "fact-1", "type": "fact", "status": "active", "summary": "A fact."},
                {"id": "task-1", "type": "effort", "status": "open", "summary": None},
            ],
            "edges": [{"source": "fact-1", "target": "task-1", "edge_type": "supports"}]
        }
        _save_knowledge(session_dir, knowledge)

        # Save modified efforts
        efforts = [{"id": "task-1", "status": "concluded", "summary": "Done."}]
        _save_efforts(session_dir, efforts)

        knowledge = _load_knowledge(session_dir)
        fact = next(n for n in knowledge["nodes"] if n["type"] == "fact")
        assert fact["id"] == "fact-1"
        assert fact["status"] == "active"

        effort = next(n for n in knowledge["nodes"] if n["type"] == "effort")
        assert effort["status"] == "concluded"

        # Edges preserved
        assert len(knowledge["edges"]) == 1
