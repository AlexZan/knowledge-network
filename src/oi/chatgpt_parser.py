"""ChatGPT export parser: parse conversations.json into ParsedDocument objects.

Converts ChatGPT conversation exports into the same ParsedDocument/DocumentChunk
format used by the rest of the ingestion pipeline. Each turn pair (user message +
following assistant response) becomes one chunk. Canvas documents embedded in
conversations are extracted as their own chunks.

URI format:
    chatgpt://{source_id}/{conv_id}#turn-{n}    — conversation turn pairs
    chatgpt://{source_id}/{conv_id}#canvas-{n}  — canvas documents
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from typing import Union

from .parser import DocumentChunk, DocumentMetadata, ParsedDocument


def _linearize_conversation(mapping: dict, current_node: str) -> list[dict]:
    """Walk parent chain from current_node to root, return in chronological order.

    Skips nodes with null messages. Handles missing parents gracefully.
    """
    chain = []
    node_id = current_node
    while node_id and node_id in mapping:
        node = mapping[node_id]
        msg = node.get("message")
        if msg is not None:
            chain.append(msg)
        node_id = node.get("parent")
    chain.reverse()
    return chain


def _extract_text(message: dict) -> str:
    """Extract text from message.content.parts, joining non-empty strings."""
    content = message.get("content") or {}
    parts = content.get("parts") or []
    texts = []
    for part in parts:
        if isinstance(part, str) and part.strip():
            texts.append(part.strip())
    return "\n\n".join(texts)


def _extract_canvas(message: dict) -> tuple[str, str] | None:
    """Check if message is a ChatGPT canvas document.

    Canvas documents have content_type='code' and a JSON text field containing
    {"type": "document", "name": "...", "content": "..."}.

    Returns (name, markdown_content) if canvas, else None.
    """
    content = message.get("content") or {}
    if content.get("content_type") != "code":
        return None
    text = content.get("text", "")
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and parsed.get("type") == "document":
            name = (parsed.get("name") or "Untitled Document").strip()
            doc_content = (parsed.get("content") or "").strip()
            if doc_content:
                return (name, doc_content)
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def parse_chatgpt_conversation(conv: dict, source_id: str) -> ParsedDocument:
    """Parse a single ChatGPT conversation into a ParsedDocument.

    Produces two chunk types:
    - Turn pairs: user message + assistant text response
    - Canvas chunks: embedded canvas documents extracted as their own chunks

    Canvas-only assistant responses (no text) are skipped as turn pairs — the
    canvas content is captured separately as a canvas chunk.
    """
    from .sources import build_chatgpt_uri

    conv_id = conv.get("id", "")
    raw_title = (conv.get("title") or "").strip()
    title = raw_title or f"Untitled {conv_id[:8]}"

    mapping = conv.get("mapping") or {}
    current_node = conv.get("current_node", "")

    provenance_uri = build_chatgpt_uri(source_id, conv_id)

    metadata = DocumentMetadata(
        title=title,
        format="chatgpt",
        source_path=conv_id,
        provenance_uri=provenance_uri,
    )

    messages = _linearize_conversation(mapping, current_node)

    chunks = []
    turn_n = 0
    canvas_n = 0
    i = 0

    while i < len(messages):
        msg = messages[i]
        role = (msg.get("author") or {}).get("role", "")

        # Canvas document — extract as its own chunk regardless of role
        canvas = _extract_canvas(msg)
        if canvas is not None:
            name, doc_content = canvas
            chunk_uri = f"{provenance_uri}#canvas-{canvas_n}"
            chunks.append(DocumentChunk(
                chunk_id=f"chatgpt://{source_id}/{conv_id}#canvas-{canvas_n}",
                content=doc_content,
                heading=name,
                heading_path=[title, name],
                provenance_uri=chunk_uri,
                char_count=len(doc_content),
            ))
            canvas_n += 1
            i += 1
            continue

        if role == "user":
            user_text = _extract_text(msg)
            if i + 1 < len(messages):
                next_msg = messages[i + 1]
                next_role = (next_msg.get("author") or {}).get("role", "")
                if next_role == "assistant":
                    # Skip turn pair if assistant responded with canvas only
                    if _extract_canvas(next_msg) is not None:
                        i += 1
                        continue
                    assistant_text = _extract_text(next_msg)
                    if user_text or assistant_text:
                        chunk_uri = f"{provenance_uri}#turn-{turn_n}"
                        turn_label = f"Turn {turn_n + 1}"
                        content = f"**User:** {user_text}\n\n**Assistant:** {assistant_text}"
                        chunks.append(DocumentChunk(
                            chunk_id=f"chatgpt://{source_id}/{conv_id}#turn-{turn_n}",
                            content=content,
                            heading=turn_label,
                            heading_path=[title, turn_label],
                            provenance_uri=chunk_uri,
                            char_count=len(content),
                        ))
                        turn_n += 1
                    i += 2
                    continue
        i += 1

    return ParsedDocument(
        metadata=metadata,
        chunks=chunks,
        total_chars=sum(c.char_count for c in chunks),
    )


def parse_chatgpt_file(path: Union[str, Path], source_id: str) -> ParsedDocument:
    """Parse a single ChatGPT conversation JSON file.

    The file should contain one conversation object (not an array) — the format
    produced by mcp_prepare_chatgpt_export.

    Args:
        path: Path to the .json file containing a single conversation object.
        source_id: Source ID for provenance URIs (e.g. 'physics-theory').
    """
    path = Path(path)
    conv = json.loads(path.read_text(encoding="utf-8"))
    return parse_chatgpt_conversation(conv, source_id)


def parse_chatgpt_export(
    path: Union[str, Path],
    source_id: str,
    title_filter: str = "",
    chatgpt_project_id: str = "",
) -> list[ParsedDocument]:
    """Parse a ChatGPT export zip or conversations.json array.

    Args:
        path: Path to .zip or conversations.json
        source_id: Registered source ID (used in URIs)
        title_filter: Comma-separated keywords; empty = all conversations.
                      Each keyword is case-insensitive substring match on title.
        chatgpt_project_id: ChatGPT project ID (the gizmo_id field in the export,
                            shown as 'g-p-...'). When set, only conversations from
                            that project are included. Takes priority over title_filter
                            when both are set.

    Returns list of ParsedDocument, one per matching conversation.
    Empty conversations (no chunks at all) are skipped.
    """
    path = Path(path)

    if str(path).endswith(".zip"):
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extract("conversations.json", tmpdir)
            json_path = Path(tmpdir) / "conversations.json"
            conversations = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        conversations = json.loads(path.read_text(encoding="utf-8"))

    keywords = [kw.strip().lower() for kw in title_filter.split(",") if kw.strip()]

    results = []
    for conv in conversations:
        # Filter by ChatGPT project ID if provided
        if chatgpt_project_id:
            if (conv.get("gizmo_id") or "") != chatgpt_project_id:
                continue
        elif keywords:
            title = (conv.get("title") or "").strip().lower()
            if not any(kw in title for kw in keywords):
                continue

        doc = parse_chatgpt_conversation(conv, source_id)
        if not doc.chunks:
            continue

        results.append(doc)

    return results
