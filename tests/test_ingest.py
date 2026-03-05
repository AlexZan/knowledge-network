"""Tests for document ingestion (Slices 13b, 13e)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from oi.ingest import (
    ExtractedClaim,
    ChunkExtractionResult,
    DocumentExtractionResult,
    IngestionResult,
    PipelineResult,
    _build_extraction_prompt,
    _get_ingested_conv_ids,
    _parse_llm_json,
    extract_from_chunk,
    extract_document,
    ingest_document,
    ingest_pipeline,
)
from oi.parser import DocumentChunk, DocumentMetadata, ParsedDocument


# Disable embeddings globally for this module
@pytest.fixture(autouse=True)
def _no_embed():
    with patch("oi.embed.get_embedding", return_value=None):
        yield


# === Helpers ===


def _make_chunk(
    chunk_id="doc.md#intro",
    content="Some content here.",
    heading="Introduction",
    heading_path=None,
    provenance_uri="doc://doc.md#intro",
    char_count=None,
):
    if heading_path is None:
        heading_path = ["Introduction"]
    if char_count is None:
        char_count = len(content)
    return DocumentChunk(
        chunk_id=chunk_id,
        content=content,
        heading=heading,
        heading_path=heading_path,
        provenance_uri=provenance_uri,
        char_count=char_count,
    )


def _make_doc(chunks=None, title="Test Doc", source_path="docs/test.md"):
    if chunks is None:
        chunks = [_make_chunk()]
    return ParsedDocument(
        metadata=DocumentMetadata(
            title=title,
            source_path=source_path,
            format="markdown",
            provenance_uri=f"doc://{source_path}",
        ),
        chunks=chunks,
        total_chars=sum(c.char_count for c in chunks),
    )


def _llm_response(claims):
    """Build a mock LLM response JSON string from claim dicts."""
    return json.dumps(claims)


# === Phase 1: Models ===


class TestModels:
    def test_extracted_claim_fields(self):
        claim = ExtractedClaim(
            node_type="fact",
            summary="Python uses indentation",
            provenance_uri="doc://test.md#intro",
            source_path="docs/test.md",
            reasoning="Core language feature",
        )
        assert claim.node_type == "fact"
        assert claim.summary == "Python uses indentation"
        assert claim.provenance_uri == "doc://test.md#intro"
        assert claim.source_path == "docs/test.md"

    def test_extracted_claim_default_reasoning(self):
        claim = ExtractedClaim(
            node_type="decision",
            summary="Use REST",
            provenance_uri="doc://x.md#api",
            source_path="x.md",
        )
        assert claim.reasoning == ""

    def test_chunk_extraction_result_success(self):
        r = ChunkExtractionResult(chunk_id="doc.md#intro", claims=[])
        assert r.error is None
        assert r.claims == []

    def test_chunk_extraction_result_error(self):
        r = ChunkExtractionResult(chunk_id="doc.md#intro", error="LLM timeout")
        assert r.error == "LLM timeout"

    def test_document_extraction_result(self):
        r = DocumentExtractionResult(
            source_path="docs/test.md",
            chunks_total=5,
            chunks_processed=3,
            chunks_skipped=1,
            chunks_failed=1,
            claims=[],
            errors=["chunk3: timeout"],
        )
        assert r.chunks_total == 5
        assert r.chunks_failed == 1

    def test_ingestion_result(self):
        r = IngestionResult(
            source_path="docs/test.md",
            nodes_created=["fact-001", "fact-002"],
            chunks_total=3,
            chunks_processed=3,
            chunks_failed=0,
            claims_extracted=2,
        )
        assert len(r.nodes_created) == 2
        assert r.errors == []


# === Phase 1: _build_extraction_prompt ===


class TestBuildExtractionPrompt:
    def test_basic_prompt(self):
        chunk = _make_chunk()
        msgs = _build_extraction_prompt(chunk, "Document: Test\n")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert "JSON array" in msgs[0]["content"]
        assert "Document: Test" in msgs[1]["content"]
        assert chunk.content in msgs[1]["content"]

    def test_heading_path_in_prompt(self):
        chunk = _make_chunk(heading_path=["Chapter 1", "Introduction"])
        msgs = _build_extraction_prompt(chunk, "")
        assert "Chapter 1 > Introduction" in msgs[1]["content"]

    def test_provenance_in_prompt(self):
        chunk = _make_chunk(provenance_uri="doc://thesis.md#abstract")
        msgs = _build_extraction_prompt(chunk, "")
        assert "doc://thesis.md#abstract" in msgs[1]["content"]

    def test_no_heading_context(self):
        chunk = _make_chunk(heading=None, heading_path=[])
        msgs = _build_extraction_prompt(chunk, "")
        assert "Section path:" not in msgs[1]["content"]
        assert "Section:" not in msgs[1]["content"]


# === JSON Parsing Robustness ===


class TestParseLlmJson:
    """Tests for _parse_llm_json — LLM output sanitization and repair."""

    def test_clean_json_passes_through(self):
        result = _parse_llm_json('[{"a": 1}, {"b": 2}]')
        assert result == [{"a": 1}, {"b": 2}]

    def test_strips_markdown_fences(self):
        text = '```json\n[{"a": 1}]\n```'
        assert _parse_llm_json(text) == [{"a": 1}]

    def test_strips_control_characters(self):
        # \x08 (backspace) inside a JSON string value
        text = '[{"summary": "hello\x08world"}]'
        result = _parse_llm_json(text)
        assert result[0]["summary"] == "helloworld"

    def test_preserves_newlines_and_tabs(self):
        text = '[{"summary": "line1\\nline2\\ttab"}]'
        result = _parse_llm_json(text)
        assert "line1\nline2\ttab" in result[0]["summary"]

    def test_repairs_truncated_array(self):
        # LLM output cut off mid-object — last complete object should survive
        text = '[{"a": 1}, {"b": 2}, {"c": 3'
        result = _parse_llm_json(text)
        assert len(result) == 2
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}

    def test_repairs_truncated_after_comma(self):
        text = '[{"a": 1}, {"b": 2},'
        result = _parse_llm_json(text)
        assert len(result) == 2

    def test_repairs_truncated_mid_value(self):
        # Truncated inside a string value
        text = '[{"a": 1}, {"b": "hello wor'
        result = _parse_llm_json(text)
        assert len(result) == 1
        assert result[0] == {"a": 1}

    def test_combined_fences_control_chars_truncation(self):
        text = '```json\n[{"s": "ok\x08"}, {"s": "trunc'
        result = _parse_llm_json(text)
        assert len(result) == 1
        assert result[0] == {"s": "ok"}

    def test_empty_array(self):
        assert _parse_llm_json("[]") == []

    def test_hopelessly_broken_raises(self):
        with pytest.raises(Exception):
            _parse_llm_json("this is not json at all")

    def test_single_complete_object_truncated(self):
        # Only one object, and it's truncated — nothing salvageable
        text = '[{"a": "hello wor'
        with pytest.raises(Exception):
            _parse_llm_json(text)


# === Phase 1: extract_from_chunk ===


class TestExtractFromChunk:
    @patch("oi.ingest.chat")
    def test_extracts_valid_claims(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Python is interpreted", "reasoning": "Core fact"},
            {"node_type": "decision", "summary": "Use pytest for testing", "reasoning": "Standard"},
        ])
        chunk = _make_chunk(content="Python is an interpreted language. We use pytest.")
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.error is None
        assert len(result.claims) == 2
        assert result.claims[0].node_type == "fact"
        assert result.claims[0].summary == "Python is interpreted"
        assert result.claims[0].provenance_uri == chunk.provenance_uri
        assert result.claims[0].source_path == "docs/test.md"

    @patch("oi.ingest.chat")
    def test_filters_invalid_node_types(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Valid claim"},
            {"node_type": "banana", "summary": "Invalid type"},
            {"node_type": "effort", "summary": "Not extractable"},
        ])
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert len(result.claims) == 1
        assert result.claims[0].node_type == "fact"

    @patch("oi.ingest.chat")
    def test_filters_empty_summaries(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": ""},
            {"node_type": "fact", "summary": "   "},
            {"node_type": "fact", "summary": "Valid"},
        ])
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert len(result.claims) == 1
        assert result.claims[0].summary == "Valid"

    @patch("oi.ingest.chat")
    def test_handles_json_parse_error(self, mock_chat):
        mock_chat.return_value = "not json at all"
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.error is not None
        assert "JSON parse error" in result.error
        assert result.claims == []

    @patch("oi.ingest.chat")
    def test_handles_llm_exception(self, mock_chat):
        mock_chat.side_effect = RuntimeError("API down")
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.error is not None
        assert "LLM call failed" in result.error

    @patch("oi.ingest.chat")
    def test_handles_non_array_response(self, mock_chat):
        mock_chat.return_value = '{"not": "an array"}'
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.error is not None
        assert "non-array" in result.error

    def test_empty_chunk_returns_no_claims(self):
        chunk = _make_chunk(content="", char_count=0)
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.error is None
        assert result.claims == []

    @patch("oi.ingest.chat")
    def test_strips_markdown_fences(self, mock_chat):
        mock_chat.return_value = '```json\n[{"node_type": "fact", "summary": "Fenced"}]\n```'
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert len(result.claims) == 1
        assert result.claims[0].summary == "Fenced"

    @patch("oi.ingest.chat")
    def test_preserves_reasoning(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "X", "reasoning": "Important because Y"},
        ])
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.claims[0].reasoning == "Important because Y"

    @patch("oi.ingest.chat")
    def test_handles_missing_reasoning(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "No reasoning here"},
        ])
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.claims[0].reasoning == ""

    @patch("oi.ingest.chat")
    def test_skips_non_dict_items(self, mock_chat):
        mock_chat.return_value = json.dumps([
            "just a string",
            42,
            {"node_type": "fact", "summary": "Valid"},
        ])
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert len(result.claims) == 1

    @patch("oi.ingest.chat")
    def test_passes_model_to_chat(self, mock_chat):
        mock_chat.return_value = "[]"
        chunk = _make_chunk()
        extract_from_chunk(chunk, "docs/test.md", model="test-model")
        mock_chat.assert_called_once()
        assert mock_chat.call_args[1]["model"] == "test-model"

    @patch("oi.ingest.chat")
    def test_metadata_context_in_prompt(self, mock_chat):
        mock_chat.return_value = "[]"
        chunk = _make_chunk()
        extract_from_chunk(chunk, "docs/test.md", metadata_context="Document: Thesis\n")
        call_msgs = mock_chat.call_args[0][0]
        assert "Document: Thesis" in call_msgs[1]["content"]

    @patch("oi.ingest.chat")
    def test_empty_array_response(self, mock_chat):
        mock_chat.return_value = "[]"
        chunk = _make_chunk()
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.error is None
        assert result.claims == []

    @patch("oi.ingest.chat")
    def test_whitespace_only_content_skipped(self, mock_chat):
        chunk = _make_chunk(content="   \n\n  ", char_count=8)
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.claims == []
        mock_chat.assert_not_called()

    @patch("oi.ingest.chat")
    def test_authored_at_propagated_from_chunk_metadata(self, mock_chat):
        """Chunk metadata authored_at is copied to extracted claims."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        chunk = _make_chunk(content="Some content")
        chunk.metadata = {"authored_at": "2025-06-15T12:00:00+00:00"}
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.claims[0].authored_at == "2025-06-15T12:00:00+00:00"

    @patch("oi.ingest.chat")
    def test_authored_at_empty_when_no_metadata(self, mock_chat):
        """Claims have empty authored_at when chunk has no metadata."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        chunk = _make_chunk(content="Some content")
        result = extract_from_chunk(chunk, "docs/test.md")
        assert result.claims[0].authored_at == ""


# === Phase 2: extract_document ===


class TestExtractDocument:
    @patch("oi.ingest.chat")
    def test_extracts_from_all_chunks(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Claim from chunk"},
        ])
        doc = _make_doc(chunks=[
            _make_chunk(chunk_id="doc.md#a", content="Chunk A content", provenance_uri="doc://doc.md#a"),
            _make_chunk(chunk_id="doc.md#b", content="Chunk B content", provenance_uri="doc://doc.md#b"),
        ])
        result = extract_document(doc)
        assert result.chunks_total == 2
        assert result.chunks_processed == 2
        assert result.chunks_skipped == 0
        assert result.chunks_failed == 0
        assert len(result.claims) == 2

    @patch("oi.ingest.chat")
    def test_skips_empty_chunks(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Claim"},
        ])
        doc = _make_doc(chunks=[
            _make_chunk(chunk_id="doc.md#empty", content="", char_count=0),
            _make_chunk(chunk_id="doc.md#real", content="Real content"),
        ])
        result = extract_document(doc)
        assert result.chunks_total == 2
        assert result.chunks_skipped == 1
        assert result.chunks_processed == 1
        assert mock_chat.call_count == 1

    @patch("oi.ingest.chat")
    def test_accumulates_errors(self, mock_chat):
        responses = iter([
            _llm_response([{"node_type": "fact", "summary": "OK"}]),
            "not json",
        ])
        mock_chat.side_effect = lambda *a, **kw: next(responses)
        doc = _make_doc(chunks=[
            _make_chunk(chunk_id="doc.md#a", content="Good chunk"),
            _make_chunk(chunk_id="doc.md#b", content="Bad chunk"),
        ])
        result = extract_document(doc)
        assert result.chunks_processed == 1
        assert result.chunks_failed == 1
        assert len(result.errors) == 1
        assert "doc.md#b" in result.errors[0]
        assert len(result.claims) == 1

    @patch("oi.ingest.chat")
    def test_includes_metadata_context(self, mock_chat):
        mock_chat.return_value = "[]"
        doc = _make_doc(title="My Thesis")
        doc.metadata.author = "Alice"
        extract_document(doc)
        call_msgs = mock_chat.call_args[0][0]
        assert "My Thesis" in call_msgs[1]["content"]
        assert "Alice" in call_msgs[1]["content"]

    @patch("oi.ingest.chat")
    def test_empty_document(self, mock_chat):
        doc = _make_doc(chunks=[])
        result = extract_document(doc)
        assert result.chunks_total == 0
        assert result.chunks_processed == 0
        assert result.claims == []
        mock_chat.assert_not_called()

    @patch("oi.ingest.chat")
    def test_preserves_provenance_per_claim(self, mock_chat):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Claim"},
        ])
        doc = _make_doc(chunks=[
            _make_chunk(
                chunk_id="doc.md#specific",
                content="Content",
                provenance_uri="doc://doc.md#specific",
            ),
        ])
        result = extract_document(doc)
        assert result.claims[0].provenance_uri == "doc://doc.md#specific"
        assert result.claims[0].source_path == "docs/test.md"


# === Phase 4: ingest_document ===


class TestIngestDocument:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    @patch("oi.ingest.chat")
    def test_creates_nodes_in_kg(self, mock_chat, session_dir):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Extracted fact"},
            {"node_type": "decision", "summary": "Extracted decision"},
        ])
        doc = _make_doc(chunks=[_make_chunk(content="Some doc content")])
        result = ingest_document(doc, session_dir)
        assert len(result.nodes_created) == 2
        assert result.claims_extracted == 2
        assert result.errors == []

        # Verify nodes exist in KG
        from oi.state import _load_knowledge
        kg = _load_knowledge(session_dir)
        node_ids = {n["id"] for n in kg["nodes"]}
        assert "fact-001" in node_ids
        assert "decision-001" in node_ids

    @patch("oi.ingest.chat")
    def test_nodes_have_provenance(self, mock_chat, session_dir):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        doc = _make_doc(chunks=[
            _make_chunk(
                content="Content",
                provenance_uri="doc://thesis.md#abstract",
            ),
        ])
        result = ingest_document(doc, session_dir)
        from oi.state import _load_knowledge
        kg = _load_knowledge(session_dir)
        node = kg["nodes"][0]
        assert node["provenance_uri"] == "doc://thesis.md#abstract"

    @patch("oi.ingest.chat")
    def test_no_edges_created(self, mock_chat, session_dir):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Fact A"},
            {"node_type": "fact", "summary": "Fact B"},
        ])
        doc = _make_doc(chunks=[_make_chunk(content="Content")])
        ingest_document(doc, session_dir)
        from oi.state import _load_knowledge
        kg = _load_knowledge(session_dir)
        assert kg["edges"] == []

    @patch("oi.ingest.chat")
    def test_source_label(self, mock_chat, session_dir):
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        doc = _make_doc(chunks=[_make_chunk(content="Content")])
        ingest_document(doc, session_dir, source_label="thesis-v2")
        from oi.state import _load_knowledge
        kg = _load_knowledge(session_dir)
        assert kg["nodes"][0]["source"] == "thesis-v2"

    @patch("oi.ingest.chat")
    def test_sandbox_isolation(self, mock_chat, session_dir):
        """Ingestion into sandbox dir doesn't affect production."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Sandbox fact"},
        ])
        sandbox = session_dir / ".oi-test"
        sandbox.mkdir()
        doc = _make_doc(chunks=[_make_chunk(content="Content")])
        result = ingest_document(doc, sandbox)
        assert len(result.nodes_created) == 1

        # Sandbox has the node
        from oi.state import _load_knowledge
        sandbox_kg = _load_knowledge(sandbox)
        assert len(sandbox_kg["nodes"]) == 1

        # Production is untouched
        prod_kg = _load_knowledge(session_dir)
        assert len(prod_kg["nodes"]) == 0

    @patch("oi.ingest.chat")
    def test_handles_extraction_errors_gracefully(self, mock_chat, session_dir):
        responses = iter([
            "not json",
            _llm_response([{"node_type": "fact", "summary": "OK"}]),
        ])
        mock_chat.side_effect = lambda *a, **kw: next(responses)
        doc = _make_doc(chunks=[
            _make_chunk(chunk_id="doc.md#bad", content="Bad"),
            _make_chunk(chunk_id="doc.md#good", content="Good"),
        ])
        result = ingest_document(doc, session_dir)
        assert result.chunks_failed == 1
        assert result.chunks_processed == 1
        assert len(result.nodes_created) == 1
        assert len(result.errors) == 1

    @patch("oi.ingest.chat")
    def test_result_metadata(self, mock_chat, session_dir):
        mock_chat.return_value = "[]"
        doc = _make_doc(
            chunks=[
                _make_chunk(content=""),
                _make_chunk(content="Real"),
            ],
            source_path="docs/notes.md",
        )
        doc.chunks[0].char_count = 0
        result = ingest_document(doc, session_dir)
        assert result.source_path == "docs/notes.md"
        assert result.chunks_total == 2

    @patch("oi.ingest.chat")
    def test_authored_at_stored_on_node(self, mock_chat, session_dir):
        """authored_at from chunk metadata reaches the knowledge graph node."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        chunk = _make_chunk(content="Some content")
        chunk.metadata = {"authored_at": "2025-06-15T12:00:00+00:00"}
        doc = _make_doc(chunks=[chunk])
        ingest_document(doc, session_dir)

        from oi.state import _load_knowledge
        kg = _load_knowledge(session_dir)
        node = kg["nodes"][0]
        assert node["authored_at"] == "2025-06-15T12:00:00+00:00"

    @patch("oi.ingest.chat")
    def test_no_authored_at_when_chunk_lacks_metadata(self, mock_chat, session_dir):
        """Nodes don't have authored_at when chunk metadata is empty."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        doc = _make_doc(chunks=[_make_chunk(content="Content")])
        ingest_document(doc, session_dir)

        from oi.state import _load_knowledge
        kg = _load_knowledge(session_dir)
        node = kg["nodes"][0]
        assert "authored_at" not in node


# === Phase 6: ingest_pipeline ===


class TestIngestPipeline:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    @pytest.fixture
    def sample_md(self, tmp_path):
        f = tmp_path / "sample.md"
        f.write_text("# Title\n\nSome content about Python.\n")
        return f

    @patch("oi.ingest.chat")
    def test_dry_run_extracts_without_writing(self, mock_chat, session_dir, sample_md):
        """Dry-run returns claims but writes nothing to graph."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Python is popular"},
        ])
        result = ingest_pipeline(sample_md, session_dir, dry_run=True)
        assert result.dry_run is True
        assert result.claims_extracted == 1
        assert result.nodes_created == []
        assert result.edges_created == 0
        # No knowledge file should exist
        assert not (session_dir / "knowledge.yaml").exists()

    @patch("oi.ingest.chat")
    def test_full_pipeline_creates_nodes_and_links(self, mock_chat, session_dir, sample_md):
        """Full pipeline writes nodes, runs linking, and generates conflict report."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Python is interpreted"},
            {"node_type": "decision", "summary": "Use pytest for tests"},
        ])
        with patch("oi.linker.link_new_nodes") as mock_link, \
             patch("oi.embed.ensure_embeddings") as mock_embed:
            from oi.linker import LinkingResult
            mock_link.return_value = LinkingResult(
                edges_created=1, contradictions_found=0, nodes_processed=2,
            )
            result = ingest_pipeline(sample_md, session_dir, skip_embedding=True)

        assert result.dry_run is False
        assert len(result.nodes_created) == 2
        assert result.claims_extracted == 2
        assert result.edges_created == 1
        assert result.errors == []
        mock_embed.assert_not_called()

    @patch("oi.ingest.chat")
    def test_skip_linking_skips_edges(self, mock_chat, session_dir, sample_md):
        """skip_linking=True skips linking pass and conflict report."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"},
        ])
        with patch("oi.linker.link_new_nodes") as mock_link:
            result = ingest_pipeline(
                sample_md, session_dir, skip_linking=True, skip_embedding=True,
            )
        assert result.edges_created == 0
        assert result.conflicts == {}
        mock_link.assert_not_called()

    def test_unsupported_format_returns_error(self, session_dir, tmp_path):
        """Unsupported file extension returns graceful error."""
        bad = tmp_path / "data.xyz"
        bad.write_text("binary data")
        result = ingest_pipeline(bad, session_dir, skip_embedding=True)
        assert len(result.errors) >= 1
        assert any("Unsupported" in e for e in result.errors)
        assert result.nodes_created == []

    @patch("oi.ingest.chat")
    def test_empty_document_zero_claims(self, mock_chat, session_dir, tmp_path):
        """Empty markdown file extracts zero claims."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        result = ingest_pipeline(empty, session_dir, skip_embedding=True)
        assert result.claims_extracted == 0
        assert result.nodes_created == []
        mock_chat.assert_not_called()

    @patch("oi.ingest.chat")
    def test_progress_callback_called(self, mock_chat, session_dir, sample_md):
        """Progress callback receives stage notifications."""
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A claim"},
        ])
        stages = []
        with patch("oi.linker.link_new_nodes") as mock_link:
            from oi.linker import LinkingResult
            mock_link.return_value = LinkingResult(
                edges_created=0, contradictions_found=0, nodes_processed=1,
            )
            ingest_pipeline(
                sample_md, session_dir,
                skip_embedding=True,
                progress_fn=lambda stage, detail: stages.append(stage),
            )
        assert "parse" in stages
        assert "extract" in stages
        assert "write" in stages
        assert "done" in stages


    @patch("oi.ingest.chat")
    def test_source_id_produces_logical_uris(self, mock_chat, session_dir, tmp_path):
        """ingest_pipeline with source_id rewrites doc:// URIs to logical form."""
        md = tmp_path / "notes.md"
        md.write_text("# Topic\n\nSome content.\n")
        mock_chat.return_value = _llm_response([{"node_type": "fact", "summary": "Some content."}])

        with patch("oi.linker.link_new_nodes") as mock_link, \
             patch("oi.embed.ensure_embeddings"):
            from oi.linker import LinkingResult
            mock_link.return_value = LinkingResult(edges_created=0, contradictions_found=0, nodes_processed=1)
            result = ingest_pipeline(
                file_path=md,
                session_dir=session_dir,
                model="test-model",
                source_id="my-source",
                skip_embedding=True,
            )

        assert result.errors == []
        # Verify source was registered
        from oi.sources import get_source
        assert get_source(session_dir, "my-source") is not None
        # Verify nodes have logical URIs
        from oi.state import _load_knowledge
        knowledge = _load_knowledge(session_dir)
        nodes = [n for n in knowledge["nodes"] if n.get("type") == "fact"]
        assert len(nodes) > 0
        for node in nodes:
            assert node["provenance_uri"].startswith("doc://my-source/")

    def test_source_id_already_registered_uses_existing(self, session_dir, tmp_path):
        """ingest_pipeline skips auto-registration if source already registered."""
        from unittest.mock import patch
        from oi.sources import register_source, get_source
        register_source(session_dir, id="my-source", type="doc_root", path=str(tmp_path))

        md = tmp_path / "notes.md"
        md.write_text("# Topic\n\nContent.\n")

        with patch("oi.ingest.chat", return_value='```json\n[]\n```'), \
             patch("oi.linker.link_new_nodes") as mock_link, \
             patch("oi.embed.ensure_embeddings"):
            from oi.linker import LinkingResult
            mock_link.return_value = LinkingResult(edges_created=0, contradictions_found=0, nodes_processed=0)
            result = ingest_pipeline(
                file_path=md, session_dir=session_dir,
                model="test-model", source_id="my-source", skip_embedding=True,
            )

        assert not any("conflict" in e.lower() for e in result.errors)
        assert get_source(session_dir, "my-source")["path"] == str(tmp_path)


# === Phase 6b: Document ingestion resume ===


class TestDocumentIngestionResume:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    @pytest.fixture
    def sample_md(self, tmp_path):
        f = tmp_path / "sample.md"
        f.write_text("# Title\n\nSome content about Python.\n")
        return f

    def test_get_ingested_doc_paths_empty_graph(self, session_dir):
        """Empty graph returns empty set."""
        from oi.ingest import _get_ingested_doc_paths
        assert _get_ingested_doc_paths(session_dir) == set()

    def test_get_ingested_doc_paths_finds_docs(self, session_dir):
        """Finds doc paths from provenance URIs."""
        from oi.ingest import _get_ingested_doc_paths
        from oi.state import _save_knowledge

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "A",
                 "provenance_uri": "doc://my-source/thesis.md#intro",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
                {"id": "fact-002", "type": "fact", "summary": "B",
                 "provenance_uri": "doc://my-source/notes.md#section-1",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
                {"id": "fact-003", "type": "fact", "summary": "C",
                 "provenance_uri": "chatgpt://other/conv-1#turn-0",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        paths = _get_ingested_doc_paths(session_dir)
        assert "my-source/thesis.md" in paths
        assert "my-source/notes.md" in paths
        assert len(paths) == 2  # chatgpt URI excluded

    def test_get_ingested_doc_paths_returns_all_sources(self, session_dir):
        """Returns paths from all sources (no source_id filter)."""
        from oi.ingest import _get_ingested_doc_paths
        from oi.state import _save_knowledge

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "A",
                 "provenance_uri": "doc://src-a/file.md#s1",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
                {"id": "fact-002", "type": "fact", "summary": "B",
                 "provenance_uri": "doc://src-b/file.md#s1",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        paths = _get_ingested_doc_paths(session_dir)
        assert "src-a/file.md" in paths
        assert "src-b/file.md" in paths
        assert len(paths) == 2

    @patch("oi.ingest.chat")
    def test_skips_already_ingested_document(self, mock_chat, session_dir, sample_md):
        """Document with matching provenance is skipped without LLM calls."""
        from oi.ingest import ingest_pipeline
        from oi.state import _save_knowledge

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old",
                 "provenance_uri": f"doc://sample.md#title",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        result = ingest_pipeline(
            sample_md, session_dir, skip_linking=True, skip_embedding=True,
        )

        assert result.documents_skipped == 1
        assert result.nodes_created == []
        assert result.claims_extracted == 0
        mock_chat.assert_not_called()

    @patch("oi.ingest.chat")
    def test_skip_existing_false_forces_reingest(self, mock_chat, session_dir, sample_md):
        """skip_existing=False processes document even if already ingested."""
        from oi.ingest import ingest_pipeline
        from oi.state import _save_knowledge

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old",
                 "provenance_uri": f"doc://sample.md#title",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Re-ingested fact"},
        ])

        result = ingest_pipeline(
            sample_md, session_dir, skip_existing=False,
            skip_linking=True, skip_embedding=True,
        )

        assert result.documents_skipped == 0
        assert len(result.nodes_created) == 1
        mock_chat.assert_called()

    @patch("oi.ingest.chat")
    def test_no_skip_when_no_match(self, mock_chat, session_dir, sample_md):
        """Document not previously ingested is processed normally."""
        from oi.ingest import ingest_pipeline
        from oi.state import _save_knowledge

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Other",
                 "provenance_uri": "doc://other-file.md#intro",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "New fact"},
        ])

        result = ingest_pipeline(
            sample_md, session_dir, skip_linking=True, skip_embedding=True,
        )

        assert result.documents_skipped == 0
        assert len(result.nodes_created) == 1

    @patch("oi.ingest.chat")
    def test_skip_with_source_id(self, mock_chat, session_dir, tmp_path):
        """Skip works correctly with source_id-prefixed provenance URIs."""
        from oi.ingest import ingest_pipeline
        from oi.sources import register_source
        from oi.state import _save_knowledge

        register_source(session_dir, id="my-src", type="doc_root", path=str(tmp_path))

        md = tmp_path / "notes.md"
        md.write_text("# Notes\n\nContent.\n")

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old",
                 "provenance_uri": "doc://my-src/notes.md#notes",
                 "status": "active", "source": "my-src",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        result = ingest_pipeline(
            md, session_dir, source_id="my-src",
            skip_linking=True, skip_embedding=True,
        )

        assert result.documents_skipped == 1
        mock_chat.assert_not_called()

    @patch("oi.ingest.chat")
    def test_skip_cross_source_id(self, mock_chat, session_dir, sample_md):
        """File ingested under source_id is skipped when re-ingested without one.

        Regression test: thesis.md ingested as doc://knowledge-network-docs/thesis.md
        was not skipped when re-ingested as doc://thesis.md (no source_id), creating
        223 duplicate nodes. The skip check must match by filename across source_id prefixes.
        """
        from oi.ingest import ingest_pipeline
        from oi.state import _save_knowledge

        # Previously ingested with source_id="my-source"
        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old",
                 "provenance_uri": "doc://my-source/sample.md#title",
                 "status": "active", "source": "my-source",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        # Re-ingest WITHOUT source_id — should still skip
        result = ingest_pipeline(
            sample_md, session_dir, skip_linking=True, skip_embedding=True,
        )

        assert result.documents_skipped == 1
        assert result.nodes_created == []
        mock_chat.assert_not_called()

    @patch("oi.ingest.chat")
    def test_skip_cross_source_id_reverse(self, mock_chat, session_dir, tmp_path):
        """File ingested without source_id is skipped when re-ingested with one."""
        from oi.ingest import ingest_pipeline
        from oi.sources import register_source
        from oi.state import _save_knowledge

        register_source(session_dir, id="my-src", type="doc_root", path=str(tmp_path))

        md = tmp_path / "notes.md"
        md.write_text("# Notes\n\nContent.\n")

        # Previously ingested without source_id
        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old",
                 "provenance_uri": "doc://notes.md#notes",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        # Re-ingest WITH source_id — should still skip
        result = ingest_pipeline(
            md, session_dir, source_id="my-src",
            skip_linking=True, skip_embedding=True,
        )

        assert result.documents_skipped == 1
        mock_chat.assert_not_called()

    def test_dry_run_skips_skip_check(self, session_dir, sample_md):
        """Dry run does not skip even if document was already ingested."""
        from oi.ingest import ingest_pipeline
        from oi.state import _save_knowledge

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old",
                 "provenance_uri": "doc://sample.md#title",
                 "status": "active", "source": "test",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        with patch("oi.ingest.chat") as mock_chat:
            mock_chat.return_value = _llm_response([
                {"node_type": "fact", "summary": "Dry run fact"},
            ])
            result = ingest_pipeline(
                sample_md, session_dir, dry_run=True,
            )

        assert result.documents_skipped == 0
        assert result.dry_run is True
        assert result.claims_extracted == 1


# === Phase 7: ingest_chatgpt_export ===


class TestIngestChatGPTExport:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    def test_ingest_chatgpt_export_unregistered_source_errors(self, session_dir):
        """Returns error if source_id not in registry."""
        from oi.ingest import ingest_chatgpt_export

        result = ingest_chatgpt_export(source_id="nonexistent", session_dir=session_dir)
        assert result.errors
        assert any("not registered" in e for e in result.errors)

    @patch("oi.ingest.chat")
    @patch("oi.chatgpt_parser.parse_chatgpt_export")
    def test_ingest_chatgpt_export_dry_run(self, mock_parse, mock_chat, session_dir):
        """Dry-run returns extracted claims but writes no nodes."""
        from oi.ingest import ingest_chatgpt_export
        from oi.sources import register_source

        register_source(session_dir, id="test-src", type="chatgpt_export", path="/fake/path.zip")

        # Return a doc with one chunk
        mock_parse.return_value = [
            _make_doc(chunks=[_make_chunk(content="**User:** Q\n\n**Assistant:** A")])
        ]
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact from a conversation"}
        ])

        result = ingest_chatgpt_export(
            source_id="test-src", session_dir=session_dir, dry_run=True
        )

        assert result.dry_run is True
        assert result.claims_extracted == 1
        assert result.nodes_created == []
        # No knowledge file written
        assert not (session_dir / "knowledge.yaml").exists()

    @patch("oi.ingest.chat")
    @patch("oi.chatgpt_parser.parse_chatgpt_export")
    def test_ingest_chatgpt_export_creates_nodes(self, mock_parse, mock_chat, session_dir):
        """Full pipeline writes nodes for each claim extracted from turn pairs."""
        from oi.ingest import ingest_chatgpt_export
        from oi.sources import register_source

        register_source(session_dir, id="test-src", type="chatgpt_export", path="/fake/path.zip")

        mock_parse.return_value = [
            _make_doc(chunks=[
                _make_chunk(chunk_id="turn-0", content="**User:** Q1\n\n**Assistant:** A1"),
                _make_chunk(chunk_id="turn-1", content="**User:** Q2\n\n**Assistant:** A2"),
            ]),
        ]
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "Claim from conversation"}
        ])

        with patch("oi.linker.link_new_nodes") as mock_link, \
             patch("oi.embed.ensure_embeddings"):
            from oi.linker import LinkingResult
            mock_link.return_value = LinkingResult(
                edges_created=0, contradictions_found=0, nodes_processed=2,
            )
            result = ingest_chatgpt_export(
                source_id="test-src", session_dir=session_dir, skip_embedding=True,
            )

        assert result.dry_run is False
        # 2 chunks → 2 LLM calls → 2 claims → 2 nodes
        assert len(result.nodes_created) == 2
        assert result.claims_extracted == 2
        assert result.errors == []
        assert "test-src" in result.source_path


# === Phase 8: Ingestion Resume/Checkpoint ===


class TestGetIngestedConvIds:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    def test_empty_graph_returns_empty(self, session_dir):
        """No nodes → empty set."""
        result = _get_ingested_conv_ids(session_dir, "my-source")
        assert result == set()

    def test_finds_existing_conv_ids(self, session_dir):
        """Nodes with matching provenance_uri → correct conv IDs extracted."""
        from oi.state import _save_knowledge
        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "provenance_uri": "chatgpt://my-source/conv-aaa#turn-0"},
                {"id": "fact-002", "provenance_uri": "chatgpt://my-source/conv-aaa#turn-1"},
                {"id": "fact-003", "provenance_uri": "chatgpt://my-source/conv-bbb#turn-0"},
            ],
            "edges": [],
        })
        result = _get_ingested_conv_ids(session_dir, "my-source")
        assert result == {"conv-aaa", "conv-bbb"}

    def test_ignores_other_sources(self, session_dir):
        """Different source_id → not included."""
        from oi.state import _save_knowledge
        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "provenance_uri": "chatgpt://other-source/conv-xxx#turn-0"},
                {"id": "fact-002", "provenance_uri": "chatgpt://my-source/conv-aaa#turn-0"},
                {"id": "fact-003", "provenance_uri": "doc://my-source/file.md#intro"},
            ],
            "edges": [],
        })
        result = _get_ingested_conv_ids(session_dir, "my-source")
        assert result == {"conv-aaa"}

    def test_ignores_nodes_without_provenance(self, session_dir):
        """Nodes missing provenance_uri are skipped."""
        from oi.state import _save_knowledge
        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001"},
                {"id": "fact-002", "provenance_uri": ""},
            ],
            "edges": [],
        })
        result = _get_ingested_conv_ids(session_dir, "my-source")
        assert result == set()


class TestIngestChatGPTExportResume:
    @pytest.fixture
    def session_dir(self, tmp_path):
        d = tmp_path / "session"
        d.mkdir()
        return d

    @patch("oi.ingest.chat")
    @patch("oi.chatgpt_parser.parse_chatgpt_export")
    def test_skips_already_ingested(self, mock_parse, mock_chat, session_dir):
        """Already-ingested conversation is skipped, new one is processed."""
        from oi.ingest import ingest_chatgpt_export
        from oi.sources import register_source
        from oi.state import _save_knowledge

        register_source(session_dir, id="test-src", type="chatgpt_export", path="/fake/path.zip")

        # Pre-populate graph with nodes from conv-aaa
        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "Old fact",
                 "provenance_uri": "chatgpt://test-src/conv-aaa#turn-0",
                 "status": "active", "source": "test-src",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        # Parser returns 2 conversations: one already ingested, one new
        mock_parse.return_value = [
            _make_doc(chunks=[_make_chunk(content="Old content")], source_path="conv-aaa"),
            _make_doc(chunks=[_make_chunk(content="New content")], source_path="conv-bbb"),
        ]
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "New fact from conv-bbb"}
        ])

        result = ingest_chatgpt_export(
            source_id="test-src", session_dir=session_dir,
            skip_linking=True, skip_embedding=True,
        )

        assert result.conversations_skipped == 1
        # Only conv-bbb should be processed (1 chunk → 1 claim → 1 node)
        assert len(result.nodes_created) == 1
        assert result.errors == []

    @patch("oi.ingest.chat")
    @patch("oi.chatgpt_parser.parse_chatgpt_export")
    def test_reports_skipped_count(self, mock_parse, mock_chat, session_dir):
        """PipelineResult.conversations_skipped is set correctly."""
        from oi.ingest import ingest_chatgpt_export
        from oi.sources import register_source
        from oi.state import _save_knowledge

        register_source(session_dir, id="test-src", type="chatgpt_export", path="/fake/path.zip")

        _save_knowledge(session_dir, {
            "nodes": [
                {"id": "fact-001", "type": "fact", "summary": "A",
                 "provenance_uri": "chatgpt://test-src/conv-1#turn-0",
                 "status": "active", "source": "test-src",
                 "created": "2025-01-01", "updated": "2025-01-01"},
                {"id": "fact-002", "type": "fact", "summary": "B",
                 "provenance_uri": "chatgpt://test-src/conv-2#turn-0",
                 "status": "active", "source": "test-src",
                 "created": "2025-01-01", "updated": "2025-01-01"},
            ],
            "edges": [],
        })

        mock_parse.return_value = [
            _make_doc(chunks=[_make_chunk(content="C1")], source_path="conv-1"),
            _make_doc(chunks=[_make_chunk(content="C2")], source_path="conv-2"),
            _make_doc(chunks=[_make_chunk(content="C3")], source_path="conv-3"),
        ]
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "New"}
        ])

        result = ingest_chatgpt_export(
            source_id="test-src", session_dir=session_dir,
            skip_linking=True, skip_embedding=True,
        )

        assert result.conversations_skipped == 2
        assert len(result.nodes_created) == 1  # only conv-3

    @patch("oi.ingest.chat")
    @patch("oi.chatgpt_parser.parse_chatgpt_export")
    def test_processes_all_when_none_ingested(self, mock_parse, mock_chat, session_dir):
        """No prior ingestion → all conversations processed."""
        from oi.ingest import ingest_chatgpt_export
        from oi.sources import register_source

        register_source(session_dir, id="test-src", type="chatgpt_export", path="/fake/path.zip")

        mock_parse.return_value = [
            _make_doc(chunks=[_make_chunk(content="C1")], source_path="conv-1"),
            _make_doc(chunks=[_make_chunk(content="C2")], source_path="conv-2"),
        ]
        mock_chat.return_value = _llm_response([
            {"node_type": "fact", "summary": "A fact"}
        ])

        result = ingest_chatgpt_export(
            source_id="test-src", session_dir=session_dir,
            skip_linking=True, skip_embedding=True,
        )

        assert result.conversations_skipped == 0
        assert len(result.nodes_created) == 2


# === Phase 5: LLM integration tests ===

import os
from oi.llm import DEFAULT_MODEL


def _has_llm_key():
    model = os.environ.get("OI_MODEL", DEFAULT_MODEL)
    if model.startswith("cerebras/"):
        return bool(os.environ.get("CEREBRAS_API_KEY"))
    if model.startswith("deepseek/"):
        return bool(os.environ.get("DEEPSEEK_API_KEY"))
    return True


requires_llm = pytest.mark.skipif(
    not _has_llm_key(),
    reason="No API key for configured model",
)


@pytest.mark.llm
class TestExtractFromChunkLLM:
    """Real LLM extraction tests. Costs ~$0.20 on Cerebras."""

    @requires_llm
    def test_extracts_claims_from_thesis_abstract(self):
        """LLM extracts meaningful facts from the thesis abstract."""
        chunk = DocumentChunk(
            chunk_id="docs/thesis.md#abstract",
            content=(
                "Current AI systems compact conversations arbitrarily—when context windows fill, "
                "tokens get summarized or discarded. This treats knowledge as a storage problem "
                "rather than a reasoning problem.\n\n"
                "This document proposes a fundamentally different approach: conclusion-triggered "
                "compaction. Instead of compressing when we run out of space, we compress when we "
                "reach understanding. Each conclusion becomes a node in a growing knowledge network, "
                "with confidence emerging from network topology rather than explicit assignment."
            ),
            heading="Abstract",
            heading_path=["Abstract"],
            provenance_uri="doc://docs/thesis.md#abstract",
            char_count=500,
        )
        result = extract_from_chunk(
            chunk,
            source_path="docs/thesis.md",
            metadata_context="Document: Living Knowledge Networks\n",
        )
        assert result.error is None
        assert len(result.claims) >= 1
        # All claims should have valid types
        valid_types = {"fact", "preference", "decision"}
        for claim in result.claims:
            assert claim.node_type in valid_types
            assert len(claim.summary) > 10
            assert claim.provenance_uri == "doc://docs/thesis.md#abstract"
            assert claim.source_path == "docs/thesis.md"

    @requires_llm
    def test_extracts_decision_from_design_section(self):
        """LLM can extract decisions from a design-oriented section."""
        chunk = DocumentChunk(
            chunk_id="docs/thesis.md#mechanism",
            content=(
                "Instead of waiting for memory pressure, perform continuous mini-compactions "
                "as conclusions are reached. The system uses conclusion-triggered compaction "
                "rather than capacity-triggered compaction. Each effort stays open until resolved. "
                "We chose to model confidence through network topology (support links, failed "
                "contradictions, independent convergence) rather than explicit numeric scores."
            ),
            heading="The Mechanism",
            heading_path=["Thesis 1", "The Mechanism"],
            provenance_uri="doc://docs/thesis.md#the-mechanism",
            char_count=400,
        )
        result = extract_from_chunk(
            chunk,
            source_path="docs/thesis.md",
            metadata_context="Document: Living Knowledge Networks\n",
        )
        assert result.error is None
        assert len(result.claims) >= 1
        # At least one claim should mention compaction or confidence
        summaries = " ".join(c.summary.lower() for c in result.claims)
        assert "compaction" in summaries or "confidence" in summaries or "topology" in summaries

    @requires_llm
    def test_extract_document_real(self):
        """Full document extraction pipeline with real LLM, 2 chunks."""
        doc = ParsedDocument(
            metadata=DocumentMetadata(
                title="Living Knowledge Networks",
                author="Test Author",
                source_path="docs/thesis.md",
                format="markdown",
                provenance_uri="doc://docs/thesis.md",
            ),
            chunks=[
                DocumentChunk(
                    chunk_id="docs/thesis.md#abstract",
                    content=(
                        "This framework proposes conclusion-triggered compaction. "
                        "Instead of compressing when context fills, we compress when "
                        "reasoning resolves. Each conclusion becomes a knowledge node."
                    ),
                    heading="Abstract",
                    heading_path=["Abstract"],
                    provenance_uri="doc://docs/thesis.md#abstract",
                    char_count=200,
                ),
                DocumentChunk(
                    chunk_id="docs/thesis.md#empty",
                    content="",
                    heading="Empty Section",
                    heading_path=["Empty Section"],
                    provenance_uri="doc://docs/thesis.md#empty",
                    char_count=0,
                ),
                DocumentChunk(
                    chunk_id="docs/thesis.md#primitives",
                    content=(
                        "The project builds a customizable AI system from composable primitives. "
                        "Primitives include: efforts (units of focused work), artifacts (compacted "
                        "knowledge), tools (extensible Python functions), schemas (Pydantic data "
                        "models), and persistence (files, SQLite, everything inspectable)."
                    ),
                    heading="Primitives",
                    heading_path=["The Bigger Picture", "Primitives"],
                    provenance_uri="doc://docs/thesis.md#primitives",
                    char_count=300,
                ),
            ],
            total_chars=500,
        )
        result = extract_document(doc)
        assert result.source_path == "docs/thesis.md"
        assert result.chunks_total == 3
        assert result.chunks_skipped == 1  # empty chunk
        assert result.chunks_processed == 2
        assert result.chunks_failed == 0
        assert len(result.claims) >= 2
        # All claims should have correct provenance
        for claim in result.claims:
            assert claim.provenance_uri.startswith("doc://docs/thesis.md#")
