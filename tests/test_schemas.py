"""Tests for schema loading utilities."""

import pytest
from oi.schemas import (
    load_artifact_types,
    get_artifact_type_names,
    build_interpretation_prompt_section,
)


class TestSchemaLoading:
    """Test schema loading from YAML."""

    def test_load_artifact_types_returns_dict(self):
        """Loading artifact types returns a dict with types key."""
        schema = load_artifact_types()
        assert isinstance(schema, dict)
        assert "types" in schema

    def test_default_types_present(self):
        """Default types (effort, fact, event) are present."""
        schema = load_artifact_types()
        types = schema["types"]
        assert "effort" in types
        assert "fact" in types
        assert "event" in types

    def test_effort_has_status(self):
        """Effort type has has_status=true."""
        schema = load_artifact_types()
        effort = schema["types"]["effort"]
        assert effort.get("has_status") is True
        assert effort.get("has_resolution") is True

    def test_fact_does_not_have_status(self):
        """Fact type has has_status=false."""
        schema = load_artifact_types()
        fact = schema["types"]["fact"]
        assert fact.get("has_status") is not True

    def test_get_artifact_type_names(self):
        """get_artifact_type_names returns list of type names."""
        names = get_artifact_type_names()
        assert isinstance(names, list)
        assert "effort" in names
        assert "fact" in names
        assert "event" in names

    def test_build_interpretation_prompt_section(self):
        """build_interpretation_prompt_section generates markdown table."""
        section = build_interpretation_prompt_section()
        assert "## Artifact Types" in section
        assert "| Type |" in section
        assert "effort" in section
        assert "fact" in section
        assert "event" in section

    def test_prompt_section_includes_status_for_effort(self):
        """Prompt section includes status explanation since effort has_status."""
        section = build_interpretation_prompt_section()
        assert "## Effort Status" in section
        assert "open" in section
        assert "resolved" in section
