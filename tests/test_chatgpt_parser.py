"""Tests for ChatGPT export parser (Slice 13f)."""

import json
import zipfile
from pathlib import Path

import pytest

from oi.chatgpt_parser import (
    _linearize_conversation,
    _extract_text,
    _extract_canvas,
    _epoch_to_iso,
    parse_chatgpt_conversation,
    parse_chatgpt_file,
    parse_chatgpt_export,
)


# === Helpers ===


def _node(node_id, role=None, text="", parent=None, children=None, create_time=None):
    """Build a mapping node. If role is None, message is null (structural node)."""
    if role is not None:
        message = {
            "id": node_id,
            "author": {"role": role},
            "content": {"content_type": "text", "parts": [text]},
        }
        if create_time is not None:
            message["create_time"] = create_time
    else:
        message = None
    return {
        "id": node_id,
        "message": message,
        "parent": parent,
        "children": children or [],
    }


def _simple_conv(conv_id="conv-1", title="My Chat", turns=None):
    """Build a minimal conversation dict with the given turn pairs."""
    if turns is None:
        turns = [("Hello", "Hi there")]

    # Build mapping: root → (user → assistant) × N
    mapping = {}
    mapping["root"] = _node("root", parent=None)

    prev = "root"
    last = "root"
    for n, (user_text, asst_text) in enumerate(turns):
        user_id = f"user-{n}"
        asst_id = f"asst-{n}"
        mapping[user_id] = _node(user_id, role="user", text=user_text, parent=prev)
        mapping[asst_id] = _node(asst_id, role="assistant", text=asst_text, parent=user_id)
        prev = asst_id
        last = asst_id

    return {
        "id": conv_id,
        "title": title,
        "mapping": mapping,
        "current_node": last,
    }


# === Tests ===


class TestLinearizeConversation:
    def test_linearize_simple_conversation(self):
        """3-node chain returns messages in chronological order."""
        mapping = {
            "root": _node("root", parent=None),
            "n1": _node("n1", role="user", text="Hello", parent="root"),
            "n2": _node("n2", role="assistant", text="Hi", parent="n1"),
        }
        messages = _linearize_conversation(mapping, "n2")
        roles = [(m.get("author") or {}).get("role") for m in messages]
        # root has null message, so only user and assistant appear
        assert roles == ["user", "assistant"]
        texts = [(m.get("content") or {}).get("parts", [""])[0] for m in messages]
        assert texts[0] == "Hello"
        assert texts[1] == "Hi"

    def test_linearize_branched_follows_current_node(self):
        """Branched conversation: only the branch leading to current_node is returned."""
        mapping = {
            "root": _node("root", parent=None),
            "user1": _node("user1", role="user", text="Q", parent="root"),
            "asst-main": _node("asst-main", role="assistant", text="Main branch", parent="user1"),
            "asst-alt": _node("asst-alt", role="assistant", text="Alt branch", parent="user1"),
        }
        # current_node is the main branch
        messages = _linearize_conversation(mapping, "asst-main")
        roles = [(m.get("author") or {}).get("role") for m in messages]
        texts = [(m.get("content") or {}).get("parts", [""])[0] for m in messages]

        assert "user" in roles
        assert "assistant" in roles
        assert "Main branch" in texts
        assert "Alt branch" not in texts


class TestExtractText:
    def test_extract_text_joins_parts(self):
        """Multi-part content is joined with double newlines."""
        msg = {"content": {"parts": ["First part", "Second part"]}}
        result = _extract_text(msg)
        assert "First part" in result
        assert "Second part" in result

    def test_extract_text_skips_empty_parts(self):
        """Empty string parts are excluded from output."""
        msg = {"content": {"parts": ["", "Real content", ""]}}
        assert _extract_text(msg) == "Real content"

    def test_extract_text_null_content(self):
        """Null content returns empty string."""
        msg = {"content": None}
        assert _extract_text(msg) == ""


class TestParseConversation:
    def test_parse_conversation_creates_turn_pair_chunks(self):
        """2 user+assistant exchanges → 2 chunks."""
        conv = _simple_conv(turns=[
            ("Question one", "Answer one"),
            ("Question two", "Answer two"),
        ])
        doc = parse_chatgpt_conversation(conv, source_id="test-src")
        assert len(doc.chunks) == 2
        assert "Question one" in doc.chunks[0].content
        assert "Answer one" in doc.chunks[0].content
        assert "Question two" in doc.chunks[1].content

    def test_parse_conversation_skips_empty_messages(self):
        """Turn pairs where both user and assistant text are empty are skipped."""
        conv = _simple_conv(conv_id="conv-empty")
        # Replace the user message with an empty-parts message
        conv["mapping"]["user-0"]["message"]["content"]["parts"] = [""]
        conv["mapping"]["asst-0"]["message"]["content"]["parts"] = [""]
        doc = parse_chatgpt_conversation(conv, source_id="test-src")
        assert len(doc.chunks) == 0

    def test_parse_conversation_provenance_uri_format(self):
        """Document and chunk provenance URIs follow chatgpt:// scheme."""
        conv = _simple_conv(conv_id="abc-123")
        doc = parse_chatgpt_conversation(conv, source_id="my-source")
        assert doc.metadata.provenance_uri == "chatgpt://my-source/abc-123"
        assert doc.chunks[0].provenance_uri == "chatgpt://my-source/abc-123#turn-0"
        assert doc.chunks[0].chunk_id == "chatgpt://my-source/abc-123#turn-0"

    def test_parse_conversation_untitled_fallback(self):
        """Blank title falls back to 'Untitled {conv_id[:8]}'."""
        conv = _simple_conv(conv_id="abcd1234xyz", title="")
        doc = parse_chatgpt_conversation(conv, source_id="src")
        assert doc.metadata.title == "Untitled abcd1234"

    def test_parse_conversation_heading_path(self):
        """Chunk heading_path contains conversation title and turn label."""
        conv = _simple_conv(title="Physics Discussion")
        doc = parse_chatgpt_conversation(conv, source_id="src")
        assert doc.chunks[0].heading_path == ["Physics Discussion", "Turn 1"]


def _canvas_node(node_id, name, content, parent=None):
    """Build a mapping node containing a canvas document."""
    return {
        "id": node_id,
        "message": {
            "id": node_id,
            "author": {"role": "assistant"},
            "content": {
                "content_type": "code",
                "language": "unknown",
                "response_format_name": "document",
                "text": json.dumps({"name": name, "type": "document", "content": content}),
            },
        },
        "parent": parent,
        "children": [],
    }


class TestExtractCanvas:
    def test_extract_canvas_returns_name_and_content(self):
        """Valid canvas message returns (name, content) tuple."""
        msg = {
            "content": {
                "content_type": "code",
                "text": json.dumps({
                    "name": "Binary Growth Law",
                    "type": "document",
                    "content": "# Binary Growth Law\n\nContent here.",
                }),
            }
        }
        result = _extract_canvas(msg)
        assert result is not None
        name, content = result
        assert name == "Binary Growth Law"
        assert "Content here" in content

    def test_extract_canvas_returns_none_for_text_message(self):
        """Regular text messages return None."""
        msg = {"content": {"content_type": "text", "parts": ["Hello"]}}
        assert _extract_canvas(msg) is None

    def test_extract_canvas_returns_none_for_non_document_code(self):
        """Code messages with non-document JSON return None."""
        msg = {
            "content": {
                "content_type": "code",
                "text": json.dumps({"type": "search_query", "queries": ["foo"]}),
            }
        }
        assert _extract_canvas(msg) is None


class TestParseConversationWithCanvas:
    def test_canvas_becomes_separate_chunk(self):
        """Canvas document in a conversation produces its own chunk."""
        mapping = {
            "root": _node("root", parent=None),
            "user1": _node("user1", role="user", text="Write a spec", parent="root"),
            "canvas1": _canvas_node("canvas1", "My Spec", "# Spec\nContent.", parent="user1"),
        }
        conv = {
            "id": "conv-1",
            "title": "Test",
            "mapping": mapping,
            "current_node": "canvas1",
        }
        doc = parse_chatgpt_conversation(conv, source_id="src")
        canvas_chunks = [c for c in doc.chunks if "canvas" in c.chunk_id]
        assert len(canvas_chunks) == 1
        assert canvas_chunks[0].heading == "My Spec"
        assert "# Spec" in canvas_chunks[0].content

    def test_canvas_only_assistant_response_skips_turn_pair(self):
        """User + canvas-only assistant creates no turn pair chunk (just canvas)."""
        mapping = {
            "root": _node("root", parent=None),
            "user1": _node("user1", role="user", text="Create document", parent="root"),
            "canvas1": _canvas_node("canvas1", "Doc", "# Doc\nBody.", parent="user1"),
        }
        conv = {
            "id": "conv-1",
            "title": "Test",
            "mapping": mapping,
            "current_node": "canvas1",
        }
        doc = parse_chatgpt_conversation(conv, source_id="src")
        turn_chunks = [c for c in doc.chunks if "turn" in c.chunk_id]
        canvas_chunks = [c for c in doc.chunks if "canvas" in c.chunk_id]
        assert len(turn_chunks) == 0
        assert len(canvas_chunks) == 1

    def test_canvas_provenance_uri_format(self):
        """Canvas chunks use #canvas-N fragment in URI."""
        mapping = {
            "root": _node("root", parent=None),
            "user1": _node("user1", role="user", text="Q", parent="root"),
            "canvas1": _canvas_node("canvas1", "Doc", "Body.", parent="user1"),
        }
        conv = {"id": "abc-123", "title": "T", "mapping": mapping, "current_node": "canvas1"}
        doc = parse_chatgpt_conversation(conv, source_id="my-src")
        canvas = doc.chunks[0]
        assert canvas.provenance_uri == "chatgpt://my-src/abc-123#canvas-0"
        assert canvas.chunk_id == "chatgpt://my-src/abc-123#canvas-0"


class TestParseChatGPTFile:
    def test_parse_single_conversation_json(self, tmp_path):
        """Single conversation JSON file parsed correctly via parse_chatgpt_file."""
        conv = _simple_conv(conv_id="test-id", title="Test Chat")
        json_path = tmp_path / "test-id.json"
        json_path.write_text(json.dumps(conv), encoding="utf-8")

        doc = parse_chatgpt_file(json_path, source_id="my-source")
        assert doc.metadata.title == "Test Chat"
        assert doc.metadata.source_path == "test-id"
        assert doc.chunks

    def test_parse_file_detects_chatgpt_json(self, tmp_path):
        """parse_file auto-detects chatgpt JSON from .json extension + content."""
        from oi.parser import parse_file
        conv = _simple_conv(conv_id="auto-id", title="Auto Detected")
        json_path = tmp_path / "auto-id.json"
        json_path.write_text(json.dumps(conv), encoding="utf-8")

        doc = parse_file(json_path, source_id="test-src")
        assert doc.metadata.format == "chatgpt"
        assert doc.metadata.title == "Auto Detected"
        assert doc.chunks


class TestParseExport:
    def test_parse_export_title_filter(self, tmp_path):
        """Keyword filter selects only matching conversations."""
        convs = [
            _simple_conv(conv_id="c1", title="Quantum gravity theory"),
            _simple_conv(conv_id="c2", title="Weekend plans"),
            _simple_conv(conv_id="c3", title="Quantum field equations"),
        ]
        json_path = tmp_path / "conversations.json"
        json_path.write_text(json.dumps(convs), encoding="utf-8")

        results = parse_chatgpt_export(json_path, source_id="src", title_filter="quantum")
        assert len(results) == 2
        titles = [d.metadata.title for d in results]
        assert all("quantum" in t.lower() or "Quantum" in t for t in titles)

    def test_parse_export_chatgpt_project_id_filter(self, tmp_path):
        """chatgpt_project_id selects only conversations from that project."""
        convs = [
            {**_simple_conv(conv_id="c1", title="Physics theory"), "gizmo_id": "g-p-abc123"},
            {**_simple_conv(conv_id="c2", title="Weekend plans"),  "gizmo_id": "g-p-other"},
            {**_simple_conv(conv_id="c3", title="More physics"),   "gizmo_id": "g-p-abc123"},
        ]
        json_path = tmp_path / "conversations.json"
        json_path.write_text(json.dumps(convs), encoding="utf-8")

        results = parse_chatgpt_export(
            json_path, source_id="src", chatgpt_project_id="g-p-abc123"
        )
        assert len(results) == 2
        ids = {d.metadata.source_path for d in results}
        assert ids == {"c1", "c3"}

    def test_parse_export_from_zip(self, tmp_path):
        """Zip file is extracted and conversations.json parsed correctly."""
        convs = [
            _simple_conv(conv_id="z1", title="Zip conversation"),
        ]
        json_path = tmp_path / "conversations.json"
        json_path.write_text(json.dumps(convs), encoding="utf-8")

        zip_path = tmp_path / "export.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(json_path, "conversations.json")

        results = parse_chatgpt_export(zip_path, source_id="src")
        assert len(results) == 1
        assert results[0].metadata.title == "Zip conversation"
        assert results[0].chunks  # has at least one chunk


# === Tests for authored_at / create_time propagation ===


class TestEpochToIso:
    def test_converts_epoch_to_iso(self):
        """Known epoch converts to expected ISO 8601 string."""
        # 2025-06-15 12:00:00 UTC
        result = _epoch_to_iso(1750003200.0)
        assert result.startswith("2025-06-15")
        assert "T" in result

    def test_none_returns_empty(self):
        assert _epoch_to_iso(None) == ""

    def test_invalid_returns_empty(self):
        assert _epoch_to_iso("not-a-number") == ""


class TestAuthoredAtOnChunks:
    def test_turn_pair_has_authored_at(self):
        """Turn pair chunk gets authored_at from user message create_time."""
        mapping = {
            "root": _node("root", parent=None),
            "u1": _node("u1", role="user", text="Hello", parent="root", create_time=1750003200.0),
            "a1": _node("a1", role="assistant", text="Hi", parent="u1", create_time=1750075260.0),
        }
        conv = {"id": "c1", "title": "T", "mapping": mapping, "current_node": "a1"}
        doc = parse_chatgpt_conversation(conv, source_id="src")
        assert len(doc.chunks) == 1
        assert "authored_at" in doc.chunks[0].metadata
        assert doc.chunks[0].metadata["authored_at"].startswith("2025-06-15")

    def test_no_create_time_means_no_authored_at(self):
        """Chunks without create_time on messages have empty metadata."""
        conv = _simple_conv()
        doc = parse_chatgpt_conversation(conv, source_id="src")
        assert doc.chunks[0].metadata.get("authored_at") is None

    def test_conversation_date_from_create_time(self):
        """DocumentMetadata.date is set from conversation-level create_time."""
        conv = _simple_conv()
        conv["create_time"] = 1750003200.0  # 2025-06-15 UTC
        doc = parse_chatgpt_conversation(conv, source_id="src")
        assert doc.metadata.date is not None
        assert str(doc.metadata.date) == "2025-06-15"

    def test_conversation_without_create_time_no_date(self):
        """No create_time on conversation → date remains None."""
        conv = _simple_conv()
        doc = parse_chatgpt_conversation(conv, source_id="src")
        assert doc.metadata.date is None
