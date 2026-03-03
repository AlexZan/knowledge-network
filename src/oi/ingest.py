"""Document ingestion: extract knowledge claims from parsed document chunks.

Takes ParsedDocument output from parser.py, uses LLM to extract claims per chunk,
and writes them to the knowledge graph via add_knowledge(). Includes a top-level
ingest_pipeline() orchestrator that chains parse → extract → write → link → embed → report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel

from .llm import chat, DEFAULT_MODEL
from .schemas import get_extractable_types, build_extraction_type_list
from .parser import ParsedDocument, DocumentChunk


# === Data Models ===


class ExtractedClaim(BaseModel):
    """A single knowledge claim extracted from a document chunk."""

    node_type: str  # fact, preference, decision
    summary: str
    provenance_uri: str  # from source chunk
    source_path: str
    reasoning: str = ""


class ChunkExtractionResult(BaseModel):
    """Result of extracting claims from a single chunk."""

    chunk_id: str
    claims: list[ExtractedClaim] = []
    error: Optional[str] = None


class DocumentExtractionResult(BaseModel):
    """Result of extracting claims from all chunks in a document."""

    source_path: str
    chunks_total: int
    chunks_processed: int
    chunks_skipped: int  # empty chunks
    chunks_failed: int
    claims: list[ExtractedClaim] = []
    errors: list[str] = []


class IngestionResult(BaseModel):
    """Result of ingesting a document into the knowledge graph."""

    source_path: str
    nodes_created: list[str] = []  # node IDs
    chunks_total: int
    chunks_processed: int
    chunks_failed: int
    claims_extracted: int
    errors: list[str] = []


class PipelineResult(BaseModel):
    """Result of the full ingestion pipeline."""

    source_path: str
    nodes_created: list[str] = []
    chunks_total: int = 0
    chunks_processed: int = 0
    chunks_failed: int = 0
    claims_extracted: int = 0
    edges_created: int = 0
    contradictions_found: int = 0
    conflicts: dict = {}  # {total, auto_resolvable, strong_recommendations, ambiguous}
    errors: list[str] = []
    dry_run: bool = False


# === Extraction Prompt ===


def _build_extraction_prompt(chunk: DocumentChunk, metadata_context: str) -> list[dict]:
    """Build the LLM messages for extracting claims from a document chunk."""
    type_list = build_extraction_type_list()

    system = (
        "You extract knowledge claims from document sections. "
        "Respond ONLY with a JSON array. No explanation, no markdown fences, no prose."
    )

    heading_context = ""
    if chunk.heading_path:
        heading_context = f"Section path: {' > '.join(chunk.heading_path)}\n"
    elif chunk.heading:
        heading_context = f"Section: {chunk.heading}\n"

    user = (
        f"Extract 0-10 knowledge claims from this document section.\n\n"
        f"Context:\n"
        f"{metadata_context}"
        f"{heading_context}"
        f"Provenance: {chunk.provenance_uri}\n\n"
        f"Rules:\n"
        f"- Extract facts, preferences, and decisions worth remembering permanently\n"
        f"- Each summary must be self-contained (no pronouns like 'it', 'this')\n"
        f"- Include reasoning briefly explaining why this claim is noteworthy\n"
        f"- Skip trivial, redundant, or overly specific details\n"
        f"- {type_list}\n\n"
        f'Respond with ONLY a JSON array:\n'
        f'[{{"node_type": "fact", "summary": "...", "reasoning": "..."}}, ...]\n'
        f"If nothing is worth extracting, respond with: []\n\n"
        f"--- Document Section ---\n"
        f"{chunk.content}"
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# === Core Functions ===


def extract_from_chunk(
    chunk: DocumentChunk,
    source_path: str,
    metadata_context: str = "",
    model: str = None,
) -> ChunkExtractionResult:
    """Extract knowledge claims from a single document chunk via LLM.

    Args:
        chunk: The document chunk to extract from.
        source_path: Path of the source document (for provenance).
        metadata_context: Optional context string (title, author, date).
        model: LLM model to use. Defaults to DEFAULT_MODEL.

    Returns:
        ChunkExtractionResult with extracted claims or error.
    """
    if not chunk.content.strip():
        return ChunkExtractionResult(chunk_id=chunk.chunk_id, claims=[], error=None)

    messages = _build_extraction_prompt(chunk, metadata_context)
    valid_types = set(get_extractable_types())

    try:
        raw = chat(messages, model=model or DEFAULT_MODEL)
        text = raw.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        nodes = json.loads(text)
        if not isinstance(nodes, list):
            return ChunkExtractionResult(
                chunk_id=chunk.chunk_id,
                error=f"LLM returned non-array: {type(nodes).__name__}",
            )

        claims = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            ntype = n.get("node_type", "")
            summary = n.get("summary", "")
            if ntype not in valid_types:
                continue
            if not isinstance(summary, str) or not summary.strip():
                continue
            claims.append(
                ExtractedClaim(
                    node_type=ntype,
                    summary=summary.strip(),
                    provenance_uri=chunk.provenance_uri,
                    source_path=source_path,
                    reasoning=str(n.get("reasoning", "")).strip(),
                )
            )

        return ChunkExtractionResult(chunk_id=chunk.chunk_id, claims=claims)

    except json.JSONDecodeError as e:
        return ChunkExtractionResult(
            chunk_id=chunk.chunk_id,
            error=f"JSON parse error: {e}",
        )
    except Exception as e:
        return ChunkExtractionResult(
            chunk_id=chunk.chunk_id,
            error=f"LLM call failed: {e}",
        )


def extract_document(
    doc: ParsedDocument,
    model: str = None,
) -> DocumentExtractionResult:
    """Extract knowledge claims from all chunks in a parsed document.

    Skips empty chunks (char_count == 0). Accumulates errors per chunk.

    Args:
        doc: ParsedDocument from parser.py.
        model: LLM model to use.

    Returns:
        DocumentExtractionResult with all claims and error info.
    """
    source_path = doc.metadata.source_path
    metadata_context = ""
    if doc.metadata.title:
        metadata_context += f"Document: {doc.metadata.title}\n"
    if doc.metadata.author:
        metadata_context += f"Author: {doc.metadata.author}\n"
    if doc.metadata.date:
        metadata_context += f"Date: {doc.metadata.date}\n"

    all_claims: list[ExtractedClaim] = []
    errors: list[str] = []
    chunks_processed = 0
    chunks_skipped = 0
    chunks_failed = 0

    for chunk in doc.chunks:
        if chunk.char_count == 0:
            chunks_skipped += 1
            continue

        result = extract_from_chunk(
            chunk, source_path, metadata_context=metadata_context, model=model
        )

        if result.error:
            chunks_failed += 1
            errors.append(f"{chunk.chunk_id}: {result.error}")
        else:
            chunks_processed += 1
            all_claims.extend(result.claims)

    return DocumentExtractionResult(
        source_path=source_path,
        chunks_total=len(doc.chunks),
        chunks_processed=chunks_processed,
        chunks_skipped=chunks_skipped,
        chunks_failed=chunks_failed,
        claims=all_claims,
        errors=errors,
    )


def ingest_document(
    doc: ParsedDocument,
    session_dir: Path,
    model: str = None,
    source_label: str = None,
) -> IngestionResult:
    """Extract claims from a document and write them to the knowledge graph.

    Uses add_knowledge(skip_linking=True, skip_embed=True) for each claim.
    Linking and embedding are deferred to Slice 13c.

    Args:
        doc: ParsedDocument from parser.py.
        session_dir: Path to the session/knowledge directory.
        model: LLM model for extraction.
        source_label: Optional source label for nodes (defaults to source_path).

    Returns:
        IngestionResult with created node IDs and error info.
    """
    from .knowledge import add_knowledge

    extraction = extract_document(doc, model=model)
    source = source_label or extraction.source_path

    nodes_created: list[str] = []
    errors = list(extraction.errors)

    for claim in extraction.claims:
        try:
            result_json = add_knowledge(
                session_dir,
                node_type=claim.node_type,
                summary=claim.summary,
                source=source,
                reasoning=claim.reasoning,
                provenance_uri=claim.provenance_uri,
                skip_linking=True,
                skip_embed=True,
            )
            result = json.loads(result_json)
            if "error" in result:
                errors.append(f"add_knowledge error: {result['error']}")
            else:
                nodes_created.append(result["node_id"])
        except Exception as e:
            errors.append(f"Failed to add claim '{claim.summary[:50]}...': {e}")

    return IngestionResult(
        source_path=extraction.source_path,
        nodes_created=nodes_created,
        chunks_total=extraction.chunks_total,
        chunks_processed=extraction.chunks_processed,
        chunks_failed=extraction.chunks_failed,
        claims_extracted=len(extraction.claims),
        errors=errors,
    )


# === Top-level Pipeline ===


def ingest_pipeline(
    file_path: str | Path,
    session_dir: Path,
    model: str = None,
    base_dir: str | Path = None,
    dry_run: bool = False,
    skip_linking: bool = False,
    skip_embedding: bool = False,
    progress_fn: Callable[[str, str], None] | None = None,
) -> PipelineResult:
    """Run the full ingestion pipeline: parse → extract → write → link → embed → report.

    Args:
        file_path: Path to the document file (.md, .pdf, .txt).
        session_dir: Path to the session/knowledge directory.
        model: LLM model for extraction and linking.
        base_dir: Base directory for provenance URIs (defaults to file's parent).
        dry_run: If True, parse + extract only — no graph writes.
        skip_linking: Skip the linking pass (faster, cheaper).
        skip_embedding: Skip the embedding pass.
        progress_fn: Optional callback(stage, detail) for progress reporting.

    Returns:
        PipelineResult with counts and any errors.
    """
    from .parser import parse_file

    errors: list[str] = []

    def _progress(stage: str, detail: str = "") -> None:
        if progress_fn:
            progress_fn(stage, detail)

    # Stage 1: Parse
    _progress("parse", str(file_path))
    try:
        doc = parse_file(file_path, base_dir=base_dir)
    except Exception as e:
        return PipelineResult(
            source_path=str(file_path),
            errors=[f"Parse failed: {e}"],
            dry_run=dry_run,
        )

    source_path = doc.metadata.source_path

    # Propagate parse errors (e.g. unsupported format)
    if hasattr(doc, "parse_errors") and doc.parse_errors:
        errors.extend(doc.parse_errors)

    # Stage 2: Extract
    _progress("extract", f"{len(doc.chunks)} chunks")
    extraction = extract_document(doc, model=model)
    errors.extend(extraction.errors)

    if dry_run:
        _progress("done", "dry run complete")
        return PipelineResult(
            source_path=source_path,
            chunks_total=extraction.chunks_total,
            chunks_processed=extraction.chunks_processed,
            chunks_failed=extraction.chunks_failed,
            claims_extracted=len(extraction.claims),
            errors=errors,
            dry_run=True,
        )

    # Stage 3: Write to graph
    _progress("write", f"{len(extraction.claims)} claims")
    ingestion = ingest_document(doc, session_dir, model=model)
    errors.extend(ingestion.errors)
    node_ids = ingestion.nodes_created

    # Stage 4: Link
    edges_created = 0
    contradictions_found = 0
    if not skip_linking and node_ids:
        _progress("link", f"{len(node_ids)} nodes")
        try:
            from .linker import link_new_nodes

            link_result = link_new_nodes(node_ids, session_dir, model=model)
            edges_created = link_result.edges_created
            contradictions_found = link_result.contradictions_found
            errors.extend(link_result.errors)
        except Exception as e:
            errors.append(f"Linking failed: {e}")

    # Stage 5: Embed
    if not skip_embedding and node_ids:
        _progress("embed", f"{len(node_ids)} nodes")
        try:
            from .embed import ensure_embeddings
            from .state import _load_knowledge

            knowledge = _load_knowledge(session_dir)
            ensure_embeddings(session_dir, knowledge)
        except Exception as e:
            errors.append(f"Embedding failed: {e}")

    # Stage 6: Conflict report
    conflicts: dict = {}
    if not skip_linking and node_ids:
        _progress("report", "generating conflict report")
        try:
            from .conflicts import generate_conflict_report

            report = generate_conflict_report(session_dir, node_ids=node_ids)
            conflicts = {
                "total": report.total_contradictions,
                "auto_resolvable": report.auto_resolvable,
                "strong_recommendations": report.strong_recommendations,
                "ambiguous": report.ambiguous,
            }
        except Exception as e:
            errors.append(f"Conflict report failed: {e}")

    _progress("done", f"{len(node_ids)} nodes created")

    return PipelineResult(
        source_path=source_path,
        nodes_created=node_ids,
        chunks_total=ingestion.chunks_total,
        chunks_processed=ingestion.chunks_processed,
        chunks_failed=ingestion.chunks_failed,
        claims_extracted=ingestion.claims_extracted,
        edges_created=edges_created,
        contradictions_found=contradictions_found,
        conflicts=conflicts,
        errors=errors,
        dry_run=False,
    )
