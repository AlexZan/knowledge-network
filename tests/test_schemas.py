"""Tests for schema loading utilities."""

import pytest
from oi.schemas import (
    load_schema,
    get_node_type_names,
    get_extractable_types,
    get_tool_addable_types,
    get_display_visible_types,
    get_linkable_edge_types,
    get_all_edge_type_names,
    node_display_prefix,
    build_knowledge_prompt_section,
    build_extraction_type_list,
    # Backward compat aliases
    load_artifact_types,
    get_artifact_type_names,
    build_interpretation_prompt_section,
)


class TestSchemaLoading:
    """Test schema loading from YAML."""

    def test_load_schema_returns_dict(self):
        schema = load_schema()
        assert isinstance(schema, dict)
        assert "node_types" in schema
        assert "edge_types" in schema

    def test_all_node_types_present(self):
        names = get_node_type_names()
        for expected in ["fact", "preference", "decision", "principle", "effort"]:
            assert expected in names

    def test_all_edge_types_present(self):
        names = get_all_edge_type_names()
        for expected in ["supports", "contradicts", "exemplifies", "because_of", "supersedes"]:
            assert expected in names


class TestNodeTypeFilters:
    """Test node type filter helpers."""

    def test_extractable_types(self):
        types = get_extractable_types()
        assert "fact" in types
        assert "preference" in types
        assert "decision" in types
        assert "effort" not in types
        assert "principle" not in types

    def test_tool_addable_types(self):
        types = get_tool_addable_types()
        assert "fact" in types
        assert "preference" in types
        assert "decision" in types
        assert "effort" not in types
        assert "principle" not in types

    def test_display_visible_types(self):
        types = get_display_visible_types()
        assert "fact" in types
        assert "preference" in types
        assert "decision" in types
        assert "principle" in types
        assert "effort" not in types

    def test_linkable_edge_types(self):
        types = get_linkable_edge_types()
        assert "supports" in types
        assert "contradicts" in types
        assert "exemplifies" not in types
        assert "because_of" not in types
        assert "supersedes" not in types


class TestNodeDisplayPrefix:
    """Test node display prefix generation."""

    def test_simple_type(self):
        node = {"type": "fact", "summary": "something"}
        assert node_display_prefix(node) == "[fact]"

    def test_preference_type(self):
        node = {"type": "preference", "summary": "something"}
        assert node_display_prefix(node) == "[preference]"

    def test_principle_without_instances(self):
        node = {"type": "principle", "summary": "something"}
        assert node_display_prefix(node) == "[principle]"

    def test_principle_with_instances(self):
        node = {"type": "principle", "summary": "something", "instance_count": 3}
        assert node_display_prefix(node) == "[principle, 3 instances]"

    def test_unknown_type(self):
        node = {"type": "unknown", "summary": "something"}
        assert node_display_prefix(node) == "[unknown]"


class TestPromptBuilders:
    """Test prompt section builders."""

    def test_build_knowledge_prompt_section(self):
        section = build_knowledge_prompt_section()
        assert "**Types:**" in section
        assert "**fact**" in section
        assert "**preference**" in section
        assert "**decision**" in section
        # Non-tool-addable types should not appear
        assert "**effort**" not in section
        assert "**principle**" not in section

    def test_build_extraction_type_list(self):
        result = build_extraction_type_list()
        assert "node_type must be one of:" in result
        assert "fact" in result
        assert "preference" in result
        assert "decision" in result
        assert "effort" not in result
        assert "principle" not in result


class TestBackwardCompat:
    """Test backward compatibility aliases still work."""

    def test_load_artifact_types(self):
        schema = load_artifact_types()
        assert isinstance(schema, dict)
        assert "types" in schema
        assert "effort" in schema["types"]
        assert "fact" in schema["types"]

    def test_get_artifact_type_names(self):
        names = get_artifact_type_names()
        assert isinstance(names, list)
        assert "effort" in names
        assert "fact" in names

    def test_build_interpretation_prompt_section(self):
        section = build_interpretation_prompt_section()
        assert "## Artifact Types" in section
        assert "| Type |" in section
        assert "effort" in section
        assert "fact" in section

    def test_effort_has_status_in_compat(self):
        schema = load_artifact_types()
        effort = schema["types"]["effort"]
        assert effort.get("has_status") is True

    def test_prompt_section_includes_effort_status(self):
        section = build_interpretation_prompt_section()
        assert "## Effort Status" in section
        assert "open" in section
        assert "resolved" in section


class TestSchemaCompleteness:
    """Test that schema has required fields for each type."""

    def test_node_types_have_required_fields(self):
        schema = load_schema()
        required_fields = ["extractable", "tool_addable", "show_in_display", "has_raw_file", "id_format", "valid_statuses", "prompt_description"]
        for name, cfg in schema["node_types"].items():
            for field in required_fields:
                assert field in cfg, f"{name} missing {field}"

    def test_edge_types_have_linkable(self):
        schema = load_schema()
        for name, cfg in schema["edge_types"].items():
            assert "linkable" in cfg, f"edge type {name} missing linkable"

    def test_id_format_values_valid(self):
        schema = load_schema()
        for name, cfg in schema["node_types"].items():
            assert cfg["id_format"] in ("counter", "name"), f"{name} has invalid id_format"

    def test_valid_statuses_are_lists(self):
        schema = load_schema()
        for name, cfg in schema["node_types"].items():
            assert isinstance(cfg["valid_statuses"], list), f"{name} valid_statuses is not a list"
