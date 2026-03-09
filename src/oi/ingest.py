"""Document ingestion: extract knowledge claims from parsed document chunks.

Takes ParsedDocument output from parser.py, uses LLM to extract claims per chunk,
and writes them to the knowledge graph via add_knowledge(). Includes a top-level
ingest_pipeline() orchestrator that chains parse → extract → write → link → embed → report.
Also provides ingest_chatgpt_export() for ChatGPT conversation sources.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Optional

from pydantic import BaseModel

from .llm import chat, DEFAULT_MODEL, get_max_input_tokens
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
    source_quote: str = ""  # verbatim text from source that this claim was extracted from


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
    documents_skipped: int = 0
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
        f"- Do NOT split composite principles into separate nodes. If a statement has contrasting parts (e.g., 'X is not A, but it IS B'), keep it as ONE node\n"
        f"- {type_list}\n"
        f"- For each claim, set voice to one of:\n"
        f'    "first_person" — the author is asserting this as their own original claim or position\n'
        f'    "reported"     — the author is describing what standard physics / conventional theory / existing literature claims.\n'
        f'                     USE THIS when text contains phrases like: "the standard interpretation holds", "conventional QM says",\n'
        f'                     "the mainstream view is", "standard quantum mechanics posits", "the accepted explanation is",\n'
        f'                     or any claim attributed to an external theory, framework, or the scientific consensus.\n'
        f'    "described"    — the author is neutrally describing an observed phenomenon or experimental result\n'
        f'                     (neither their own theory nor attributed to another — just describing what happens)\n\n'
        f"- Include source_quote: the verbatim text from the source that this claim is based on (1-3 sentences, exact wording)\n\n"
        f'Respond with ONLY a JSON array:\n'
        f'[{{"node_type": "fact", "summary": "...", "reasoning": "...", "voice": "first_person|reported|described", "source_quote": "..."}}, ...]\n'
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

    # Missing comma repair: LLMs sometimes emit "}{" instead of "},{"
    repaired = re.sub(r'\}\s*\{', '},{', text)
    if repaired != text:
        try:
            return json.loads(repaired)
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
                    source_quote=str(n.get("source_quote", "")).strip(),
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


# === Conversation-Aware Extraction (Decision 022) ===


def _estimate_tokens(text: str, model: str = None) -> int:
    """Estimate token count for text using litellm's token counter."""
    try:
        from litellm import token_counter
        return token_counter(model=model or DEFAULT_MODEL, text=text)
    except Exception:
        return len(text) // 4  # fallback: ~4 chars per token


def _is_canvas_chunk(chunk: DocumentChunk) -> bool:
    """Check if a chunk is a canvas document (vs a conversation turn)."""
    return "#canvas-" in (chunk.chunk_id or "")


def _build_conversation_text(doc: ParsedDocument) -> str:
    """Concatenate conversation turn chunks into a single string.

    Excludes canvas chunks — those are extracted separately via extract_from_chunk().
    """
    parts = []
    for chunk in doc.chunks:
        if chunk.char_count == 0 or _is_canvas_chunk(chunk):
            continue
        parts.append(chunk.content)
    return "\n\n---\n\n".join(parts)


def _build_conversation_prompt(
    conversation_text: str,
    metadata_context: str,
    prior_nodes: list[dict] | None = None,
) -> list[dict]:
    """Build LLM messages for conversation-aware extraction."""
    type_list = build_extraction_type_list()

    system = (
        "You extract knowledge claims from conversations. "
        "Respond ONLY with a JSON array. No explanation, no markdown fences, no prose."
    )

    prior_context = ""
    if prior_nodes:
        summaries = "\n".join(
            f"- [{n['node_type']}] {n['summary']}" for n in prior_nodes
        )
        prior_context = (
            f"Nodes extracted from earlier in this conversation:\n{summaries}\n\n"
            f"For the next section below, UPDATE, EXTEND, or ADD TO these nodes.\n"
            f"If a prior node was exploratory and the conversation now contradicts or "
            f"abandons it, mark it with node_type \"retracted\" so it can be removed.\n"
            f"Only output NEW or UPDATED nodes — do not repeat unchanged prior nodes.\n\n"
        )

    user = (
        f"Read this full conversation and extract knowledge claims that represent "
        f"settled conclusions, committed positions, and key ideas.\n\n"
        f"Context:\n"
        f"{metadata_context}"
        f"Rules:\n"
        f"- Extract ONLY conclusions, settled positions, and ideas the participants committed to\n"
        f"- IGNORE exploratory hypotheticals, ideas proposed then abandoned, rhetorical questions, and scaffolding discussion\n"
        f"- The USER is the primary author and source of authority. When the user and assistant both state the same idea, prefer the user's wording\n"
        f"- If the assistant rephrases a user idea more formally or confidently than the user stated it, use the USER's framing, not the assistant's elevation\n"
        f"- HOWEVER: when the user asks the assistant to explain, elaborate, or apply their framework, the assistant's response IS extractable — it represents the framework the user is developing\n"
        f"- Tentative user language ('maybe', 'I wonder', 'could be', 'just thinking', 'spitballing') means the idea is NOT a settled position — do not extract it as one\n"
        f"- If an idea was proposed early and revised later, extract ONLY the final version\n"
        f"- Do NOT split composite principles into separate nodes. If a statement has contrasting parts (e.g., 'X is not A, but it IS B'), keep it as ONE node\n"
        f"- Each summary must be self-contained (no pronouns like 'it', 'this')\n"
        f"- Include reasoning briefly explaining why this claim is noteworthy\n"
        f"- {type_list}\n"
        f"- For each claim, set voice to one of:\n"
        f'    "first_person" — the author is asserting this as their own original claim or position\n'
        f'    "reported"     — the author is describing what standard physics / conventional theory / existing literature claims\n'
        f'    "described"    — the author is neutrally describing an observed phenomenon or experimental result\n'
        f"- Include source_quote: the verbatim text from the conversation that this claim is based on (1-3 sentences, exact wording — prefer user's words when available)\n\n"
        f"{prior_context}"
        f'Respond with ONLY a JSON array:\n'
        f'[{{"node_type": "fact", "summary": "...", "reasoning": "...", "voice": "first_person|reported|described", "source_quote": "..."}}, ...]\n'
        f"If nothing is worth extracting, respond with: []\n\n"
        f"--- Conversation ---\n"
        f"{conversation_text}"
    )

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_conversation_response(
    text: str,
    source_path: str,
    provenance_uri: str,
    authored_at: str = "",
) -> list[ExtractedClaim]:
    """Parse LLM response into ExtractedClaim objects, filtering retracted nodes."""
    valid_types = set(get_extractable_types())
    nodes = _parse_llm_json(text)
    if not isinstance(nodes, list):
        return []

    claims = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        ntype = n.get("node_type", "")
        summary = n.get("summary", "")
        if ntype == "retracted":
            continue  # handled by caller for iterative mode
        if ntype not in valid_types:
            continue
        if not isinstance(summary, str) or not summary.strip():
            continue
        raw_voice = str(n.get("voice", "first_person")).strip().lower()
        voice = raw_voice if raw_voice in ("first_person", "reported", "described") else "first_person"
        claims.append(
            ExtractedClaim(
                node_type=ntype,
                summary=summary.strip(),
                provenance_uri=provenance_uri,
                source_path=source_path,
                reasoning=str(n.get("reasoning", "")).strip(),
                voice=voice,
                authored_at=authored_at,
                source_quote=str(n.get("source_quote", "")).strip(),
            )
        )
    return claims


def _extract_retracted(text: str) -> list[str]:
    """Extract summaries of retracted nodes from LLM response."""
    nodes = _parse_llm_json(text)
    if not isinstance(nodes, list):
        return []
    return [
        n.get("summary", "").strip()
        for n in nodes
        if isinstance(n, dict) and n.get("node_type") == "retracted"
    ]


def _chat_with_retry(
    messages: list[dict],
    model: str,
    phase: str,
    log_meta: dict,
    errors: list[str],
) -> str | None:
    """Call chat() and retry once on JSON parse failure.

    Returns raw response text on success, None on failure (after retry).
    Appends error/retry info to errors list.
    """
    for attempt in range(2):
        try:
            raw = chat(messages, model=model, phase=phase, log_meta=log_meta)
            raw_text = raw.strip()
            # Validate that the response is parseable JSON before returning
            _parse_llm_json(raw_text)
            return raw_text
        except json.JSONDecodeError:
            if attempt == 0:
                source = log_meta.get("source", "unknown")
                errors.append(
                    f"JSON parse failed for {source}, retrying (attempt 2/2)"
                )
                continue
            else:
                return None
        except Exception:
            # Non-JSON errors (network, timeout, etc.) — don't retry
            raise
    return None


def extract_from_conversation(
    doc: ParsedDocument,
    model: str = None,
) -> DocumentExtractionResult:
    """Extract knowledge claims from a conversation using full-context awareness.

    For conversations that fit in the model's context window, sends the entire
    conversation in one LLM call. For larger conversations, uses iterative
    node-carry-forward: extract from the first chunk, then send subsequent
    chunks with prior node summaries as compressed context.

    See Decision 022 for rationale.

    Canvas chunks (embedded markdown documents) are routed to per-chunk
    extraction (extract_from_chunk) instead of conversation-aware extraction.
    This preserves document structure for canvas content while keeping
    conversation turns in the conclusion-focused pipeline.
    """
    model = model or DEFAULT_MODEL
    source_path = doc.metadata.source_path
    metadata_context = ""
    if doc.metadata.title:
        metadata_context += f"Conversation: {doc.metadata.title}\n"
    if doc.metadata.author:
        metadata_context += f"Author: {doc.metadata.author}\n"
    if doc.metadata.date:
        metadata_context += f"Date: {doc.metadata.date}\n"

    # Split chunks: conversation turns vs canvas documents
    conv_chunks = [c for c in doc.chunks if not _is_canvas_chunk(c)]
    canvas_chunks = [c for c in doc.chunks if _is_canvas_chunk(c) and c.char_count > 0]

    # Get first conversation chunk's provenance and authored_at
    first_chunk = next((c for c in conv_chunks if c.char_count > 0), None)
    if not first_chunk and not canvas_chunks:
        return DocumentExtractionResult(
            source_path=source_path,
            chunks_total=len(doc.chunks),
            chunks_processed=0,
            chunks_skipped=len(doc.chunks),
            chunks_failed=0,
        )

    # Extract canvas chunks via per-chunk document extraction
    canvas_claims: list[ExtractedClaim] = []
    canvas_processed = 0
    canvas_failed = 0
    canvas_errors: list[str] = []
    canvas_metadata = metadata_context.replace("Conversation:", "Document:")
    for chunk in canvas_chunks:
        chunk_result = extract_from_chunk(
            chunk, source_path, metadata_context=canvas_metadata, model=model)
        if chunk_result.error:
            canvas_failed += 1
            canvas_errors.append(f"Canvas '{chunk.heading}': {chunk_result.error}")
        else:
            canvas_processed += 1
            canvas_claims.extend(chunk_result.claims)

    # If no conversation turns, return canvas-only results
    if not first_chunk:
        return DocumentExtractionResult(
            source_path=source_path,
            chunks_total=len(doc.chunks),
            chunks_processed=canvas_processed,
            chunks_skipped=len(doc.chunks) - len(canvas_chunks),
            chunks_failed=canvas_failed,
            claims=canvas_claims,
            errors=canvas_errors,
        )

    provenance_uri = first_chunk.provenance_uri
    authored_at = ""
    if hasattr(first_chunk, "metadata") and first_chunk.metadata:
        authored_at = first_chunk.metadata.get("authored_at", "")

    # Concatenate conversation turns only (canvas already extracted above)
    full_text = _build_conversation_text(doc)
    non_empty_conv_chunks = sum(1 for c in conv_chunks if c.char_count > 0)

    # Reserve tokens for prompt overhead and response
    max_input = get_max_input_tokens(model)
    prompt_overhead = 500  # system message + instructions
    response_reserve = 4000  # room for output
    available_tokens = max_input - prompt_overhead - response_reserve

    text_tokens = _estimate_tokens(full_text, model)

    errors: list[str] = list(canvas_errors)
    empty_conv_chunks = len(conv_chunks) - non_empty_conv_chunks
    total_skipped = empty_conv_chunks + (len(doc.chunks) - len(conv_chunks) - len(canvas_chunks))

    if text_tokens <= available_tokens:
        # Single-call path: send entire conversation
        messages = _build_conversation_prompt(full_text, metadata_context)
        log_meta = {"source": source_path, "mode": "single"}
        try:
            raw_text = _chat_with_retry(
                messages, model=model, phase="extract_conversation",
                log_meta=log_meta, errors=errors)
            if raw_text is None:
                errors.append(f"Conversation extraction failed after retry: JSON parse error")
                return DocumentExtractionResult(
                    source_path=source_path,
                    chunks_total=len(doc.chunks),
                    chunks_processed=canvas_processed,
                    chunks_skipped=total_skipped,
                    chunks_failed=non_empty_conv_chunks + canvas_failed,
                    claims=canvas_claims,
                    errors=errors,
                )
            claims = _parse_conversation_response(
                raw_text, source_path, provenance_uri, authored_at)
            return DocumentExtractionResult(
                source_path=source_path,
                chunks_total=len(doc.chunks),
                chunks_processed=non_empty_conv_chunks + canvas_processed,
                chunks_skipped=total_skipped,
                chunks_failed=canvas_failed,
                claims=canvas_claims + claims,
                errors=errors,
            )
        except Exception as e:
            errors.append(f"Conversation extraction failed: {e}")
            return DocumentExtractionResult(
                source_path=source_path,
                chunks_total=len(doc.chunks),
                chunks_processed=canvas_processed,
                chunks_skipped=total_skipped,
                chunks_failed=non_empty_conv_chunks + canvas_failed,
                claims=canvas_claims,
                errors=errors,
            )
    else:
        # Iterative path: node-carry-forward
        # Split conversation into segments that fit in context
        non_empty = [c for c in conv_chunks if c.char_count > 0]
        accumulated_nodes: list[dict] = []
        all_claims: list[ExtractedClaim] = []
        chunks_processed = 0
        chunks_failed = 0

        # Build segments by accumulating chunks until we approach the limit
        segment_chunks: list[DocumentChunk] = []
        segment_tokens = 0

        for chunk in non_empty:
            chunk_tokens = _estimate_tokens(chunk.content, model)
            # Reserve space for prior node summaries (~50 tokens per node)
            prior_overhead = len(accumulated_nodes) * 50
            segment_limit = available_tokens - prior_overhead

            if segment_tokens + chunk_tokens > segment_limit and segment_chunks:
                # Process current segment
                segment_text = "\n\n---\n\n".join(c.content for c in segment_chunks)
                messages = _build_conversation_prompt(
                    segment_text, metadata_context,
                    prior_nodes=accumulated_nodes if accumulated_nodes else None,
                )
                log_meta = {"source": source_path, "mode": "iterative",
                            "segment": chunks_processed}
                try:
                    raw_text = _chat_with_retry(
                        messages, model=model, phase="extract_conversation",
                        log_meta=log_meta, errors=errors)
                    if raw_text is None:
                        chunks_failed += len(segment_chunks)
                        errors.append(f"Segment extraction failed after retry: JSON parse error")
                    else:
                        # Extract retracted nodes and remove them from accumulated
                        retracted = _extract_retracted(raw_text)
                        if retracted:
                            accumulated_nodes = [
                                n for n in accumulated_nodes
                                if n["summary"] not in retracted
                            ]

                        # Parse new claims
                        new_claims = _parse_conversation_response(
                            raw_text, source_path, provenance_uri, authored_at)
                        all_claims.extend(new_claims)
                        chunks_processed += len(segment_chunks)

                        # Add to accumulated for next segment
                        for claim in new_claims:
                            accumulated_nodes.append({
                                "node_type": claim.node_type,
                                "summary": claim.summary,
                            })
                except Exception as e:
                    chunks_failed += len(segment_chunks)
                    errors.append(f"Segment extraction failed: {e}")

                # Reset segment
                segment_chunks = []
                segment_tokens = 0

            segment_chunks.append(chunk)
            segment_tokens += chunk_tokens

        # Process final segment
        if segment_chunks:
            segment_text = "\n\n---\n\n".join(c.content for c in segment_chunks)
            messages = _build_conversation_prompt(
                segment_text, metadata_context,
                prior_nodes=accumulated_nodes if accumulated_nodes else None,
            )
            log_meta = {"source": source_path, "mode": "iterative",
                        "segment": chunks_processed}
            try:
                raw_text = _chat_with_retry(
                    messages, model=model, phase="extract_conversation",
                    log_meta=log_meta, errors=errors)
                if raw_text is None:
                    chunks_failed += len(segment_chunks)
                    errors.append(f"Final segment extraction failed after retry: JSON parse error")
                else:
                    new_claims = _parse_conversation_response(
                        raw_text, source_path, provenance_uri, authored_at)
                    all_claims.extend(new_claims)
                    chunks_processed += len(segment_chunks)
            except Exception as e:
                chunks_failed += len(segment_chunks)
                errors.append(f"Final segment extraction failed: {e}")

        return DocumentExtractionResult(
            source_path=source_path,
            chunks_total=len(doc.chunks),
            chunks_processed=chunks_processed + canvas_processed,
            chunks_skipped=total_skipped,
            chunks_failed=chunks_failed + canvas_failed,
            claims=canvas_claims + all_claims,
            errors=errors,
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
                source_quote=claim.source_quote or None,
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


def ingest_conversation(
    doc: ParsedDocument,
    session_dir: Path,
    model: str = None,
    source_label: str = None,
) -> IngestionResult:
    """Extract claims from a conversation and write them to the knowledge graph.

    Like ingest_document() but uses conversation-aware extraction (Decision 022)
    instead of per-chunk extraction. Used for ChatGPT conversations where
    full-context awareness produces better, synthesized claims.

    Args:
        doc: ParsedDocument from chatgpt_parser.
        session_dir: Path to the session/knowledge directory.
        model: LLM model for extraction.
        source_label: Optional source label for nodes (defaults to source_path).

    Returns:
        IngestionResult with created node IDs and error info.
    """
    from .knowledge import add_knowledge

    extraction = extract_from_conversation(doc, model=model)
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
                source_quote=claim.source_quote or None,
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
    skip_existing: bool = True,
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

    # Check if already ingested (before expensive parse+extract)
    # Matches by filename regardless of source_id prefix — the same file
    # ingested as doc://thesis.md and doc://my-source/thesis.md are the same
    # document and should not be re-ingested.
    if skip_existing and not dry_run:
        file_p = Path(file_path).resolve()
        bd = Path(base_dir).resolve() if base_dir else file_p.parent
        try:
            rel = file_p.relative_to(bd)
        except ValueError:
            rel = Path(file_p.name)
        rel_str = str(rel).replace("\\", "/")
        ingested = _get_ingested_doc_paths(session_dir)
        # Match either exact path or path with any source_id prefix
        # e.g. rel_str="thesis.md" matches "thesis.md" or "my-source/thesis.md"
        matched = any(p == rel_str or p.endswith(f"/{rel_str}") for p in ingested)
        if not matched and source_id:
            # Also check the source_id-prefixed form
            prefixed = f"{source_id}/{rel_str}"
            matched = any(p == prefixed or p.endswith(f"/{rel_str}") for p in ingested)
        if matched:
            _progress("skip", f"{rel_str} already ingested")
            return PipelineResult(
                source_path=str(file_path),
                documents_skipped=1,
                errors=[f"Already ingested ({rel_str}), skipping. Use skip_existing=False to force re-ingest."],
                dry_run=dry_run,
            )

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


def _get_ingested_doc_paths(session_dir: Path) -> set[str]:
    """Return doc paths already ingested. Scans provenance_uri for doc:// prefix.

    Returns set of full path fragments as they appear after 'doc://'
    (e.g. 'thesis.md', 'my-source/thesis.md'). Does NOT filter by source_id
    because the same file may have been ingested under a different source_id
    previously — we want to catch that cross-source duplicate.
    """
    from .state import _load_knowledge

    knowledge = _load_knowledge(session_dir)
    paths: set[str] = set()
    for node in knowledge.get("nodes", []):
        uri = node.get("provenance_uri", "")
        if uri.startswith("doc://"):
            # Extract path between doc:// and #section
            rest = uri[len("doc://"):]
            path_part = rest.split("#")[0]
            if path_part:
                paths.add(path_part)
    return paths


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
    """Ingest ChatGPT conversations from a registered source.

    Gets source path from registry via get_source(session_dir, source_id).
    The path can point to a directory of individual JSON files or a
    conversations.json array file. Calls parse_chatgpt_export() then runs
    the pipeline per conversation using conversation-aware extraction (Decision 022).
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

    source_path = source["path"]

    # Stage 1: Parse
    _progress("parse", source_path)
    try:
        docs = parse_chatgpt_export(
            source_path,
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
            extraction = extract_from_conversation(doc, model=model)
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

    # Stage 3: Write to graph (conversation-aware extraction per Decision 022)
    _progress("extract+write", f"{n_matched} conversations")
    node_ids: list[str] = []
    all_claims_count = 0
    consecutive_empty = 0
    EMPTY_THRESHOLD = 5  # stop after N consecutive conversations with 0 claims
    aborted = False
    for idx, doc in enumerate(docs):
        ingestion = ingest_conversation(doc, session_dir, model=model, source_label=source_id)
        node_ids.extend(ingestion.nodes_created)
        chunks_total += ingestion.chunks_total
        chunks_processed += ingestion.chunks_processed
        chunks_failed += ingestion.chunks_failed
        all_claims_count += ingestion.claims_extracted
        errors.extend(ingestion.errors)

        # Early-stop: detect sustained empty extraction (likely prompt/model issue)
        has_content = ingestion.chunks_processed > 0
        if has_content and ingestion.claims_extracted == 0 and not ingestion.errors:
            consecutive_empty += 1
        else:
            consecutive_empty = 0

        if consecutive_empty >= EMPTY_THRESHOLD:
            remaining = len(docs) - idx - 1
            errors.append(
                f"ABORTED: {consecutive_empty} consecutive conversations with content "
                f"produced 0 claims (no errors). This usually means the extraction "
                f"prompt is misconfigured or the model is returning empty results. "
                f"{remaining} conversations were NOT processed. "
                f"Last empty: '{doc.metadata.title}'"
            )
            _progress("abort", f"{consecutive_empty} consecutive empty results — stopping")
            aborted = True
            break

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
