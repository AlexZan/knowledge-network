"""Document ingestion: extract knowledge claims from parsed document chunks.

Takes ParsedDocument output from parser.py, uses LLM to extract claims per chunk,
and writes them to the knowledge graph via add_knowledge(). Includes a top-level
ingest_pipeline() orchestrator that chains parse → extract → write → link → embed → report.
Also provides ingest_chatgpt_export() for ChatGPT export zip files.
"""

from __future__ import annotations

import json
import re
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
    voice: str = "first_person"  # "first_person" | "reported" | "described"
    authored_at: str = ""  # ISO 8601 timestamp from source (e.g. ChatGPT create_time)


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
    conversations_skipped: int = 0
    clusters_found: int = 0
    concepts_created: int = 0
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
        f"- {type_list}\n"
        f"- For each claim, set voice to one of:\n"
        f'    "first_person" — the author is asserting this as their own original claim or position\n'
        f'    "reported"     — the author is describing what standard physics / conventional theory / existing literature claims.\n'
        f'                     USE THIS when text contains phrases like: "the standard interpretation holds", "conventional QM says",\n'
        f'                     "the mainstream view is", "standard quantum mechanics posits", "the accepted explanation is",\n'
        f'                     or any claim attributed to an external theory, framework, or the scientific consensus.\n'
        f'    "described"    — the author is neutrally describing an observed phenomenon or experimental result\n'
        f'                     (neither their own theory nor attributed to another — just describing what happens)\n\n'
        f'Respond with ONLY a JSON array:\n'
        f'[{{"node_type": "fact", "summary": "...", "reasoning": "...", "voice": "first_person|reported|described"}}, ...]\n'
        f"If nothing is worth extracting, respond with: []\n\n"
        f"--- Document Section ---\n"
        f"{chunk.content}"
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# === Core Functions ===


def _parse_llm_json(text: str) -> list:
    """Parse JSON array from LLM output, handling common LLM quirks.

    Handles: markdown fences, control characters, truncated output.
    Raises JSONDecodeError only if all repair attempts fail.
    """
    text = text.strip()
    # Strip markdown fences (opening always present, closing may be truncated)
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove opening fence line
        lines = lines[1:]
        # Remove closing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    # Sanitize control characters (keep \n, \r, \t)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Truncation repair: close unclosed brackets/braces.
    # Strategy: if text starts with '[', try progressively trimming from the end
    # to find the last complete object, then close the array.
    if text.lstrip().startswith("["):
        # Trim trailing partial object: find last '}' and close the array there
        last_brace = text.rfind("}")
        if last_brace > 0:
            candidate = text[:last_brace + 1].rstrip().rstrip(",") + "]"
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    # Nothing worked — raise the original error for reporting
    return json.loads(text)


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
        raw = chat(
            messages,
            model=model or DEFAULT_MODEL,
            phase="extract",
            log_meta={"chunk_id": chunk.chunk_id, "source": source_path},
        )
        text = raw.strip()
        nodes = _parse_llm_json(text)
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
            raw_voice = str(n.get("voice", "first_person")).strip().lower()
            voice = raw_voice if raw_voice in ("first_person", "reported", "described") else "first_person"
            authored_at = ""
            if hasattr(chunk, "metadata") and chunk.metadata:
                authored_at = chunk.metadata.get("authored_at", "")
            claims.append(
                ExtractedClaim(
                    node_type=ntype,
                    summary=summary.strip(),
                    provenance_uri=chunk.provenance_uri,
                    source_path=source_path,
                    reasoning=str(n.get("reasoning", "")).strip(),
                    voice=voice,
                    authored_at=authored_at,
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
                voice=claim.voice,
                authored_at=claim.authored_at or None,
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
    skip_clustering: bool = True,
    progress_fn: Callable[[str, str], None] | None = None,
    source_id: str | None = None,
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

    # Register source if provided and not already registered
    if source_id:
        from .sources import get_source, register_source
        if not get_source(session_dir, source_id):
            reg = register_source(
                session_dir,
                id=source_id,
                type="doc_root",
                path=str(Path(file_path).resolve().parent if base_dir is None else Path(base_dir).resolve()),
            )
            if reg.get("status") == "conflict":
                errors.append(f"Source registration conflict: {reg['error']}")

    # Stage 1: Parse
    _progress("parse", str(file_path))
    try:
        doc = parse_file(file_path, base_dir=base_dir, source_id=source_id)
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

    # Stage 6: Cluster
    clusters_found = 0
    concepts_created = 0
    if not skip_clustering and not skip_embedding and node_ids:
        _progress("cluster", f"finding similar nodes")
        try:
            from .cluster import find_clusters, synthesize_concepts
            from .state import _load_knowledge as _load_kg

            kg = _load_kg(session_dir)
            clusters = find_clusters(session_dir, kg)
            clusters_found = len(clusters)

            # Stage 7: Synthesize concepts
            if clusters:
                _progress("synthesize", f"{clusters_found} cluster(s)")
                concepts = synthesize_concepts(clusters, session_dir, kg, model=model)
                concepts_created = len(concepts)
                for c in concepts:
                    node_ids.append(c["concept_node_id"])
        except Exception as e:
            errors.append(f"Clustering failed: {e}")

    # Stage 8: Conflict report
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
        clusters_found=clusters_found,
        concepts_created=concepts_created,
        conflicts=conflicts,
        errors=errors,
        dry_run=False,
    )


def _get_ingested_conv_ids(session_dir: Path, source_id: str) -> set[str]:
    """Return conversation IDs already ingested for this ChatGPT source.

    Scans knowledge.yaml for nodes with provenance_uri matching
    chatgpt://{source_id}/ prefix and extracts unique conversation IDs.
    """
    from .state import _load_knowledge

    knowledge = _load_knowledge(session_dir)
    prefix = f"chatgpt://{source_id}/"
    ids: set[str] = set()
    for node in knowledge.get("nodes", []):
        uri = node.get("provenance_uri", "")
        if uri.startswith(prefix):
            rest = uri[len(prefix):]
            conv_id = rest.split("#")[0]
            if conv_id:
                ids.add(conv_id)
    return ids


def ingest_chatgpt_export(
    source_id: str,
    session_dir: Path,
    model: str = None,
    title_filter: str = "",
    chatgpt_project_id: str = "",
    dry_run: bool = False,
    skip_linking: bool = False,
    skip_embedding: bool = False,
    skip_clustering: bool = True,
    progress_fn: Callable[[str, str], None] | None = None,
) -> PipelineResult:
    """Ingest a ChatGPT export using the registered source path.

    Gets zip path from source registry via get_source(session_dir, source_id).
    Calls parse_chatgpt_export() then runs the pipeline per conversation.
    Returns aggregated PipelineResult.

    Args:
        source_id: Registered source ID (from mcp_add_source).
        session_dir: Path to the session/knowledge directory.
        model: LLM model for extraction.
        title_filter: Comma-separated keywords to filter conversations by title.
        chatgpt_project_id: ChatGPT project ID ('g-p-...' from the export) to
                            restrict ingestion to one project.
        dry_run: If True, parse + extract only — no graph writes.
        skip_linking: Skip the linking pass (faster, cheaper).
        skip_embedding: Skip the embedding pass.
        progress_fn: Optional callback(stage, detail) for progress reporting.
    """
    from .sources import get_source
    from .chatgpt_parser import parse_chatgpt_export

    errors: list[str] = []

    def _progress(stage: str, detail: str = "") -> None:
        if progress_fn:
            progress_fn(stage, detail)

    # Look up registered source
    source = get_source(session_dir, source_id)
    if not source:
        return PipelineResult(
            source_path=source_id,
            errors=[f"Source '{source_id}' not registered. Use mcp_add_source first."],
        )

    zip_path = source["path"]

    # Stage 1: Parse
    _progress("parse", zip_path)
    try:
        docs = parse_chatgpt_export(
            zip_path,
            source_id=source_id,
            title_filter=title_filter,
            chatgpt_project_id=chatgpt_project_id,
        )
    except Exception as e:
        return PipelineResult(
            source_path=source_id,
            errors=[f"Parse failed: {e}"],
        )

    # Filter out already-ingested conversations
    already_ingested = _get_ingested_conv_ids(session_dir, source_id) if not dry_run else set()
    new_docs = []
    conversations_skipped = 0
    for doc in docs:
        conv_id = doc.metadata.source_path
        if conv_id in already_ingested:
            conversations_skipped += 1
        else:
            new_docs.append(doc)

    if not dry_run:
        docs = new_docs

    n_matched = len(docs)
    source_path_label = f"{source_id} ({n_matched} conversations)"

    chunks_total = 0
    chunks_processed = 0
    chunks_failed = 0

    # Stage 2: Extract (dry-run path)
    if dry_run:
        _progress("extract", f"{n_matched} conversations")
        all_claims_count = 0
        for doc in docs:
            extraction = extract_document(doc, model=model)
            chunks_total += extraction.chunks_total
            chunks_processed += extraction.chunks_processed
            chunks_failed += extraction.chunks_failed
            all_claims_count += len(extraction.claims)
            errors.extend(extraction.errors)

        _progress("done", "dry run complete")
        return PipelineResult(
            source_path=source_path_label,
            chunks_total=chunks_total,
            chunks_processed=chunks_processed,
            chunks_failed=chunks_failed,
            claims_extracted=all_claims_count,
            errors=errors,
            dry_run=True,
        )

    if conversations_skipped:
        _progress("dedup", f"{conversations_skipped} already ingested, skipping")

    # Stage 3: Write to graph
    _progress("extract+write", f"{n_matched} conversations")
    node_ids: list[str] = []
    all_claims_count = 0
    for doc in docs:
        ingestion = ingest_document(doc, session_dir, model=model, source_label=source_id)
        node_ids.extend(ingestion.nodes_created)
        chunks_total += ingestion.chunks_total
        chunks_processed += ingestion.chunks_processed
        chunks_failed += ingestion.chunks_failed
        all_claims_count += ingestion.claims_extracted
        errors.extend(ingestion.errors)

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

    # Stage 6: Cluster
    clusters_found = 0
    concepts_created = 0
    if not skip_clustering and not skip_embedding and node_ids:
        _progress("cluster", f"finding similar nodes")
        try:
            from .cluster import find_clusters, synthesize_concepts
            from .state import _load_knowledge as _load_kg2

            kg = _load_kg2(session_dir)
            clusters = find_clusters(session_dir, kg)
            clusters_found = len(clusters)

            # Stage 7: Synthesize concepts
            if clusters:
                _progress("synthesize", f"{clusters_found} cluster(s)")
                concepts = synthesize_concepts(clusters, session_dir, kg, model=model)
                concepts_created = len(concepts)
                for c in concepts:
                    node_ids.append(c["concept_node_id"])
        except Exception as e:
            errors.append(f"Clustering failed: {e}")

    # Stage 8: Conflict report
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
        source_path=source_path_label,
        nodes_created=node_ids,
        chunks_total=chunks_total,
        chunks_processed=chunks_processed,
        chunks_failed=chunks_failed,
        claims_extracted=all_claims_count,
        edges_created=edges_created,
        contradictions_found=contradictions_found,
        conversations_skipped=conversations_skipped,
        clusters_found=clusters_found,
        concepts_created=concepts_created,
        conflicts=conflicts,
        errors=errors,
        dry_run=False,
    )
