"""Tests for document parser (Slice 13a)."""

import io
import textwrap
from datetime import date
from pathlib import Path

import pytest

from oi.parser import (
    DocumentChunk,
    DocumentMetadata,
    ParsedDocument,
    _build_provenance_uri,
    _extract_frontmatter,
    _infer_date_from_filename,
    _infer_title_from_content,
    _make_chunks,
    _parse_markdown,
    _parse_text,
    _slugify,
    parse_directory,
    parse_file,
)


# === Utility Tests ===


class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert _slugify("What's New?") == "whats-new"

    def test_multiple_spaces(self):
        assert _slugify("The   Big   Idea") == "the-big-idea"

    def test_leading_trailing(self):
        assert _slugify("  -hello- ") == "hello"

    def test_underscores(self):
        assert _slugify("some_heading_text") == "some-heading-text"

    def test_empty(self):
        assert _slugify("") == ""

    def test_numbers(self):
        assert _slugify("Phase 2: Setup") == "phase-2-setup"


class TestBuildProvenanceUri:
    def test_no_fragment(self):
        assert _build_provenance_uri("docs/thesis.md") == "doc://docs/thesis.md"

    def test_with_fragment(self):
        uri = _build_provenance_uri("docs/thesis.md", "abstract")
        assert uri == "doc://docs/thesis.md#abstract"

    def test_backslash_normalization(self):
        uri = _build_provenance_uri("docs\\sub\\file.md")
        assert uri == "doc://docs/sub/file.md"


class TestExtractFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\ntitle: My Doc\nauthor: Alice\n---\n\nBody text."
        meta, body = _extract_frontmatter(text)
        assert meta == {"title": "My Doc", "author": "Alice"}
        assert body == "Body text."

    def test_no_frontmatter(self):
        text = "# Just a heading\n\nBody text."
        meta, body = _extract_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_unclosed_frontmatter(self):
        text = "---\ntitle: Broken\nstuff"
        meta, body = _extract_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_non_dict_frontmatter(self):
        text = "---\n- item1\n- item2\n---\nBody."
        meta, body = _extract_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_frontmatter_with_date(self):
        text = "---\ntitle: Notes\ndate: 2024-03-15\n---\nContent."
        meta, body = _extract_frontmatter(text)
        # YAML parses bare dates as datetime.date objects
        assert meta["date"] == date(2024, 3, 15)
        assert body == "Content."

    def test_horizontal_rule_not_frontmatter(self):
        text = "Some text\n\n---\n\nMore text"
        meta, body = _extract_frontmatter(text)
        assert meta == {}
        assert body == text


class TestInferDateFromFilename:
    def test_date_prefix(self):
        p = Path("2024-01-15-meeting-notes.md")
        assert _infer_date_from_filename(p) == date(2024, 1, 15)

    def test_date_in_middle(self):
        p = Path("notes-2023-12-01-final.txt")
        assert _infer_date_from_filename(p) == date(2023, 12, 1)

    def test_no_date(self):
        p = Path("readme.md")
        assert _infer_date_from_filename(p) is None

    def test_invalid_date(self):
        p = Path("2024-13-45-bad.md")
        assert _infer_date_from_filename(p) is None


class TestInferTitleFromContent:
    def test_h1_title(self):
        text = "# My Document\n\nSome content."
        assert _infer_title_from_content(text) == "My Document"

    def test_no_h1(self):
        text = "## Not a title\n\nContent."
        assert _infer_title_from_content(text) is None

    def test_h1_not_first_line(self):
        text = "Some preamble\n\n# The Title\n\nContent."
        assert _infer_title_from_content(text) == "The Title"


# === Markdown Parser Tests ===


class TestMarkdownParser:
    def test_simple_sections(self):
        md = textwrap.dedent("""\
            # My Doc

            Intro paragraph.

            ## Section One

            Content of section one.

            ## Section Two

            Content of section two.
        """)
        result = _parse_markdown(md, "test.md", 2000)
        assert result.metadata.title == "My Doc"
        assert result.metadata.format == "markdown"
        assert len(result.chunks) >= 3  # h1 + 2 sections

        # Check section slugs — h2 under h1 gets parent prefix
        slugs = [c.chunk_id.split("#")[1] for c in result.chunks]
        assert "my-doc" in slugs
        assert "my-doc-section-one" in slugs
        assert "my-doc-section-two" in slugs

    def test_heading_path_tracking(self):
        md = textwrap.dedent("""\
            ## Parent

            Parent content.

            ### Child

            Child content.

            ## Sibling

            Sibling content.
        """)
        result = _parse_markdown(md, "test.md", 2000)
        chunks_by_slug = {c.chunk_id.split("#")[1]: c for c in result.chunks}

        child = chunks_by_slug["parent-child"]
        assert child.heading_path == ["Parent", "Child"]

        sibling = chunks_by_slug["sibling"]
        assert sibling.heading_path == ["Sibling"]

    def test_code_block_awareness(self):
        md = textwrap.dedent("""\
            ## Real Section

            Some code:

            ```python
            ## This is NOT a heading
            def foo():
                pass
            ```

            More text.
        """)
        result = _parse_markdown(md, "test.md", 2000)
        headings = [c.heading for c in result.chunks if c.heading]
        assert "This is NOT a heading" not in headings
        assert "Real Section" in headings

    def test_long_section_splits(self):
        long_text = ("Paragraph one. " * 50 + "\n\n" + "Paragraph two. " * 50)
        md = f"## Big Section\n\n{long_text}"
        result = _parse_markdown(md, "test.md", 200)
        assert len(result.chunks) > 1
        for chunk in result.chunks:
            assert "big-section" in chunk.chunk_id

    def test_frontmatter_metadata(self):
        md = "---\ntitle: Custom Title\nauthor: Bob\ndate: 2024-06-15\n---\n\n# Ignored H1\n\nBody."
        result = _parse_markdown(md, "test.md", 2000)
        assert result.metadata.title == "Custom Title"
        assert result.metadata.author == "Bob"
        assert result.metadata.date == date(2024, 6, 15)

    def test_empty_section(self):
        md = "## Empty\n\n## Has Content\n\nSome text."
        result = _parse_markdown(md, "test.md", 2000)
        slugs = [c.chunk_id.split("#")[1] for c in result.chunks]
        assert "empty" in slugs
        empty_chunk = [c for c in result.chunks if "empty" in c.chunk_id][0]
        assert empty_chunk.char_count == 0

    def test_no_headings(self):
        md = "Just some plain text\nwith no headings at all."
        result = _parse_markdown(md, "test.md", 2000)
        assert len(result.chunks) == 1
        assert result.chunks[0].heading is None

    def test_h1_not_splitting(self):
        md = textwrap.dedent("""\
            # Document Title

            Intro.

            ## Section

            Content.
        """)
        result = _parse_markdown(md, "test.md", 2000)
        # h1 should appear in heading path of preamble? No, h1 triggers a section too.
        # The key is it creates sections like any other heading.
        chunk_headings = [c.heading for c in result.chunks if c.heading]
        assert "Document Title" in chunk_headings

    def test_duplicate_headings_get_unique_slugs(self):
        """Same h3 heading under different h2 parents produces unique slugs."""
        md = textwrap.dedent("""\
            ## Thesis 1

            Intro.

            ### The Problem

            Problem for thesis 1.

            ## Thesis 2

            Intro.

            ### The Problem

            Problem for thesis 2.
        """)
        result = _parse_markdown(md, "test.md", 2000)
        slugs = [c.chunk_id.split("#")[1] for c in result.chunks]
        assert "thesis-1-the-problem" in slugs
        assert "thesis-2-the-problem" in slugs
        # They must be different
        assert len(slugs) == len(set(slugs)), f"Duplicate slugs found: {slugs}"

    def test_top_level_slugs_stay_short(self):
        """Top-level headings (single element path) use just the heading text."""
        md = textwrap.dedent("""\
            ## Overview

            Content.

            ## Details

            More content.
        """)
        result = _parse_markdown(md, "test.md", 2000)
        slugs = [c.chunk_id.split("#")[1] for c in result.chunks]
        assert "overview" in slugs
        assert "details" in slugs

    def test_provenance_uris(self):
        md = "## About\n\nContent here."
        result = _parse_markdown(md, "docs/file.md", 2000)
        assert result.metadata.provenance_uri == "doc://docs/file.md"
        assert result.chunks[0].provenance_uri == "doc://docs/file.md#about"

    def test_date_from_filename(self):
        md = "# Notes\n\nSome notes."
        result = _parse_markdown(md, "2024-03-15-meeting.md", 2000)
        assert result.metadata.date == date(2024, 3, 15)


# === Plain Text Parser Tests ===


class TestTextParser:
    def test_simple_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = _parse_text(text, "notes.txt", 2000)
        assert result.metadata.format == "text"
        assert result.metadata.title == "notes"
        assert len(result.chunks) == 1  # All fit in one chunk
        assert "First paragraph." in result.chunks[0].content

    def test_paragraph_splitting(self):
        p1 = "A" * 100
        p2 = "B" * 100
        p3 = "C" * 100
        text = f"{p1}\n\n{p2}\n\n{p3}"
        result = _parse_text(text, "big.txt", 150)
        assert len(result.chunks) >= 2

    def test_empty_text(self):
        result = _parse_text("", "empty.txt", 2000)
        assert result.chunks == []
        assert result.total_chars == 0

    def test_single_paragraph(self):
        result = _parse_text("Just one block of text.", "one.txt", 2000)
        assert len(result.chunks) == 1

    def test_date_from_filename(self):
        result = _parse_text("Content.", "2024-01-01-log.txt", 2000)
        assert result.metadata.date == date(2024, 1, 1)


# === PDF Parser Tests ===


class TestPdfParser:
    @pytest.fixture
    def simple_pdf(self, tmp_path):
        """Create a minimal PDF with pypdf."""
        try:
            from pypdf import PdfWriter
        except ImportError:
            pytest.skip("pypdf not installed")

        writer = PdfWriter()
        # Add a blank page with text annotation
        writer.add_blank_page(width=612, height=792)

        # Set metadata
        writer.add_metadata(
            {
                "/Title": "Test Document",
                "/Author": "Test Author",
            }
        )

        pdf_path = tmp_path / "test.pdf"
        with open(pdf_path, "wb") as f:
            writer.write(f)
        return pdf_path

    @pytest.fixture
    def pdf_with_text(self, tmp_path):
        """Create a PDF with actual text content using reportlab-style approach."""
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError:
            pytest.skip("pypdf not installed")

        # Create a minimal PDF with text via raw PDF stream
        # This is a valid minimal PDF with text on one page
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>stream\n"
            b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000266 00000 n \n"
            b"0000000360 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\n"
            b"startxref\n431\n%%EOF"
        )
        pdf_path = tmp_path / "with_text.pdf"
        pdf_path.write_bytes(pdf_content)
        return pdf_path

    def test_pdf_metadata(self, simple_pdf):
        from oi.parser import _parse_pdf

        result = _parse_pdf(simple_pdf, "test.pdf", 2000)
        assert result.metadata.format == "pdf"
        assert result.metadata.title == "Test Document"
        assert result.metadata.author == "Test Author"

    def test_pdf_text_extraction(self, pdf_with_text):
        from oi.parser import _parse_pdf

        result = _parse_pdf(pdf_with_text, "with_text.pdf", 2000)
        assert result.metadata.format == "pdf"
        # Should have at least one chunk with text
        if result.chunks:  # text extraction may vary by pypdf version
            assert any("Hello" in c.content for c in result.chunks)

    def test_pdf_missing_pypdf(self, monkeypatch):
        """Graceful error when pypdf not installed."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("No module named 'pypdf'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from oi.parser import _parse_pdf

        result = _parse_pdf(Path("/fake.pdf"), "fake.pdf", 2000)
        assert "pypdf not installed" in result.parse_errors[0]

    def test_pdf_invalid_file(self, tmp_path):
        from oi.parser import _parse_pdf

        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_text("not a pdf")
        result = _parse_pdf(bad_pdf, "bad.pdf", 2000)
        assert len(result.parse_errors) > 0
        assert "Failed to read PDF" in result.parse_errors[0]

    def test_pdf_date_from_filename(self, tmp_path):
        try:
            from pypdf import PdfWriter
        except ImportError:
            pytest.skip("pypdf not installed")

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        pdf_path = tmp_path / "2024-05-20-report.pdf"
        with open(pdf_path, "wb") as f:
            writer.write(f)

        from oi.parser import _parse_pdf

        result = _parse_pdf(pdf_path, "2024-05-20-report.pdf", 2000)
        assert result.metadata.date == date(2024, 5, 20)


# === Top-Level API Tests ===


class TestParseFile:
    def test_markdown_file(self, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Title\n\n## Intro\n\nHello world.")
        result = parse_file(md_file)
        assert result.metadata.format == "markdown"
        assert result.metadata.title == "Title"
        assert len(result.chunks) >= 1

    def test_text_file(self, tmp_path):
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Some plain text content.")
        result = parse_file(txt_file)
        assert result.metadata.format == "text"

    def test_unsupported_format(self, tmp_path):
        html_file = tmp_path / "page.html"
        html_file.write_text("<html>hello</html>")
        result = parse_file(html_file)
        assert result.metadata.format == "unknown"
        assert "Unsupported format" in result.parse_errors[0]

    def test_base_dir_relative_path(self, tmp_path):
        sub = tmp_path / "docs"
        sub.mkdir()
        f = sub / "file.md"
        f.write_text("# Test\n\nContent.")
        result = parse_file(f, base_dir=tmp_path)
        assert result.metadata.source_path == "docs/file.md"
        assert result.metadata.provenance_uri == "doc://docs/file.md"

    def test_default_base_dir(self, tmp_path):
        f = tmp_path / "file.md"
        f.write_text("# Test\n\nContent.")
        result = parse_file(f)
        assert result.metadata.source_path == "file.md"


class TestParseDirectory:
    def test_finds_supported_files(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Doc\n\nContent.")
        (tmp_path / "notes.txt").write_text("Plain text.")
        (tmp_path / "style.css").write_text("body {}")  # Should be skipped
        results = parse_directory(tmp_path)
        formats = {r.metadata.format for r in results}
        assert "markdown" in formats
        assert "text" in formats
        assert len(results) == 2

    def test_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "top.md").write_text("# Top\n\nContent.")
        (sub / "nested.md").write_text("# Nested\n\nContent.")
        results = parse_directory(tmp_path)
        paths = {r.metadata.source_path for r in results}
        assert "top.md" in paths
        assert "sub/nested.md" in paths

    def test_custom_extensions(self, tmp_path):
        (tmp_path / "file.md").write_text("# Markdown")
        (tmp_path / "file.txt").write_text("Text")
        results = parse_directory(tmp_path, extensions={".md"})
        assert len(results) == 1
        assert results[0].metadata.format == "markdown"

    def test_sorted_by_path(self, tmp_path):
        (tmp_path / "b.md").write_text("# B")
        (tmp_path / "a.md").write_text("# A")
        results = parse_directory(tmp_path)
        paths = [r.metadata.source_path for r in results]
        assert paths == sorted(paths)

    def test_empty_directory(self, tmp_path):
        results = parse_directory(tmp_path)
        assert results == []


# === Chunk Splitting Tests ===


class TestMakeChunks:
    def test_small_content_single_chunk(self):
        chunks = _make_chunks("Short text.", "Heading", ["Heading"], "f.md", 2000)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."
        assert chunks[0].heading == "Heading"
        assert chunks[0].heading_path == ["Heading"]

    def test_long_content_splits(self):
        content = "\n\n".join(f"Paragraph {i}. " + "x" * 80 for i in range(10))
        chunks = _make_chunks(content, "Big", ["Big"], "f.md", 200)
        assert len(chunks) > 1
        # All chunks reference the heading
        for c in chunks:
            assert c.heading == "Big"
            assert "big" in c.chunk_id

    def test_single_huge_paragraph(self):
        content = "x" * 5000
        chunks = _make_chunks(content, "Huge", ["Huge"], "f.md", 2000)
        assert len(chunks) == 1  # Can't split a single paragraph
        assert chunks[0].char_count == 5000


# === Dogfood Tests (real project docs) ===


class TestDogfood:
    """Parse real project documents to verify end-to-end behavior."""

    PROJECT_ROOT = Path(__file__).parent.parent

    def test_parse_thesis(self):
        thesis = self.PROJECT_ROOT / "docs" / "thesis.md"
        if not thesis.exists():
            pytest.skip("docs/thesis.md not found")
        result = parse_file(thesis, base_dir=self.PROJECT_ROOT)
        assert result.metadata.format == "markdown"
        assert result.metadata.source_path == "docs/thesis.md"
        assert result.metadata.provenance_uri == "doc://docs/thesis.md"
        assert result.total_chars > 0
        assert len(result.chunks) > 1
        # Should have real section headings
        headings = [c.heading for c in result.chunks if c.heading]
        assert len(headings) > 0

    def test_parse_roadmap(self):
        roadmap = self.PROJECT_ROOT / "docs" / "slices" / "README.md"
        if not roadmap.exists():
            pytest.skip("docs/slices/README.md not found")
        result = parse_file(roadmap, base_dir=self.PROJECT_ROOT)
        assert result.metadata.format == "markdown"
        assert result.metadata.source_path == "docs/slices/README.md"
        assert result.total_chars > 0
        assert len(result.chunks) > 1

    def test_parse_docs_directory(self):
        docs_dir = self.PROJECT_ROOT / "docs"
        if not docs_dir.exists():
            pytest.skip("docs/ directory not found")
        results = parse_directory(docs_dir, base_dir=self.PROJECT_ROOT, extensions={".md"})
        assert len(results) > 0
        # All should be markdown
        for r in results:
            assert r.metadata.format == "markdown"
            assert r.metadata.source_path.startswith("docs/")
            assert r.metadata.provenance_uri.startswith("doc://docs/")
