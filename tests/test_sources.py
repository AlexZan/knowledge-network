"""Tests for source registry (Slice 14a)."""

import pytest
from pathlib import Path


class TestLoadSaveSources:
    def test_load_empty_when_no_file(self, tmp_path):
        from oi.sources import load_sources
        assert load_sources(tmp_path) == []

    def test_save_and_load_roundtrip(self, tmp_path):
        from oi.sources import save_sources, load_sources
        sources = [{"id": "my-docs", "type": "doc_root", "path": "/some/path", "label": "My Docs"}]
        save_sources(tmp_path, sources)
        loaded = load_sources(tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "my-docs"


class TestRegisterSource:
    def test_register_new_source(self, tmp_path):
        from oi.sources import register_source, load_sources
        result = register_source(tmp_path, id="my-docs", type="doc_root", path=str(tmp_path))
        assert result["status"] == "registered"
        assert result["source_id"] == "my-docs"
        assert len(load_sources(tmp_path)) == 1

    def test_register_same_source_idempotent(self, tmp_path):
        from oi.sources import register_source
        register_source(tmp_path, id="my-docs", type="doc_root", path=str(tmp_path))
        result = register_source(tmp_path, id="my-docs", type="doc_root", path=str(tmp_path))
        assert result["status"] == "exists"

    def test_register_conflict_different_path(self, tmp_path):
        from oi.sources import register_source
        other = tmp_path / "other"
        other.mkdir()
        register_source(tmp_path, id="my-docs", type="doc_root", path=str(tmp_path))
        result = register_source(tmp_path, id="my-docs", type="doc_root", path=str(other))
        assert result["status"] == "conflict"
        assert "error" in result

    def test_register_multiple_sources(self, tmp_path):
        from oi.sources import register_source, load_sources
        d1 = tmp_path / "d1"; d1.mkdir()
        d2 = tmp_path / "d2"; d2.mkdir()
        register_source(tmp_path, id="source-a", type="doc_root", path=str(d1))
        register_source(tmp_path, id="source-b", type="doc_root", path=str(d2))
        sources = load_sources(tmp_path)
        assert len(sources) == 2
        assert {s["id"] for s in sources} == {"source-a", "source-b"}

    def test_register_stores_label(self, tmp_path):
        from oi.sources import register_source, get_source
        register_source(tmp_path, id="my-docs", type="doc_root", path=str(tmp_path), label="My Docs")
        source = get_source(tmp_path, "my-docs")
        assert source["label"] == "My Docs"


class TestGetSource:
    def test_get_registered_source(self, tmp_path):
        from oi.sources import register_source, get_source
        register_source(tmp_path, id="my-docs", type="doc_root", path=str(tmp_path))
        source = get_source(tmp_path, "my-docs")
        assert source is not None
        assert source["id"] == "my-docs"

    def test_get_missing_source_returns_none(self, tmp_path):
        from oi.sources import get_source
        assert get_source(tmp_path, "nonexistent") is None


class TestBuildUris:
    def test_build_doc_uri(self):
        from oi.sources import build_doc_uri
        uri = build_doc_uri("my-docs", "docs/thesis.md")
        assert uri == "doc://my-docs/docs/thesis.md"

    def test_build_doc_uri_with_fragment(self):
        from oi.sources import build_doc_uri
        uri = build_doc_uri("my-docs", "docs/thesis.md", fragment="abstract")
        assert uri == "doc://my-docs/docs/thesis.md#abstract"

    def test_build_doc_uri_normalizes_backslashes(self):
        from oi.sources import build_doc_uri
        uri = build_doc_uri("my-docs", "docs\\thesis.md")
        assert uri == "doc://my-docs/docs/thesis.md"

    def test_build_chatgpt_uri(self):
        from oi.sources import build_chatgpt_uri
        uri = build_chatgpt_uri("physics-chatgpt", "6966425b-18fc-8332-aef9-ba73d13742bd")
        assert uri == "chatgpt://physics-chatgpt/6966425b-18fc-8332-aef9-ba73d13742bd"


class TestRewriteDocUri:
    def test_rewrite_legacy_uri(self):
        from oi.sources import rewrite_doc_uri
        uri = rewrite_doc_uri("doc://thesis.md#abstract", "my-docs")
        assert uri == "doc://my-docs/thesis.md#abstract"

    def test_rewrite_already_logical_is_idempotent(self):
        from oi.sources import rewrite_doc_uri
        uri = "doc://my-docs/thesis.md#abstract"
        assert rewrite_doc_uri(uri, "my-docs") == uri

    def test_rewrite_non_doc_uri_unchanged(self):
        from oi.sources import rewrite_doc_uri
        uri = "chatlog://claude-code/abc123:L42"
        assert rewrite_doc_uri(uri, "my-docs") == uri

    def test_rewrite_empty_uri_unchanged(self):
        from oi.sources import rewrite_doc_uri
        assert rewrite_doc_uri("", "my-docs") == ""


class TestResolveUri:
    def test_resolve_doc_uri(self, tmp_path):
        from oi.sources import register_source, resolve_uri
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        register_source(tmp_path, id="my-docs", type="doc_root", path=str(docs_dir))
        result = resolve_uri("doc://my-docs/thesis.md#section", tmp_path)
        assert result is not None
        assert result["source_id"] == "my-docs"
        assert result["source_type"] == "doc_root"
        assert result["relative_ref"] == "thesis.md"
        assert result["fragment"] == "section"
        assert result["physical_path"] == docs_dir / "thesis.md"

    def test_resolve_chatgpt_uri(self, tmp_path):
        from oi.sources import register_source, resolve_uri
        export = tmp_path / "conversations.json"
        export.touch()
        register_source(tmp_path, id="physics-chatgpt", type="chatgpt_export", path=str(export))
        result = resolve_uri("chatgpt://physics-chatgpt/6966425b-18fc-8332", tmp_path)
        assert result is not None
        assert result["source_id"] == "physics-chatgpt"
        assert result["relative_ref"] == "6966425b-18fc-8332"
        assert result["physical_path"] == export  # chatgpt: physical_path is the file itself

    def test_resolve_unregistered_source_returns_none(self, tmp_path):
        from oi.sources import resolve_uri
        assert resolve_uri("doc://nonexistent/file.md", tmp_path) is None

    def test_resolve_unsupported_scheme_returns_none(self, tmp_path):
        from oi.sources import resolve_uri
        assert resolve_uri("chatlog://claude-code/abc:L5", tmp_path) is None

    def test_resolve_empty_uri_returns_none(self, tmp_path):
        from oi.sources import resolve_uri
        assert resolve_uri("", tmp_path) is None


class TestParseFileWithSourceId:
    def test_parse_file_with_source_id_uses_logical_uri(self, tmp_path):
        from oi.parser import parse_file
        md = tmp_path / "notes.md"
        md.write_text("# Hello\n\nSome content here.\n")
        doc = parse_file(md, source_id="my-docs")
        assert doc.metadata.provenance_uri.startswith("doc://my-docs/")
        for chunk in doc.chunks:
            assert chunk.provenance_uri.startswith("doc://my-docs/")

    def test_parse_file_without_source_id_backwards_compat(self, tmp_path):
        from oi.parser import parse_file
        md = tmp_path / "notes.md"
        md.write_text("# Hello\n\nSome content here.\n")
        doc = parse_file(md)
        # Legacy: doc://{filename} with no source prefix
        assert doc.metadata.provenance_uri.startswith("doc://")
        assert "my-docs" not in doc.metadata.provenance_uri

    def test_chunk_provenance_uri_rewritten_not_chunk_id(self, tmp_path):
        """provenance_uri gets source prefix; chunk_id is an internal identifier."""
        from oi.parser import parse_file
        md = tmp_path / "notes.md"
        md.write_text("# Section One\n\nContent.\n\n# Section Two\n\nMore.\n")
        doc = parse_file(md, source_id="my-source")
        for chunk in doc.chunks:
            assert chunk.provenance_uri.startswith("doc://my-source/")
            # chunk_id is internal path format — not expected to have URI scheme
            assert "my-source" not in chunk.chunk_id or chunk.chunk_id.startswith("doc://my-source/")
