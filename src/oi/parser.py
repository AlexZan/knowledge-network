"""Document parser: read files, extract metadata, chunk into sections.

Supports markdown (heading-based), PDF (page-based), and plain text (paragraph-based).
Output feeds claim extraction (Slice 13b). No LLM calls — pure data processing.
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# === Data Models ===


class DocumentMetadata(BaseModel):
    """Metadata extracted from a document."""

    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime.date] = None
    source_path: str  # Relative path from base_dir
    format: str  # "markdown", "pdf", "text"
    provenance_uri: str  # doc://relative/path.md


class DocumentChunk(BaseModel):
    """A section of a document."""

    chunk_id: str  # "docs/thesis.md#abstract"
    content: str
    heading: Optional[str] = None
    heading_path: list[str] = []
    provenance_uri: str  # doc://path#section-slug
    char_count: int


class ParsedDocument(BaseModel):
    """Result of parsing a single document."""

    metadata: DocumentMetadata
    chunks: list[DocumentChunk]
    total_chars: int
    parse_errors: list[str] = []


# === Utilities ===


def _slugify(text: str) -> str:
    """Convert heading text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _slug_from_path(heading_path: list[str], heading: str | None) -> str:
    """Build a slug from the heading path to ensure uniqueness.

    If heading_path has >1 element, join all into slug (e.g. "parent-child").
    Otherwise fall back to just the heading (backward-compat for top-level).
    """
    if not heading:
        return "preamble"
    if len(heading_path) > 1:
        return _slugify(" ".join(heading_path))
    return _slugify(heading)


def _build_provenance_uri(rel_path: str, fragment: str | None = None) -> str:
    """Build a doc:// provenance URI."""
    # Normalize path separators
    rel_path = rel_path.replace("\\", "/")
    uri = f"doc://{rel_path}"
    if fragment:
        uri += f"#{fragment}"
    return uri


def _extract_frontmatter(text: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from text.

    Returns (metadata_dict, remaining_text).
    Only treats leading --- blocks as frontmatter (not horizontal rules).
    """
    if not text.startswith("---"):
        return {}, text

    # Find closing ---
    lines = text.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    # Parse YAML between the fences
    import yaml

    frontmatter_text = "\n".join(lines[1:end_idx])
    remaining = "\n".join(lines[end_idx + 1 :])

    try:
        meta = yaml.safe_load(frontmatter_text)
        if not isinstance(meta, dict):
            return {}, text
        return meta, remaining.lstrip("\n")
    except yaml.YAMLError:
        return {}, text


_DATE_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _infer_date_from_filename(path: Path) -> datetime.date | None:
    """Try to extract a date from filename like 2024-01-15-meeting-notes.md."""
    m = _DATE_PATTERN.search(path.stem)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def _infer_title_from_content(text: str) -> str | None:
    """Extract title from first h1 heading."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped[2:].strip()
    return None


# === Markdown Parser ===


def _parse_markdown(
    text: str, rel_path: str, max_chunk_chars: int
) -> ParsedDocument:
    """Parse markdown into heading-based chunks."""
    frontmatter, body = _extract_frontmatter(text)

    # Extract metadata
    title = frontmatter.get("title") or _infer_title_from_content(body)
    author = frontmatter.get("author")
    doc_date = None
    if "date" in frontmatter:
        raw = frontmatter["date"]
        if isinstance(raw, datetime.date):
            doc_date = raw
        elif isinstance(raw, str):
            m = _DATE_PATTERN.search(raw)
            if m:
                try:
                    doc_date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    pass
    if doc_date is None:
        doc_date = _infer_date_from_filename(Path(rel_path))

    base_uri = _build_provenance_uri(rel_path)
    metadata = DocumentMetadata(
        title=title,
        author=author,
        date=doc_date,
        source_path=rel_path,
        format="markdown",
        provenance_uri=base_uri,
    )

    chunks = _split_markdown_by_headings(body, rel_path, max_chunk_chars)
    total = sum(c.char_count for c in chunks)

    return ParsedDocument(metadata=metadata, chunks=chunks, total_chars=total)


def _split_markdown_by_headings(
    text: str, rel_path: str, max_chunk_chars: int
) -> list[DocumentChunk]:
    """Split markdown by h2+ headings, tracking heading path."""
    lines = text.split("\n")
    heading_re = re.compile(r"^(#{1,6})\s+(.+)$")

    # Collect sections: list of (level, heading_text, start_line)
    sections: list[tuple[int, str | None, int]] = []
    in_code_block = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Track fenced code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        m = heading_re.match(line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            sections.append((level, heading_text, i))

    # Build chunks from sections
    chunks: list[DocumentChunk] = []

    if not sections:
        # No headings — whole doc is one chunk
        content = text.strip()
        if content:
            chunks.extend(
                _make_chunks(content, None, [], rel_path, max_chunk_chars)
            )
        return chunks

    # Content before first heading
    first_heading_line = sections[0][2]
    preamble = "\n".join(lines[:first_heading_line]).strip()
    if preamble:
        chunks.extend(
            _make_chunks(preamble, None, [], rel_path, max_chunk_chars)
        )

    # Each section
    heading_path: list[tuple[int, str]] = []  # (level, text) stack

    for idx, (level, heading_text, start_line) in enumerate(sections):
        # Update heading path
        # Pop headings at same level or deeper
        heading_path = [(l, t) for l, t in heading_path if l < level]
        heading_path.append((level, heading_text))

        # Get section content (from line after heading to next heading or EOF)
        end_line = sections[idx + 1][2] if idx + 1 < len(sections) else len(lines)
        content_lines = lines[start_line + 1 : end_line]
        content = "\n".join(content_lines).strip()

        path_texts = [t for _, t in heading_path]

        if content:
            chunks.extend(
                _make_chunks(
                    content, heading_text, path_texts, rel_path, max_chunk_chars
                )
            )
        else:
            # Empty section — still record it with empty content
            slug = _slug_from_path(path_texts, heading_text)
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#{slug}",
                    content="",
                    heading=heading_text,
                    heading_path=path_texts,
                    provenance_uri=_build_provenance_uri(rel_path, slug),
                    char_count=0,
                )
            )

    return chunks


def _make_chunks(
    content: str,
    heading: str | None,
    heading_path: list[str],
    rel_path: str,
    max_chunk_chars: int,
) -> list[DocumentChunk]:
    """Create one or more chunks from content, splitting if too long."""
    slug = _slug_from_path(heading_path, heading)

    if len(content) <= max_chunk_chars:
        return [
            DocumentChunk(
                chunk_id=f"{rel_path}#{slug}",
                content=content,
                heading=heading,
                heading_path=heading_path,
                provenance_uri=_build_provenance_uri(rel_path, slug),
                char_count=len(content),
            )
        ]

    # Split long content at paragraph boundaries
    paragraphs = re.split(r"\n\n+", content)
    chunks: list[DocumentChunk] = []
    current: list[str] = []
    current_len = 0
    part = 1

    for para in paragraphs:
        para_len = len(para)
        # If single paragraph exceeds limit, force it into its own chunk
        if para_len > max_chunk_chars:
            # Flush current
            if current:
                chunk_slug = f"{slug}-part-{part}"
                text = "\n\n".join(current)
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{rel_path}#{chunk_slug}",
                        content=text,
                        heading=heading,
                        heading_path=heading_path,
                        provenance_uri=_build_provenance_uri(rel_path, chunk_slug),
                        char_count=len(text),
                    )
                )
                part += 1
                current = []
                current_len = 0

            chunk_slug = f"{slug}-part-{part}"
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#{chunk_slug}",
                    content=para,
                    heading=heading,
                    heading_path=heading_path,
                    provenance_uri=_build_provenance_uri(rel_path, chunk_slug),
                    char_count=para_len,
                )
            )
            part += 1
            continue

        if current_len + para_len + 2 > max_chunk_chars and current:
            chunk_slug = f"{slug}-part-{part}"
            text = "\n\n".join(current)
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#{chunk_slug}",
                    content=text,
                    heading=heading,
                    heading_path=heading_path,
                    provenance_uri=_build_provenance_uri(rel_path, chunk_slug),
                    char_count=len(text),
                )
            )
            part += 1
            current = []
            current_len = 0

        current.append(para)
        current_len += para_len + (2 if current_len > 0 else 0)

    if current:
        text = "\n\n".join(current)
        if chunks:
            chunk_slug = f"{slug}-part-{part}"
        else:
            chunk_slug = slug
        chunks.append(
            DocumentChunk(
                chunk_id=f"{rel_path}#{chunk_slug}",
                content=text,
                heading=heading,
                heading_path=heading_path,
                provenance_uri=_build_provenance_uri(rel_path, chunk_slug),
                char_count=len(text),
            )
        )

    return chunks


# === Plain Text Parser ===


def _parse_text(
    text: str, rel_path: str, max_chunk_chars: int
) -> ParsedDocument:
    """Parse plain text into paragraph-based chunks."""
    doc_date = _infer_date_from_filename(Path(rel_path))
    base_uri = _build_provenance_uri(rel_path)

    metadata = DocumentMetadata(
        title=Path(rel_path).stem,
        date=doc_date,
        source_path=rel_path,
        format="text",
        provenance_uri=base_uri,
    )

    # Split on blank lines
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

    if not paragraphs:
        return ParsedDocument(metadata=metadata, chunks=[], total_chars=0)

    # Merge small paragraphs, split large ones
    chunks: list[DocumentChunk] = []
    current: list[str] = []
    current_len = 0
    part = 1

    for para in paragraphs:
        para_len = len(para)

        if current_len + para_len + 2 > max_chunk_chars and current:
            text_block = "\n\n".join(current)
            slug = f"part-{part}"
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#{slug}",
                    content=text_block,
                    heading=None,
                    provenance_uri=_build_provenance_uri(rel_path, slug),
                    char_count=len(text_block),
                )
            )
            part += 1
            current = []
            current_len = 0

        current.append(para)
        current_len += para_len + (2 if current_len > 0 else 0)

    if current:
        text_block = "\n\n".join(current)
        slug = f"part-{part}" if part > 1 or not current else "part-1"
        chunks.append(
            DocumentChunk(
                chunk_id=f"{rel_path}#{slug}",
                content=text_block,
                heading=None,
                provenance_uri=_build_provenance_uri(rel_path, slug),
                char_count=len(text_block),
            )
        )

    total = sum(c.char_count for c in chunks)
    return ParsedDocument(metadata=metadata, chunks=chunks, total_chars=total)


# === PDF Parser ===


def _parse_pdf(
    path: Path, rel_path: str, max_chunk_chars: int
) -> ParsedDocument:
    """Parse PDF into page-based chunks."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ParsedDocument(
            metadata=DocumentMetadata(
                source_path=rel_path,
                format="pdf",
                provenance_uri=_build_provenance_uri(rel_path),
            ),
            chunks=[],
            total_chars=0,
            parse_errors=["pypdf not installed: pip install pypdf>=4.0.0"],
        )

    errors: list[str] = []
    base_uri = _build_provenance_uri(rel_path)

    try:
        reader = PdfReader(path)
    except Exception as e:
        return ParsedDocument(
            metadata=DocumentMetadata(
                source_path=rel_path,
                format="pdf",
                provenance_uri=base_uri,
            ),
            chunks=[],
            total_chars=0,
            parse_errors=[f"Failed to read PDF: {e}"],
        )

    # Extract metadata from PDF info dict
    title = None
    author = None
    doc_date = None

    info = reader.metadata
    if info:
        title = info.get("/Title") or info.title
        author = info.get("/Author") or info.author
        raw_date = info.get("/CreationDate")
        if raw_date and isinstance(raw_date, str):
            # PDF dates: D:YYYYMMDDHHmmSS or similar
            m = re.search(r"(\d{4})(\d{2})(\d{2})", raw_date)
            if m:
                try:
                    doc_date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                except ValueError:
                    pass

    if doc_date is None:
        doc_date = _infer_date_from_filename(path)

    # Clean up empty strings
    if title and not title.strip():
        title = None
    if author and not author.strip():
        author = None

    metadata = DocumentMetadata(
        title=title,
        author=author,
        date=doc_date,
        source_path=rel_path,
        format="pdf",
        provenance_uri=base_uri,
    )

    # Extract pages
    chunks: list[DocumentChunk] = []
    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            errors.append(f"Page {page_num}: {e}")
            text = ""

        text = text.strip()
        if not text:
            continue

        slug = f"page-{page_num}"
        if len(text) <= max_chunk_chars:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{rel_path}#{slug}",
                    content=text,
                    heading=f"Page {page_num}",
                    provenance_uri=_build_provenance_uri(rel_path, slug),
                    char_count=len(text),
                )
            )
        else:
            # Split long pages at paragraph boundaries
            sub_chunks = _make_chunks(
                text, f"Page {page_num}", [f"Page {page_num}"], rel_path, max_chunk_chars
            )
            # Fix slugs to include page number
            for i, sc in enumerate(sub_chunks):
                if len(sub_chunks) == 1:
                    sc.chunk_id = f"{rel_path}#{slug}"
                    sc.provenance_uri = _build_provenance_uri(rel_path, slug)
                else:
                    new_slug = f"page-{page_num}-part-{i + 1}"
                    sc.chunk_id = f"{rel_path}#{new_slug}"
                    sc.provenance_uri = _build_provenance_uri(rel_path, new_slug)
            chunks.extend(sub_chunks)

    total = sum(c.char_count for c in chunks)
    return ParsedDocument(
        metadata=metadata, chunks=chunks, total_chars=total, parse_errors=errors
    )


# === Top-Level API ===


_FORMAT_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".text": "text",
    ".pdf": "pdf",
}

DEFAULT_EXTENSIONS = {".md", ".pdf", ".txt"}


def parse_file(
    path: str | Path,
    base_dir: str | Path | None = None,
    max_chunk_chars: int = 2000,
) -> ParsedDocument:
    """Parse a single file into chunks.

    Args:
        path: Path to the file.
        base_dir: Base directory for computing relative paths and provenance URIs.
                  Defaults to the file's parent directory.
        max_chunk_chars: Soft limit for chunk size. Splits at natural boundaries.

    Returns:
        ParsedDocument with metadata and chunks.
    """
    path = Path(path).resolve()
    if base_dir is None:
        base_dir = path.parent
    else:
        base_dir = Path(base_dir).resolve()

    try:
        rel_path = str(path.relative_to(base_dir))
    except ValueError:
        rel_path = path.name

    # Normalize to forward slashes
    rel_path = rel_path.replace("\\", "/")

    suffix = path.suffix.lower()
    fmt = _FORMAT_MAP.get(suffix)

    if fmt is None:
        return ParsedDocument(
            metadata=DocumentMetadata(
                source_path=rel_path,
                format="unknown",
                provenance_uri=_build_provenance_uri(rel_path),
            ),
            chunks=[],
            total_chars=0,
            parse_errors=[f"Unsupported format: {suffix}"],
        )

    if fmt == "pdf":
        return _parse_pdf(path, rel_path, max_chunk_chars)

    # Text-based formats: read the file
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="latin-1")
        except Exception as e:
            return ParsedDocument(
                metadata=DocumentMetadata(
                    source_path=rel_path,
                    format=fmt,
                    provenance_uri=_build_provenance_uri(rel_path),
                ),
                chunks=[],
                total_chars=0,
                parse_errors=[f"Failed to read file: {e}"],
            )

    if fmt == "markdown":
        return _parse_markdown(text, rel_path, max_chunk_chars)
    else:
        return _parse_text(text, rel_path, max_chunk_chars)


def parse_directory(
    directory: str | Path,
    base_dir: str | Path | None = None,
    max_chunk_chars: int = 2000,
    extensions: set[str] | None = None,
) -> list[ParsedDocument]:
    """Parse all supported files in a directory tree.

    Args:
        directory: Root directory to scan.
        base_dir: Base for relative paths. Defaults to directory.
        max_chunk_chars: Soft limit for chunk size.
        extensions: File extensions to include (with dots). Defaults to {".md", ".pdf", ".txt"}.

    Returns:
        List of ParsedDocument, one per file. Sorted by relative path.
    """
    directory = Path(directory).resolve()
    if base_dir is None:
        base_dir = directory
    else:
        base_dir = Path(base_dir).resolve()

    if extensions is None:
        extensions = DEFAULT_EXTENSIONS

    results: list[ParsedDocument] = []
    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in extensions:
            continue
        results.append(
            parse_file(file_path, base_dir=base_dir, max_chunk_chars=max_chunk_chars)
        )

    return results
